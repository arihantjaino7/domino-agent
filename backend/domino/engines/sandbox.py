"""Sandbox simulation. Pure and deterministic; no LLM.

For each strategy: GRAPH.COPY the live world to `sandbox:<run>:<S>`, apply the plan with the SAME
executor code used for real execution, project shortages there (committed POs arrive at the rate the
upstream can jointly support, after proportional rationing), run the verifier, then drop the fork.
With `memory_graph`, the balanced preset ranks sources by the reliability learned from past deliveries;
the result lists each learned value and the ranking it changed. Same world and memory, same result.
"""

from __future__ import annotations

from typing import Any

from domino.allocators.greedy import allocate, build_problem, reliability_effects
from domino.allocators.strategies import DEFAULT_BUDGET_CENTS, PRESETS, RECOMMENDED
from domino.engines.executor import approve_decision, execute_plan, propose_decision
from domino.engines.shortage import project_shortages
from domino.engines.verifier import verify_execution
from domino.graph.lifecycle import copy_graph, drop_graph
from domino.graph.run_query import run_query


def world_version(graph: str) -> int:
    return run_query("decision/get", {"decision_id": ""}, graph=graph)[0]["world_version"]


def decision_id(incident_id: str, strategy: str, version: int) -> str:
    return f"DEC-{incident_id}-{strategy}-v{version}"


def score(projection: dict[str, Any], baseline: dict[str, Any], plan: dict[str, Any] | None) -> dict[str, Any]:
    late_before = {o["order_id"] for o in baseline["orders"] if o["status"] == "projected_late"}
    by_id = {o["order_id"]: o for o in projection["orders"]}
    late = [o for o in projection["orders"] if o["status"] == "projected_late"]
    late_ids = {o["order_id"] for o in late}
    protected = plan["protected_orders"] if plan else []
    spend = plan["spend_cents"] if plan else 0
    penalty = sum(o["penalty_cents"] for o in late)
    base_penalty = baseline["totals"]["penalty_exposure_cents"]
    planned = sum(p["rate_wk"] for p in projection["pos"])
    realized = sum(p["realized_rate_wk"] for p in projection["pos"])
    return {
        "orders": len(projection["orders"]),
        "on_time": len(projection["orders"]) - len(late),
        "late": len(late),
        "days_late": sum(o["late_days"] for o in late),
        "penalty_cents": penalty,
        "revenue_protected_cents": sum(by_id[o]["value_cents"] for o in late_before - late_ids if o in by_id),
        "spend_cents": spend,
        "suppliers": sorted({p["site_id"] for p in plan["pos"]}) if plan else [],
        "protected_projected": len(protected),
        "protected_but_late": sorted(set(protected) & late_ids),
        "planned_rate_wk": planned, "realized_rate_wk": realized,
        "avoided_penalty_cents": base_penalty - penalty,
        "net_benefit_cents": base_penalty - penalty - spend,
    }


def simulate_strategies(live: str, incident_id: str, run_id: str = "local", horizon: int = 42,
                        budget_cents: int = DEFAULT_BUDGET_CENTS, strategies: list[str] | None = None,
                        memory_graph: str | None = None) -> dict[str, Any]:
    problem = build_problem(live, horizon, budget_cents, run_id=run_id, memory_graph=memory_graph)
    version = world_version(live)
    baseline = problem["baseline"]
    rows, plans = [], {}
    for s in strategies or list(PRESETS):
        if PRESETS[s]["mode"] is None:
            rows.append({"strategy": s, "name": PRESETS[s]["name"], **score(baseline, baseline, None),
                         "verification": {"ok": True, "failed": []}})
            continue
        plan = allocate(problem, s, decision_id(incident_id, s, version), version)
        plans[s] = plan
        fork = f"sandbox:{run_id}:{s}"
        copy_graph(live, fork)
        try:
            propose_decision(fork, incident_id, plan, rationale=f"sandbox {s}")
            approve_decision(fork, plan, approved_by="sandbox")
            receipt = execute_plan(fork, plan)
            projection = project_shortages(fork, horizon)
            verification = verify_execution(fork, plan, receipt, run_id=f"{run_id}-{s}")
        finally:
            drop_graph(fork)
        rows.append({"strategy": s, "name": PRESETS[s]["name"], **score(projection, baseline, plan),
                     "receipt": receipt.get("summary", receipt.get("outcome")),
                     "verification": {"ok": verification["ok"], "failed": verification["failed"],
                                      "checks": verification["checks"]}})
    return {"incident_id": incident_id, "world_version": version, "budget_cents": budget_cents,
            "recommended": RECOMMENDED, "strategies": rows, "plans": plans,
            "learned_reliability": problem["learned"], "ranking_changes": reliability_effects(problem)}
