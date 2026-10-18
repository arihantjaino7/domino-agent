"""Strategy presets. Every preset runs the same greedy code.

mode   "naive": tier-1 nominal view. Price only, approved spare as capacity, no taint check,
                no upstream bookkeeping. This is baseline B1, what a tool without the graph does.
       "graph": DOMINO's view. Only sources with remaining clean capacity (max-flow), capped by
                upstream bookkeeping, so shared cell lines are not promised twice.
air    "never" | "when_needed" (sea unless sea is too late) | "always" (fastest).
key    how candidate sources are ranked for each order.
"""

from __future__ import annotations

DEFAULT_BUDGET_CENTS = 25_000_000  # $250,000 recovery budget per decision

PRESETS: dict[str, dict] = {
    "S0": {"name": "Do nothing", "mode": None},
    "S1": {"name": "Naive baseline", "mode": "naive", "air": "never", "key": "price"},
    "S2": {"name": "Lowest cost", "mode": "graph", "air": "never", "key": "price"},
    "S3": {"name": "Max service", "mode": "graph", "air": "always", "key": "speed"},
    "S4": {"name": "DOMINO balanced", "mode": "graph", "air": "when_needed", "key": "balanced"},
}
RECOMMENDED = "S4"
