"""`make seed`: generate the world from WORLD_SEED, build world:pristine, copy it to world:live."""

from __future__ import annotations

import sys
import time

from domino.config import settings
from domino.graph.lifecycle import build_pristine, graph_counts, reset_live
from domino.seed.generator import generate
from domino.seed.world import EDGE_TYPES, NODE_GROUPS


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    t0 = time.perf_counter()
    world = generate(settings.world_seed)
    t_gen = time.perf_counter() - t0
    result = build_pristine(world, settings.world_graph_pristine)
    t_load = time.perf_counter() - t0 - t_gen
    live = reset_live(settings.world_graph_pristine, settings.world_graph_live)
    counts = graph_counts(live)
    total = time.perf_counter() - t0

    print(f"DOMINO world  seed={world.seed}  fingerprint={world.fingerprint()[:16]}")
    print(f"  {settings.world_graph_pristine}: schema applied (PurchaseOrder.id constraint "
          f"{result['schema']['constraint']}), loaded and checked")
    print(f"  {live}: GRAPH.COPY of {settings.world_graph_pristine}")
    print()
    print("  Nodes                    Edges")
    nodes = [(g, counts.get(g, 0)) for g in NODE_GROUPS] + [("Meta", counts.get("Meta", 0))]
    edges = [(t, counts.get(t, 0)) for t in EDGE_TYPES if counts.get(t, 0)]
    for i in range(max(len(nodes), len(edges))):
        left = f"  {nodes[i][0]:<14}{nodes[i][1]:>6}" if i < len(nodes) else " " * 22
        right = f"    {edges[i][0]:<17}{edges[i][1]:>6}" if i < len(edges) else ""
        print(left + right)
    n_nodes = sum(n for _, n in nodes)
    n_edges = sum(n for _, n in edges)
    print(f"  {'TOTAL':<14}{n_nodes:>6}    {'TOTAL':<17}{n_edges:>6}")
    print()
    print(f"✓ seeded in {total:.1f}s (generate {t_gen:.2f}s, load {t_load:.2f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
