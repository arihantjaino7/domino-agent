"""Decision lifecycle and the executor. Pure and deterministic; no LLM.

propose_decision -> approve_decision (bound to plan_hash + world_version) -> execute_plan, or reject_decision:
  preflight read (every reference checked) -> one atomic write -> receipt compared with the plan (V9).
Running the same execution twice creates nothing the second time ("already_executed").
"""

from __future__ import annotations

import json
import threading
from collections import defaultdict
from typing import Any

from domino.graph.run_query import QueryError, run_query

_locks: dict[str, threading.Lock] = defaultdict(threading.Lock)


def propose_decision(graph: str, incident_id: str, plan: dict[str, Any], rationale: str = "") -> dict[str, Any]:
    rows = run_query("decision/create", {
        "incident_id": incident_id, "decision_id": plan["decision_id"], "strategy": plan["strategy"],
        "plan_hash": plan["plan_hash"], "world_version": plan["world_version"],
        "budget_cents": plan["budget_cents"], "rationale": rationale}, ro=False, graph=graph)
    if not rows:
        return {"outcome": "unknown_entity", "unknown": [incident_id]}
    if rows[0]["plan_hash"] != plan["plan_hash"]:
        return {"outcome": "conflict", "detail": "a different plan is already recorded under this decision id"}
    return {"outcome": "ok", "decision": rows[0]["decision"], "status": rows[0]["status"]}


def approve_decision(graph: str, plan: dict[str, Any], approved_by: str) -> dict[str, Any]:
    state = run_query("decision/get", {"decision_id": plan["decision_id"]}, graph=graph)[0]
    if state["decision"] is None:
        return {"outcome": "unknown_entity", "unknown": [plan["decision_id"]]}
    if state["world_version"] != plan["world_version"]:
        return {"outcome": "stale_world", "detail": f"world moved from v{plan['world_version']} to "
                                                    f"v{state['world_version']}; re-simulate before approving"}
    rows = run_query("decision/approve", {"decision_id": plan["decision_id"], "plan_hash": plan["plan_hash"],
                                          "approved_by": approved_by}, ro=False, graph=graph)
    if not rows:
        return {"outcome": "not_approvable", "detail": f"decision is {state['status']} or plan_hash differs"}
    return {"outcome": "ok", "status": "approved", "approved_by": approved_by}


def reject_decision(graph: str, decision_id: str, feedback: str, rejected_by: str = "web") -> dict[str, Any]:
    rows = run_query("decision/reject", {"decision_id": decision_id, "feedback": feedback[:1000],
                                         "rejected_by": rejected_by}, ro=False, graph=graph)
    if not rows:
        return {"outcome": "not_rejectable", "detail": f"{decision_id} is not a proposed decision"}
    return {"outcome": "ok", "status": "rejected"}


def _pos_param(plan: dict[str, Any]) -> list[dict[str, Any]]:
    return [{**p, "order_ids": sorted({a["order_id"] for a in p["allocations"]})} for p in plan["pos"]]


def preflight(graph: str, plan: dict[str, Any]) -> dict[str, Any]:
    pos = _pos_param(plan)
    rows = run_query("execute/preflight", {"pos": pos}, graph=graph) if pos else []
    problems, existing = [], []
    if len(rows) != len(pos):
        problems.append(f"preflight returned {len(rows)} rows for {len(pos)} planned POs")
    for r in rows:
        if r["existing"]:
            existing.append(r["po_id"])
        if r["edges"] != 1:
            problems.append(f"{r['po_id']}: no approved CAN_SUPPLY edge for this site, part and plant")
        if r["components"] != 1:
            problems.append(f"{r['po_id']}: unknown component")
        if r["allocations"] < 1:
            problems.append(f"{r['po_id']}: PO has no allocations")
        if r["orders_found"] != r["orders_planned"]:
            problems.append(f"{r['po_id']}: {r['orders_planned'] - r['orders_found']} allocated orders not in the graph")
        if r["free_wk"] is not None and r["rate_wk"] > r["free_wk"]:
            problems.append(f"{r['po_id']}: rate {r['rate_wk']}/wk exceeds free spare {r['free_wk']}/wk")
    return {"ok": not problems and not existing, "problems": problems, "existing": existing, "rows": rows}


def execute_plan(graph: str, plan: dict[str, Any], day: int = 0) -> dict[str, Any]:
    """Preflight, one atomic write, receipt. Never writes a partial plan."""
    if not plan["pos"]:
        return {"outcome": "nothing_to_execute"}
    with _locks[graph]:
        state = run_query("decision/get", {"decision_id": plan["decision_id"]}, graph=graph)[0]
        if state["status"] == "executed":
            return {"outcome": "already_executed", "decision": plan["decision_id"], "pos_created": 0}
        if state["status"] != "approved" or state["plan_hash"] != plan["plan_hash"]:
            return {"outcome": "not_approved", "detail": f"decision status {state['status']}"}
        if state["world_version"] != plan["world_version"]:
            return {"outcome": "stale_world", "detail": "world changed since approval; re-simulate"}
        pf = preflight(graph, plan)
        if pf["existing"]:
            return {"outcome": "already_executed", "decision": plan["decision_id"], "pos_created": 0,
                    "existing": pf["existing"]}
        if not pf["ok"]:
            return {"outcome": "preflight_failed", "problems": pf["problems"]}
        payload = json.dumps({"plan_hash": plan["plan_hash"], "pos": [p["id"] for p in plan["pos"]]})
        try:
            rows = run_query("execute/write", {
                "decision_id": plan["decision_id"], "plan_hash": plan["plan_hash"],
                "world_version": plan["world_version"], "pos": _pos_param(plan), "day": day,
                "action_id": f"ACT-{plan['decision_id']}-execute", "payload_json": payload}, ro=False, graph=graph)
        except QueryError as exc:
            if "unique constraint" in str(exc):
                return {"outcome": "already_executed", "decision": plan["decision_id"], "pos_created": 0}
            raise
    if not rows:
        return {"outcome": "write_matched_nothing", "detail": "decision or world_version changed during execution"}
    r = rows[0]
    expected_protects = sum(len(p["allocations"]) for p in plan["pos"])
    receipt = {
        "outcome": "executed", "decision": r["decision"], "world_version": r["world_version"],
        "pos_created": r["pos_created"], "protects_created": r["protects_created"],
        "orders_protected": sorted(r["orders"]), "po_ids": sorted(p["id"] for p in plan["pos"]),
        "expected_pos": len(plan["pos"]), "expected_protects": expected_protects,
    }
    receipt["receipt_matches_plan"] = (r["pos_created"] == len(plan["pos"]) and
                                       r["protects_created"] == expected_protects)
    receipt["summary"] = (f"+{r['pos_created']} PurchaseOrder, +{r['protects_created']} PROTECTS, "
                          f"{len(r['orders'])} orders -> protected (projected)")
    return receipt
