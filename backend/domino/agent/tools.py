"""The agent's tool catalogue (PLAN §9.4): a fixed, parameterised set over the deterministic engines.

The LLM never writes Cypher. Every id argument is resolved against the graph first; an unknown id
raises ToolInputError ("unknown_entity", with did-you-mean suggestions), which the MCP layer returns
as `is_error: true` so the agent can recover. Each tool records a compact summary (<= ~2 KB, sent to
the LLM, with a result_ref) and a full payload (for the UI) in the run context.

`execute_plan` is deliberately NOT a tool: only the human approval path calls the executor.
"""

from __future__ import annotations

import difflib
import re
from typing import Any

from domino.agent import memory
from domino.agent.context import GUARDED_ID, RunContext
from domino.allocators.strategies import PRESETS
from domino.engines.alternatives import find_alternatives as _find_alternatives
from domino.engines.capacity import compute_true_capacity as _true_capacity
from domino.engines.executor import propose_decision
from domino.engines.exposure import trace_exposure as _trace_exposure
from domino.engines.incident import declare_incident as _declare
from domino.engines.sandbox import simulate_strategies as _simulate
from domino.engines.shortage import project_shortages as _project
from domino.engines.verifier import verify_execution as _verify
from domino.graph.run_query import run_query

HORIZON = 42
OUTCOMES = ("answered_with_path", "answered_from_memory", "not_in_graph", "unknown_entity")
CLAIM_TYPES = ("depends_on", "exposed", "late", "rejected", "protected", "capacity", "not_in_graph")


class ToolInputError(ValueError):
    pass


def _usd(cents: int | None) -> int | None:
    return None if cents is None else round(cents / 100)


def require_ids(ctx: RunContext, ids: list[str], labels: tuple[str, ...] = ()) -> dict[str, list[str]]:
    """Every id must exist (and carry one of `labels`, if given) before any engine runs."""
    rows = run_query("agent/ids_exist", {"ids": sorted(set(ids))}, graph=ctx.graph)
    found = {r["id"]: r["labels"] for r in rows if r["labels"]}
    unknown = [i for i in sorted(set(ids)) if i not in found]
    wrong = [i for i in found if labels and not set(found[i]) & set(labels)]
    if unknown:
        all_ids = [r["id"] for r in run_query("agent/all_ids", graph=ctx.graph)]
        hints = {u: difflib.get_close_matches(u, all_ids, n=3, cutoff=0.6) for u in unknown}
        raise ToolInputError(f"unknown_entity: {unknown} not in the graph. Did you mean: {hints}? "
                             "Use resolve_entities to find ids from names.")
    if wrong:
        raise ToolInputError(f"wrong entity type: {wrong} are not {labels}")
    return found


def _need_incident(ctx: RunContext, incident_id: str) -> None:
    require_ids(ctx, [incident_id], ("Incident",))


# ---------------------------------------------------------------------------
# Detect
# ---------------------------------------------------------------------------

def resolve_entities(ctx: RunContext, terms: list[str]) -> dict[str, Any]:
    out = []
    for term in terms:
        clean = re.sub(r"[^\w\s]", " ", term).strip()
        if not clean:
            continue
        hits: dict[str, dict[str, Any]] = {}
        fuzzy = " ".join(f"%{w}%" if len(w) > 3 else w for w in clean.split())
        for q in (clean, fuzzy):
            for r in run_query("agent/resolve_places", {"term": q}, graph=ctx.graph):
                label = next((x for x in r["labels"] if x != "Place"), r["labels"][0])
                if r["id"] not in hits or hits[r["id"]]["score"] < r["score"]:
                    hits[r["id"]] = {"id": r["id"], "label": label, "name": r["name"], "country": r["country"],
                                     "score": round(r["score"], 3)}
        cands = sorted(hits.values(), key=lambda h: (-h["score"], h["id"]))[:5]
        countries = {c["country"] for c in cands[:2] if c["score"] >= 0.85 * cands[0]["score"] and c["country"]}
        ambiguous = len(countries) > 1
        out.append({"term": term, "candidates": cands, "ambiguous": ambiguous,
                    "outcome": "found" if cands else "not_in_graph"})
    summary = {"results": out,
               "note": "No candidates means the name is not modelled in the graph; that is not the same as safe."}
    ctx.add_result("resolve_entities", summary, {"results": out})
    return summary


def declare_incident(ctx: RunContext, entity_ids: list[str], kind: str, title: str, duration_days: int,
                     capacity_factor: float = 0.0) -> dict[str, Any]:
    require_ids(ctx, entity_ids, ("HazardZone", "Region", "Site"))
    if not 0 <= capacity_factor < 1:
        raise ToolInputError("capacity_factor must be in [0, 1): 0 = fully down, 0.5 = half capacity")
    if not 1 <= duration_days <= 120:
        raise ToolInputError("duration_days must be between 1 and 120")
    n = run_query("agent/next_incident_id", graph=ctx.graph)[0]["n"]
    incident_id = f"INC-{n + 1:04d}"
    res = _declare(ctx.graph, incident_id=incident_id, kind=kind, title=title, alert_text=ctx.alert_text,
                   entity_ids=entity_ids, capacity_factor=capacity_factor, duration_days=duration_days)
    if res["outcome"] != "ok":
        raise ToolInputError(f"{res['outcome']}: {res}")
    ctx.incident_id = incident_id
    summary = {"incident_id": incident_id, "sites_affected": res["site_ids"], "disrupted_until_day": res["end_day"],
               "capacity_factor": capacity_factor, "world_version": res["world_version"]}
    ctx.add_result("declare_incident", summary, res)
    return summary


# ---------------------------------------------------------------------------
# Context
# ---------------------------------------------------------------------------

def get_entity_context(ctx: RunContext, entity_id: str) -> dict[str, Any]:
    require_ids(ctx, [entity_id])
    rows = run_query("agent/entity_context", {"entity_id": entity_id}, graph=ctx.graph)
    props = rows[0]["props"] if rows else {}
    links: dict[str, list[str]] = {}
    for r in rows:
        if r["rel"]:
            key = f"{'->' if r['outgoing'] else '<-'}{r['rel']}"
            links.setdefault(key, []).append(r["other"])
    summary = {"entity": entity_id, "labels": rows[0]["labels"] if rows else [], "properties": props,
               "neighbours": {k: sorted(v)[:15] for k, v in sorted(links.items())}}
    ctx.add_result("get_entity_context", summary, {"rows": rows})
    return summary


def recall_history(ctx: RunContext, entity_ids: list[str]) -> dict[str, Any]:
    rows = memory.recall_history(entity_ids)
    summary = {"memories": rows, "outcome": "answered_from_memory" if rows else "nothing_remembered",
               "note": "Each memory carries the date it was learned (learned_on)."}
    ctx.add_result("recall_history", summary, {"memories": rows})
    return summary


# ---------------------------------------------------------------------------
# Investigate
# ---------------------------------------------------------------------------

def trace_exposure(ctx: RunContext, incident_id: str) -> dict[str, Any]:
    _need_incident(ctx, incident_id)
    exp = _trace_exposure(ctx.graph, incident_id, HORIZON)
    evidence = []
    for ev in exp["evidence"]:
        eid = ctx.add_evidence(ev["path"])
        evidence.append({"id": eid, "path": ev["path"], "component": ev["component"], "product": ev["product"],
                         "orders": len(ev["orders"])})
    summary = {"incident_id": incident_id, "tier1_view": exp["tier1_view"],
               "multi_tier": {**exp["multi_tier"]},
               "shared_upstream": exp["shared_upstream"], "evidence": evidence}
    ctx.add_result("trace_exposure", summary, exp)
    return summary


def explain_shared_dependencies(ctx: RunContext, incident_id: str) -> dict[str, Any]:
    _need_incident(ctx, incident_id)
    exp = _trace_exposure(ctx.graph, incident_id, HORIZON)
    shared = []
    for s in exp["shared_upstream"]:
        paths = [{"id": ctx.add_evidence([s["site"], d]), "path": [s["site"], d]} for d in s["dependents"]]
        shared.append({**s, "evidence": paths})
    summary = {"incident_id": incident_id, "shared_upstream": shared,
               "meaning": "each listed site feeds several tier-1 suppliers (active or alternate); backups that "
                          "share it are not independent"}
    ctx.add_result("explain_shared_dependencies", summary, {"shared": shared})
    return summary


def project_shortages(ctx: RunContext, horizon: int = HORIZON) -> dict[str, Any]:
    res = _project(ctx.graph, horizon)
    late = [o for o in res["orders"] if o["status"] == "projected_late"]
    summary = {
        "horizon_days": horizon,
        "totals": {**res["totals"], "revenue_at_risk_usd": _usd(res["totals"]["revenue_at_risk_cents"]),
                   "penalty_exposure_usd": _usd(res["totals"]["penalty_exposure_cents"])},
        "plants": res["plants"],
        "reduced_supply": [{"plant": c["plant"], "component": c["component"], "stockout_day": c["stockout_day"],
                            "unmet_units_at_horizon": c["unmet_units_at_horizon"]}
                           for c in res["components"] if c["reduced"]],
        "projected_late_orders": [{"order_id": o["order_id"], "plant": o["plant"], "product": o["product"],
                                   "need_day": o["need_day"], "late_days": o["late_days"],
                                   "beyond_horizon": o["beyond_horizon"], "strategic": o["tier"] == "strategic"}
                                  for o in late[:25]],
        "wording": "exposed = connected to the disruption; projected_late = the do-nothing projection says late",
    }
    for k in ("revenue_at_risk_cents", "penalty_exposure_cents"):
        summary["totals"].pop(k)
    ctx.add_result("project_shortages", summary, res)
    return summary


def compute_true_capacity(ctx: RunContext, component_id: str, plant_id: str) -> dict[str, Any]:
    require_ids(ctx, [component_id], ("Component",))
    require_ids(ctx, [plant_id], ("Plant",))
    cap = _true_capacity(ctx.graph, component_id, plant_id, run_id=ctx.run_id)
    summary = {"component": component_id, "plant": plant_id, "naive_wk": cap["naive_wk"], "true_wk": cap["true_wk"],
               "healthy_network_wk": cap["nominal_wk"], "bottleneck": [b["what"] + f" ({b['cap']}/wk)"
                                                                       for b in cap["bottleneck"]],
               "sources": [{"site": s["site"], "clean_wk": s["clean_wk"], "nominal_wk": s["nominal_wk"]}
                           for s in cap["sites"]],
               "units": "units of the component per week", "warnings": cap["warnings"]}
    ctx.add_result("compute_true_capacity", summary, cap)
    return summary


# ---------------------------------------------------------------------------
# Recover
# ---------------------------------------------------------------------------

def find_alternatives(ctx: RunContext, component_id: str, plant_id: str) -> dict[str, Any]:
    require_ids(ctx, [component_id], ("Component",))
    require_ids(ctx, [plant_id], ("Plant",))
    alts = _find_alternatives(ctx.graph, component_id, plant_id, HORIZON, run_id=ctx.run_id)

    def ev(paths: list[list[str]]) -> list[str]:
        return [ctx.add_evidence(p) for p in paths]

    summary = {
        "component": component_id, "plant": plant_id,
        "accepted": [{"site": a["site"], "component": a["component"], "price_usd": _usd(a["price_cents"]),
                      "usable_wk": a["usable_wk"], "lead_days": a["lead_days"], "sea_days": a["transit_days"],
                      "air_days": a["air_transit_days"], "exposure_warning": a["exposure_warning"],
                      "reduced": a["reduced"], "evidence_ids": ev(a["tainted_paths"])} for a in alts["accepted"]],
        "rejected": [{"site": r["site"], "component": r["component"], "price_usd": _usd(r["price_cents"]),
                      "reason": r["reason"], "detail": r["detail"], "evidence_ids": ev(r["tainted_paths"])}
                     for r in alts["rejected"]],
        "rule": "exposure is a warning; a source is rejected only when its remaining clean capacity is 0",
    }
    ctx.add_result("find_alternatives", summary, alts)
    return summary


def simulate_strategies(ctx: RunContext, budget_usd: int | None = None) -> dict[str, Any]:
    if not ctx.incident_id:
        raise ToolInputError("declare the incident first")
    budget = budget_usd * 100 if budget_usd else ctx.budget_cents
    sim = _simulate(ctx.graph, ctx.incident_id, run_id=ctx.run_id, horizon=HORIZON, budget_cents=budget)
    ctx.plans = sim["plans"]
    rows = []
    for r in sim["strategies"]:
        plan = sim["plans"].get(r["strategy"])
        rows.append({
            "strategy_id": r["strategy"], "name": r["name"], "on_time": f"{r['on_time']}/{r['orders']}",
            "late": r["late"], "days_late": r["days_late"], "penalty_usd": _usd(r["penalty_cents"]),
            "spend_usd": _usd(r["spend_cents"]), "net_benefit_usd": _usd(r["net_benefit_cents"]),
            "avoided_penalty_usd": _usd(r["avoided_penalty_cents"]),
            "revenue_protected_usd": _usd(r["revenue_protected_cents"]),
            "protected_projected": r["protected_projected"], "protected_but_late": r["protected_but_late"],
            "rate_planned_vs_realized_wk": [r["planned_rate_wk"], r["realized_rate_wk"]],
            "invariants": "all pass" if r["verification"]["ok"] else f"FAIL {r['verification']['failed']}",
            "purchase_orders": [f"{p['site_id']} {p['component_id']}->{p['plant_id']} {p['rate_wk']}/wk x{p['qty']} "
                                f"{p['mode']}" for p in (plan or {}).get("pos", [])],
        })
    summary = {"budget_usd": _usd(budget), "strategies": rows, "default_recommendation": sim["recommended"],
               "note": "each plan was executed in its own GRAPH.COPY sandbox with joint upstream rationing"}
    ctx.add_result("simulate_strategies", summary, {k: v for k, v in sim.items() if k != "plans"})
    return summary


# ---------------------------------------------------------------------------
# Act
# ---------------------------------------------------------------------------

def flag_orders_at_risk(ctx: RunContext, order_ids: list[str], reason: str) -> dict[str, Any]:
    require_ids(ctx, order_ids, ("Order",))
    n = run_query("agent/flag_orders", {"order_ids": sorted(set(order_ids)), "reason": reason[:200]},
                  ro=False, graph=ctx.graph)[0]["flagged"]
    summary = {"flagged": n, "order_ids": sorted(set(order_ids)), "policy": "auto (reversible, internal)"}
    ctx.add_result("flag_orders_at_risk", summary, summary)
    return summary


def submit_plan_for_approval(ctx: RunContext, strategy_id: str, rationale: str,
                             evidence_ids: list[str] | None = None) -> dict[str, Any]:
    plan = ctx.plans.get(strategy_id)
    if plan is None:
        raise ToolInputError(f"unknown strategy {strategy_id!r}; run simulate_strategies first "
                             f"(available: {sorted(ctx.plans)})")
    if not plan["pos"]:
        raise ToolInputError(f"{strategy_id} commits nothing; there is nothing to approve")
    bad = [e for e in evidence_ids or [] if e not in ctx.evidence]
    if bad:
        raise ToolInputError(f"unknown evidence ids {bad}; cite ids returned by tools in this run")
    res = propose_decision(ctx.graph, ctx.incident_id, plan, rationale=rationale[:1000])
    if res["outcome"] != "ok":
        raise ToolInputError(f"{res['outcome']}: {res}")
    ctx.pending = plan
    summary = {"decision_id": plan["decision_id"], "strategy_id": strategy_id, "status": "awaiting_approval",
               "plan_hash": plan["plan_hash"], "spend_usd": _usd(plan["spend_cents"]),
               "purchase_orders": len(plan["pos"]), "orders_to_protect": len(plan["protected_orders"]),
               "next": "A human now approves or rejects. Do not call more tools until you hear back."}
    ctx.add_result("submit_plan_for_approval", summary, {"plan": plan, "rationale": rationale})
    return summary


# ---------------------------------------------------------------------------
# Verify and report
# ---------------------------------------------------------------------------

def verify_execution(ctx: RunContext, decision_id: str) -> dict[str, Any]:
    plan = ctx.pending if ctx.pending and ctx.pending["decision_id"] == decision_id else None
    if plan is None:
        raise ToolInputError(f"{decision_id} is not this run's approved decision")
    ver = _verify(ctx.graph, plan, ctx.receipt, run_id=ctx.run_id)
    after = _project(ctx.graph, HORIZON)["totals"]
    summary = {"decision_id": decision_id, "all_pass": ver["ok"], "failed": ver["failed"],
               "checks": [{"id": c["id"], "name": c["name"], "ok": c["ok"]} for c in ver["checks"]],
               "receipt": (ctx.receipt or {}).get("summary"),
               "after": {"orders": after["orders"], "projected_late": after["projected_late"]},
               "wording": "protected (projected): POs committed, parts not yet received"}
    ctx.add_result("verify_execution", summary, ver)
    return summary


def record_lessons(ctx: RunContext, incident_id: str, lessons: list[dict[str, Any]]) -> dict[str, Any]:
    _need_incident(ctx, incident_id)
    ids = sorted({e for l in lessons for e in l.get("entity_ids", [])})
    if ids:
        require_ids(ctx, ids)
    involved = ids
    memory.record_incident({"id": incident_id, "title": ctx.alert_text[:120] or incident_id, "outcome": "recorded"},
                           [{"id": e, "kind": "entity", "name": e, "role": "involved"} for e in involved])
    lesson_ids = memory.record_lessons(incident_id, [{"text": l["text"][:500], "entity_ids": l.get("entity_ids", []),
                                                      "evidence": ",".join(l.get("evidence_ids", []))}
                                                     for l in lessons])
    summary = {"incident_id": incident_id, "lesson_ids": lesson_ids, "graph": "memory"}
    ctx.add_result("record_lessons", summary, summary)
    return summary


def _resolve_ref(ctx: RunContext, ref: str) -> bool:
    """'R-03.totals.projected_late' must resolve to a value in this run's results."""
    head, *path = ref.split(".")
    node: Any = ctx.results.get(head)
    for key in path:
        if isinstance(node, dict) and key in node:
            node = node[key]
        elif isinstance(node, list) and key.isdigit() and int(key) < len(node):
            node = node[int(key)]
        else:
            return False
    return node is not None


def submit_incident_report(ctx: RunContext, headline: str, outcome: str, claims: list[dict[str, Any]],
                           decision_id: str | None = None, open_risks: list[str] | None = None,
                           lessons: list[str] | None = None) -> dict[str, Any]:
    errors = []
    if outcome not in OUTCOMES:
        errors.append(f"outcome must be one of {OUTCOMES}")
    for i, c in enumerate(claims):
        if c.get("type") not in CLAIM_TYPES:
            errors.append(f"claim {i}: type must be one of {CLAIM_TYPES}")
        cited = [e for e in c.get("evidence_ids", [])]
        for e in cited:
            if e not in ctx.evidence:
                errors.append(f"claim {i}: evidence id {e} was not returned by any tool in this run")
        on_paths = {n for e in cited if e in ctx.evidence for n in ctx.evidence[e]}
        for ent in c.get("entities", []):
            if c.get("type") in ("depends_on", "exposed", "rejected") and ent not in on_paths:
                errors.append(f"claim {i}: {ent} is not on any cited evidence path {cited}")
            elif ent not in ctx.seen_ids and ent not in on_paths:
                errors.append(f"claim {i}: {ent} does not appear in this run's tool results")
        for ref in c.get("metric_refs", []):
            if not _resolve_ref(ctx, ref):
                errors.append(f"claim {i}: metric_ref {ref} does not resolve in this run's results")
        for found in GUARDED_ID.findall(c.get("text", "")):
            if found not in ctx.seen_ids:
                errors.append(f"claim {i}: text mentions {found}, which no tool returned (entity guard)")
    for found in GUARDED_ID.findall(headline):
        if found not in ctx.seen_ids:
            errors.append(f"headline mentions {found}, which no tool returned (entity guard)")
    if decision_id and (not ctx.pending or ctx.pending["decision_id"] != decision_id):
        errors.append(f"decision_id {decision_id} is not this run's decision")
    if errors:
        raise ToolInputError("report rejected; fix and resubmit:\n- " + "\n- ".join(errors[:20]))
    ctx.report = {"headline": headline, "outcome": outcome, "claims": claims, "decision_id": decision_id,
                  "open_risks": open_risks or [], "lessons": lessons or []}
    summary = {"accepted": True, "claims": len(claims), "outcome": outcome}
    ctx.add_result("submit_incident_report", summary, {"report": ctx.report})
    return summary


CATALOGUE = [
    resolve_entities, declare_incident, get_entity_context, recall_history, trace_exposure,
    explain_shared_dependencies, project_shortages, compute_true_capacity, find_alternatives,
    simulate_strategies, flag_orders_at_risk, submit_plan_for_approval, verify_execution, record_lessons,
    submit_incident_report,
]
GATES = {"submit_plan_for_approval"}
STRATEGIES = sorted(PRESETS)
