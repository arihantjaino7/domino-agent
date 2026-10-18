"""A scripted stand-in for the model: offline, free, deterministic.

It drives the real loop, the real MCP tools and the real approval path with a fixed investigation
script, reading ids from the tool results like a model would. It exists to test the plumbing
(`make demo-headless DRY_RUN=1`, and the M6 tests) without spending API credit. It is NOT the
agent: it makes no judgement calls, and its report is template text built only from tool results.
"""

from __future__ import annotations

import json
from typing import Any

from anthropic.types.beta import BetaMessage

TERMS = {"monsoon": ["Ayutthaya", "Chao Phraya Basin"], "panel_fire": ["Lumenvue", "Suzhou"],
         "non_event": ["Antwerp"]}
INCIDENT = {"monsoon": ("flood", "Monsoon flooding", 28), "panel_fire": ("fire", "Panel plant fire", 14)}
PREFER = ("HazardZone", "Site", "Region")


class _Stream:
    def __init__(self, msg: BetaMessage) -> None:
        self._msg = msg

    async def __aenter__(self) -> "_Stream":
        return self

    async def __aexit__(self, *exc: Any) -> None:
        return None

    async def get_final_message(self) -> BetaMessage:
        return self._msg


class _Messages:
    def __init__(self, owner: "ScriptedClient") -> None:
        self._owner = owner

    def stream(self, **params: Any) -> _Stream:
        self._owner.requests.append(params)
        return _Stream(self._owner.next_message(params["messages"]))


class _Beta:
    def __init__(self, owner: "ScriptedClient") -> None:
        self.messages = _Messages(owner)


class ScriptedClient:
    """Duck-types `AsyncAnthropic().beta.messages.stream(...)`."""

    def __init__(self, scenario: str, strategy: str = "S4") -> None:
        self.scenario = scenario
        self.strategy = strategy
        self.beta = _Beta(self)
        self.requests: list[dict[str, Any]] = []
        self.results: dict[str, list[dict[str, Any]]] = {}
        self._n = 0

    # -- reading the conversation ------------------------------------------------
    def _absorb(self, messages: list[dict[str, Any]]) -> str:
        """Collect tool results by tool name; return any human note in the last user turn."""
        names = {}
        for m in messages:
            for b in m["content"] if isinstance(m["content"], list) else []:
                if b.get("type") == "tool_use":
                    names[b["id"]] = b["name"]
        self.results = {}
        for m in messages:
            for b in m["content"] if m["role"] == "user" and isinstance(m["content"], list) else []:
                if b.get("type") == "tool_result" and not b.get("is_error"):
                    try:
                        self.results.setdefault(names[b["tool_use_id"]], []).append(json.loads(b["content"]))
                    except (KeyError, ValueError):
                        pass
        last = messages[-1]["content"]
        return " ".join(b.get("text", "") for b in last if b.get("type") == "text")

    def _last(self, tool: str) -> dict[str, Any] | None:
        return self.results.get(tool, [None])[-1]

    # -- building replies ---------------------------------------------------------
    def _msg(self, blocks: list[dict[str, Any]], stop: str) -> BetaMessage:
        self._n += 1
        return BetaMessage.model_validate({
            "id": f"msg_scripted_{self._n}", "type": "message", "role": "assistant", "model": "scripted",
            "content": blocks, "stop_reason": stop, "stop_sequence": None,
            "usage": {"input_tokens": 0, "output_tokens": 0}})

    def _call(self, *calls: tuple[str, dict[str, Any]]) -> BetaMessage:
        blocks = [{"type": "tool_use", "id": f"toolu_{self._n}_{i}", "name": n, "input": a}
                  for i, (n, a) in enumerate(calls)]
        return self._msg(blocks, "tool_use")

    def _done(self, text: str) -> BetaMessage:
        return self._msg([{"type": "text", "text": text}], "end_turn")

    def next_message(self, messages: list[dict[str, Any]]) -> BetaMessage:
        note = self._absorb(messages)
        if self._last("submit_incident_report"):
            return self._done("Report submitted.")
        resolved = self._last("resolve_entities")
        if resolved is None:
            return self._call(("resolve_entities", {"terms": TERMS[self.scenario]}))
        cands = [c for r in resolved["results"] for c in r["candidates"]]
        if not cands:
            return self._call(("submit_incident_report", {
                "headline": "The alert names places that are not in the graph; no exposure can be traced.",
                "outcome": "not_in_graph",
                "claims": [{"type": "not_in_graph", "text": "None of the alert's places resolve to graph entities. "
                            "This means they are not modelled, which is not the same as safe.",
                            "entities": [], "evidence_ids": [], "metric_refs": [resolved["result_ref"] + ".results"]}],
                "open_risks": ["The location may matter through links the graph does not model."]}))
        declared = self._last("declare_incident")
        if declared is None:
            best = sorted(cands, key=lambda c: (PREFER.index(c["label"]) if c["label"] in PREFER else 9, -c["score"]))[0]
            kind, title, days = INCIDENT[self.scenario]
            return self._call(("declare_incident", {"entity_ids": [best["id"]], "kind": kind, "title": title,
                                                    "duration_days": days, "capacity_factor": 0.0}))
        inc = declared["incident_id"]
        if self._last("trace_exposure") is None:
            return self._call(("trace_exposure", {"incident_id": inc}))
        traced = self._last("trace_exposure")
        on_paths = sorted({n for e in traced["evidence"] for n in e["path"] if n.startswith("S-")})
        if on_paths and self._last("recall_history") is None:
            return self._call(("recall_history", {"entity_ids": on_paths}))
        if self._last("project_shortages") is None:
            return self._call(("project_shortages", {}))
        short = self._last("project_shortages")
        pairs = [(r["component"], r["plant"]) for r in short["reduced_supply"]]
        if self._last("find_alternatives") is None and pairs:
            calls = []
            for comp, plant in pairs:
                calls += [("find_alternatives", {"component_id": comp, "plant_id": plant}),
                          ("compute_true_capacity", {"component_id": comp, "plant_id": plant})]
            return self._call(*calls)
        if self._last("simulate_strategies") is None:
            return self._call(("simulate_strategies", {}))
        trace = self._last("trace_exposure")
        evidence = [e["id"] for e in trace["evidence"]]
        submitted = self.results.get("submit_plan_for_approval", [])
        if "REJECTED" in note and self.strategy == "S4":
            self.strategy = "S3"
            return self._call(("submit_plan_for_approval", {"strategy_id": "S3", "rationale": "Re-plan after "
                               "rejection: max-service plan.", "evidence_ids": evidence}))
        if not submitted:
            sim = self._last("simulate_strategies")
            learned = sim.get("ranking_changes") or [r["why"] for r in sim.get("learned_reliability", [])]
            return self._call(("submit_plan_for_approval", {
                "strategy_id": self.strategy, "evidence_ids": evidence,
                "rationale": "Protects the most penalty-weighted orders within budget in the sandbox comparison."
                             + (" Learned from past deliveries: " + "; ".join(learned) + "." if learned else "")}))
        if "could not proceed" in note:  # approval failed (e.g. the world changed): stop instead of guessing
            return self._done("The approval could not proceed because the world changed; a new run is needed.")
        decision = submitted[-1]["decision_id"]
        if self._last("verify_execution") is None:
            return self._call(("verify_execution", {"decision_id": decision}))
        sites = sorted({n for e in trace["evidence"] for n in e["path"] if n.startswith("S-")})
        if self._last("record_lessons") is None:
            return self._call(("record_lessons", {"incident_id": inc, "lessons": [{
                "text": "A single upstream site fed several tier-1 suppliers; check FEEDS paths, not tier-1 lists.",
                "entity_ids": sites, "evidence_ids": evidence[:1]}]}))
        claims = [{"type": "exposed", "text": f"{len(trace['multi_tier']['tier1_sites'])} tier-1 suppliers are "
                   "exposed through upstream FEEDS paths.", "entities": trace["evidence"][0]["path"][:2],
                   "evidence_ids": evidence[:1], "metric_refs": [trace["result_ref"] + ".multi_tier.exposed_tier1"]},
                  {"type": "late", "text": "The do-nothing projection has orders arriving late.", "entities": [],
                   "evidence_ids": [], "metric_refs": [short["result_ref"] + ".totals.projected_late"]}]
        for alt in self.results.get("find_alternatives", []):
            for r in alt["rejected"]:
                claims.append({"type": "rejected", "text": f"{r['site']} was rejected: {r['reason']}.",
                               "entities": [r["site"]] if r["evidence_ids"] else [],
                               "evidence_ids": r["evidence_ids"], "metric_refs": []})
        return self._call(("submit_incident_report", {
            "headline": f"{inc}: exposure traced, plan {decision} approved and verified.",
            "outcome": "answered_with_path", "claims": claims, "decision_id": decision,
            "open_risks": ["Protected orders are projected: parts are not yet received."]}))
