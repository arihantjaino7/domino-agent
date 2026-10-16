"""In-memory world: plain node and edge rows, ready for the batched UNWIND loader.

Node groups and edge types match the files in `queries/seed/`. Every value is a
plain int, float, str or bool, so the world can be hashed and compared exactly.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

# Node group -> loader query. The group name is also the primary label.
NODE_GROUPS: dict[str, str] = {
    "Supplier": "seed/nodes_supplier",
    "Site": "seed/nodes_site",
    "Region": "seed/nodes_region",
    "HazardZone": "seed/nodes_hazard_zone",
    "Port": "seed/nodes_port",
    "Plant": "seed/nodes_plant",
    "Component": "seed/nodes_component",
    "Product": "seed/nodes_product",
    "Customer": "seed/nodes_customer",
    "Order": "seed/nodes_order",
}

# Edge type -> (source group(s), target group(s)) for validation. Loader file is seed/edges_<type>.
EDGE_TYPES: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "OPERATES": (("Supplier",), ("Site",)),
    "LOCATED_IN": (("Site", "Port", "Plant"), ("Region",)),
    "IN_ZONE": (("Region",), ("HazardZone",)),
    "MAKES": (("Site",), ("Component",)),
    "MADE_FROM": (("Component",), ("Component",)),
    "FEEDS": (("Site",), ("Site",)),
    "SUPPLIES": (("Site",), ("Plant",)),
    "CAN_SUPPLY": (("Site",), ("Plant",)),
    "REQUIRES": (("Product",), ("Component",)),
    "ALLOWS_ALTERNATE": (("Product",), ("Component",)),
    "BUILDS": (("Plant",), ("Product",)),
    "STOCKS": (("Plant",), ("Component",)),
    "PLACED": (("Customer",), ("Order",)),
    "FOR_PRODUCT": (("Order",), ("Product",)),
    "FULFILLED_AT": (("Order",), ("Plant",)),
    "SHIPS_VIA": (("Site",), ("Port",)),
    "LANE": (("Port",), ("Port",)),
    "DELIVERS_TO": (("Port",), ("Plant",)),
}


@dataclass
class World:
    seed: int
    nodes: dict[str, list[dict[str, Any]]] = field(default_factory=lambda: {g: [] for g in NODE_GROUPS})
    edges: dict[str, list[dict[str, Any]]] = field(default_factory=lambda: {t: [] for t in EDGE_TYPES})

    # ---- building -------------------------------------------------------
    def add_node(self, group: str, **props: Any) -> dict[str, Any]:
        row = {k: v for k, v in props.items() if v is not None}
        self.nodes[group].append(row)
        return row

    def add_edge(self, rel: str, src: str, dst: str, **props: Any) -> dict[str, Any]:
        row = {"src": src, "dst": dst, "props": {k: v for k, v in props.items() if v is not None}}
        self.edges[rel].append(row)
        return row

    # ---- reading --------------------------------------------------------
    def node(self, node_id: str) -> dict[str, Any]:
        for rows in self.nodes.values():
            for r in rows:
                if r["id"] == node_id:
                    return r
        raise KeyError(node_id)

    def edges_of(self, rel: str, src: str | None = None, dst: str | None = None) -> list[dict[str, Any]]:
        return [e for e in self.edges[rel]
                if (src is None or e["src"] == src) and (dst is None or e["dst"] == dst)]

    def counts(self) -> dict[str, int]:
        out = {g: len(rows) for g, rows in self.nodes.items()}
        out.update({t: len(rows) for t, rows in self.edges.items()})
        return out

    @property
    def n_nodes(self) -> int:
        return sum(len(r) for r in self.nodes.values())

    @property
    def n_edges(self) -> int:
        return sum(len(r) for r in self.edges.values())

    def fingerprint(self) -> str:
        """sha256 of the whole world; equal fingerprints mean identical worlds."""
        blob = json.dumps({"nodes": self.nodes, "edges": self.edges}, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(blob.encode()).hexdigest()
