"""Per-run server-side state shared by the MCP tools and the agent loop.

The LLM never sees or passes this state. The loop injects `run_id` into every tool call (hidden from
the tool schema the model gets), and tools read and write the run's context here: result refs
(R-01...), evidence paths (E1...), simulated plans, the pending decision and every id seen in results.
External MCP clients that pass no run_id share the "external" context on the live world.
"""

from __future__ import annotations

import re
import threading
from dataclasses import dataclass, field
from typing import Any

from domino.allocators.strategies import DEFAULT_BUDGET_CENTS
from domino.config import settings

# Ids the entity guard checks in narrative text: sites, suppliers, orders, plants.
GUARDED_ID = re.compile(r"\b(?:SUP|SO|PL|S)-[A-Z0-9]+(?:-[A-Z0-9]+)*\b")
ANY_ID = re.compile(r"\b(?:SUP|SO|PL|S|R|Z|P|A|CU|INC|DEC|PO)-[A-Z0-9]+(?:-[A-Z0-9]+)*\b")


@dataclass
class RunContext:
    run_id: str
    graph: str
    budget_cents: int = DEFAULT_BUDGET_CENTS
    alert_text: str = ""
    incident_id: str | None = None
    results: dict[str, dict[str, Any]] = field(default_factory=dict)     # R-xx -> compact summary
    ui: dict[str, dict[str, Any]] = field(default_factory=dict)          # R-xx -> full payload
    queries: dict[str, list[dict[str, Any]]] = field(default_factory=dict)  # R-xx -> Cypher it ran (drawer)
    evidence: dict[str, list[str]] = field(default_factory=dict)         # E-n -> path of ids
    plans: dict[str, dict[str, Any]] = field(default_factory=dict)       # strategy -> plan
    pending: dict[str, Any] | None = None                                # plan awaiting approval
    receipt: dict[str, Any] | None = None
    delivery: dict[str, Any] | None = None                              # fast-forward result, once delivered
    report: dict[str, Any] | None = None
    rejected: dict[str, str] = field(default_factory=dict)              # decision id -> human feedback
    rejected_plans: dict[str, str] = field(default_factory=dict)        # content hash of a rejected plan -> feedback
    approval_failed: dict[str, str] = field(default_factory=dict)       # decision id -> why approval could not run
    memory_ids: dict[str, str] = field(default_factory=dict)            # world incident id -> its memory incident id
    memory_graph: str = field(default_factory=lambda: settings.memory_graph)  # scripted runs use memory:dryrun
    seen_ids: set[str] = field(default_factory=set)
    lock: threading.Lock = field(default_factory=threading.Lock)

    def add_evidence(self, path: list[str]) -> str:
        for eid, p in self.evidence.items():
            if p == path:
                return eid
        eid = f"E{len(self.evidence) + 1}"
        self.evidence[eid] = list(path)
        return eid

    def add_result(self, tool: str, summary: dict[str, Any], ui: dict[str, Any]) -> str:
        ref = f"R-{len(self.results) + 1:02d}"
        tagged = {"result_ref": ref, **summary}
        summary.clear()
        summary.update(tagged)  # the caller returns this same dict, now carrying its result_ref
        self.results[ref] = summary
        self.ui[ref] = {"tool": tool, **ui}
        self.note_ids(summary)
        self.note_ids(ui)
        return ref

    def note_ids(self, obj: Any) -> None:
        if isinstance(obj, str):
            self.seen_ids |= set(ANY_ID.findall(obj))
        elif isinstance(obj, dict):
            for k, v in obj.items():
                self.note_ids(k)
                self.note_ids(v)
        elif isinstance(obj, (list, tuple, set)):
            for v in obj:
                self.note_ids(v)


CONTEXTS: dict[str, RunContext] = {}
_lock = threading.Lock()


def get_context(run_id: str | None) -> RunContext:
    rid = run_id or "external"
    with _lock:
        if rid not in CONTEXTS:
            CONTEXTS[rid] = RunContext(run_id=rid, graph=settings.world_graph_live)
        return CONTEXTS[rid]


def new_context(run_id: str, graph: str, alert_text: str = "", budget_cents: int = DEFAULT_BUDGET_CENTS) -> RunContext:
    with _lock:
        CONTEXTS[run_id] = RunContext(run_id=run_id, graph=graph, alert_text=alert_text, budget_cents=budget_cents)
        return CONTEXTS[run_id]
