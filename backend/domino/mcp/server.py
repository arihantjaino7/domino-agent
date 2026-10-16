"""MCP server (official SDK; in mcp 2.x `FastMCP` is called `MCPServer`), mounted at /mcp.

These are thin wrappers over `domino.agent.tools` (CLAUDE.md rule 4). Engines are synchronous, so
each call runs in a worker thread (`asyncio.to_thread`) and never blocks the event loop or SSE.

`run_id` is injected by DOMINO's own agent loop and stripped from the schema the model sees.
External clients (Claude Desktop / Code) can omit it; they then share the "external" context
on the live world. There is no tool that writes Cypher, and `execute_plan` is not exposed.
"""

from __future__ import annotations

import asyncio
from typing import Annotated, Any

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import Field

from domino.agent import tools as T
from domino.agent.context import get_context
from domino.graph.client import ping

mcp = MCPServer(name="domino", instructions=(
    "DOMINO: supply-chain recovery tools over a FalkorDB graph of Kestrel Devices' multi-tier supply chain. "
    "Every number comes from a deterministic engine; ids are validated against the graph."))

RunId = Annotated[str, Field(description="Injected by DOMINO's agent loop; leave empty.")]


async def _call(fn, run_id: str, **kwargs: Any) -> dict[str, Any]:
    ctx = get_context(run_id)

    def work() -> dict[str, Any]:
        with ctx.lock:
            return fn(ctx, **kwargs)

    try:
        return await asyncio.to_thread(work)
    except T.ToolInputError as exc:  # surfaces as is_error: true with this message, so the agent can recover
        raise ToolError(str(exc)) from exc


@mcp.tool()
def health() -> dict:
    """Check that DOMINO can reach FalkorDB."""
    return ping()


@mcp.tool()
async def resolve_entities(
    terms: Annotated[list[str], Field(description="Place or company names taken from the alert text")],
    run_id: RunId = "",
) -> dict:
    """Find graph entities (regions, hazard zones, sites, ports, plants) for names in an alert.
    Uses exact and fuzzy full-text search. Returns candidates with id, label, country and score, and flags
    ambiguity. No candidates means the name is not modelled in the graph, which is not the same as safe."""
    return await _call(T.resolve_entities, run_id, terms=terms)


@mcp.tool()
async def declare_incident(
    entity_ids: Annotated[list[str], Field(description="Ids of the affected hazard zone, region or site(s)")],
    kind: Annotated[str, Field(description="flood, quake, typhoon, fire, strike, ...")],
    title: Annotated[str, Field(description="Short incident title")],
    duration_days: Annotated[int, Field(description="Expected outage in days (use the alert's estimate)")],
    capacity_factor: Annotated[float, Field(description="Remaining capacity: 0 = fully down, 0.5 = half")] = 0.0,
    run_id: RunId = "",
) -> dict:
    """Record an observed disruption in the graph (policy: automatic, it records a fact). A zone expands to
    its regions and their sites. Returns the incident id and the affected sites."""
    return await _call(T.declare_incident, run_id, entity_ids=entity_ids, kind=kind, title=title,
                       duration_days=duration_days, capacity_factor=capacity_factor)


@mcp.tool()
async def get_entity_context(
    entity_id: Annotated[str, Field(description="Any graph id, e.g. S-VOLT-AYU or PL-BAC")],
    run_id: RunId = "",
) -> dict:
    """Properties of one entity and a summary of its direct neighbours."""
    return await _call(T.get_entity_context, run_id, entity_id=entity_id)


@mcp.tool()
async def recall_history(
    entity_ids: Annotated[list[str], Field(description="Entity ids to look up in institutional memory")],
    run_id: RunId = "",
) -> dict:
    """Past incidents and lessons about these entities from the persistent memory graph, each with the
    date it was learned."""
    return await _call(T.recall_history, run_id, entity_ids=entity_ids)


@mcp.tool()
async def trace_exposure(
    incident_id: Annotated[str, Field(description="Incident id from declare_incident")],
    run_id: RunId = "",
) -> dict:
    """Multi-tier exposure: walks FEEDS paths of any depth from the affected sites to tier-1 suppliers,
    plants, products and open orders. Returns the tier-1-only view for contrast, exposed tier-1 sites and
    evidence paths (E-ids) to cite."""
    return await _call(T.trace_exposure, run_id, incident_id=incident_id)


@mcp.tool()
async def explain_shared_dependencies(
    incident_id: Annotated[str, Field(description="Incident id")],
    run_id: RunId = "",
) -> dict:
    """Affected upstream sites that feed two or more tier-1 suppliers (active or alternate), with evidence:
    proof that apparently independent backups share a hidden dependency."""
    return await _call(T.explain_shared_dependencies, run_id, incident_id=incident_id)


@mcp.tool()
async def project_shortages(
    horizon: Annotated[int, Field(description="Days to project (default 42)")] = 42,
    run_id: RunId = "",
) -> dict:
    """Do-nothing projection, day by day: which orders are merely exposed vs projected late, stockout day
    per plant and part, revenue at risk and late penalties. Includes committed purchase orders."""
    return await _call(T.project_shortages, run_id, horizon=horizon)


@mcp.tool()
async def compute_true_capacity(
    component_id: Annotated[str, Field(description="Component id, e.g. BAT-4S")],
    plant_id: Annotated[str, Field(description="Plant id, e.g. PL-BAC")],
    run_id: RunId = "",
) -> dict:
    """True weekly capacity for a part at a plant, from algo.maxFlow over the whole upstream network,
    vs the naive tier-1 sum, with the bottleneck (min cut)."""
    return await _call(T.compute_true_capacity, run_id, component_id=component_id, plant_id=plant_id)


@mcp.tool()
async def find_alternatives(
    component_id: Annotated[str, Field(description="Component id the plant is short of")],
    plant_id: Annotated[str, Field(description="Plant id")],
    run_id: RunId = "",
) -> dict:
    """Approved alternate sources for a part at a plant. Each is checked for BOM compatibility and for
    disrupted sites upstream; exposure is a warning, and a source is rejected only when its remaining
    clean capacity is 0. Rejections come with a reason and evidence ids."""
    return await _call(T.find_alternatives, run_id, component_id=component_id, plant_id=plant_id)


@mcp.tool()
async def simulate_strategies(
    budget_usd: Annotated[int | None, Field(description="Recovery budget in USD (default 250000)")] = None,
    run_id: RunId = "",
) -> dict:
    """Build every recovery strategy (S0 do nothing, S1 naive baseline, S2 lowest cost, S3 max service,
    S4 DOMINO balanced) and execute each in its own sandbox copy of the graph with joint upstream
    rationing. Returns on-time orders, spend, penalties, net benefit and invariant checks per strategy."""
    return await _call(T.simulate_strategies, run_id, budget_usd=budget_usd)


@mcp.tool()
async def flag_orders_at_risk(
    order_ids: Annotated[list[str], Field(description="Order ids to flag")],
    reason: Annotated[str, Field(description="Why they are at risk")],
    run_id: RunId = "",
) -> dict:
    """Mark orders as at risk (policy: automatic, reversible, internal)."""
    return await _call(T.flag_orders_at_risk, run_id, order_ids=order_ids, reason=reason)


@mcp.tool()
async def submit_plan_for_approval(
    strategy_id: Annotated[str, Field(description="A strategy id from simulate_strategies, e.g. S4")],
    rationale: Annotated[str, Field(description="Why this plan, and the trade-off against the cheapest plan")],
    evidence_ids: Annotated[list[str], Field(description="Evidence ids supporting the plan")] = [],  # noqa: B006
    run_id: RunId = "",
) -> dict:
    """Submit a simulated plan for human approval (purchase commitments always need a human). The run
    pauses until a human approves or rejects; you will then be told the outcome."""
    return await _call(T.submit_plan_for_approval, run_id, strategy_id=strategy_id, rationale=rationale,
                       evidence_ids=evidence_ids)


@mcp.tool()
async def verify_execution(
    decision_id: Annotated[str, Field(description="The approved decision id")],
    run_id: RunId = "",
) -> dict:
    """After execution: invariants V1-V9 against the graph, the execution receipt, and the projection after."""
    return await _call(T.verify_execution, run_id, decision_id=decision_id)


@mcp.tool()
async def record_lessons(
    incident_id: Annotated[str, Field(description="Incident id")],
    lessons: Annotated[list[dict], Field(description="[{text, entity_ids: [...], evidence_ids: [...]}]")],
    run_id: RunId = "",
) -> dict:
    """Write lessons about specific entities to the persistent memory graph (policy: automatic)."""
    return await _call(T.record_lessons, run_id, incident_id=incident_id, lessons=lessons)


@mcp.tool()
async def submit_incident_report(
    headline: Annotated[str, Field(description="One-sentence summary")],
    outcome: Annotated[str, Field(description="answered_with_path | answered_from_memory | not_in_graph | "
                                              "unknown_entity")],
    claims: Annotated[list[dict], Field(description=(
        "[{type: depends_on|exposed|late|rejected|protected|capacity|not_in_graph, text, entities: [ids], "
        "evidence_ids: [E-ids], metric_refs: ['R-03.totals.projected_late', ...]}]"))],
    decision_id: Annotated[str | None, Field(description="Decision id, if a plan was approved")] = None,
    open_risks: Annotated[list[str], Field(description="Risks that remain")] = [],  # noqa: B006
    lessons: Annotated[list[str], Field(description="Lessons learned")] = [],  # noqa: B006
    run_id: RunId = "",
) -> dict:
    """Final structured report. Rejected with errors if a claim cites evidence or metrics that this run's
    tools did not return, or names an entity that is not on its cited paths; fix and resubmit."""
    return await _call(T.submit_incident_report, run_id, headline=headline, outcome=outcome, claims=claims,
                       decision_id=decision_id, open_risks=open_risks, lessons=lessons)
