"""Container start-up: build world:pristine if it is missing, and make sure world:live exists.

Unlike `make seed`, this never rebuilds an existing world, so a restart keeps the live demo state
(and the memory graph is never touched).
"""

from __future__ import annotations

import sys

from domino.config import settings
from domino.graph.client import get_db
from domino.graph.lifecycle import build_pristine, reset_live
from domino.seed.generator import generate


def main() -> int:
    graphs = set(get_db().list_graphs())
    if settings.world_graph_pristine not in graphs:
        build_pristine(generate(settings.world_seed), settings.world_graph_pristine)
        print(f"built {settings.world_graph_pristine} from seed {settings.world_seed}")
    if settings.world_graph_live not in graphs:
        reset_live()
        print(f"copied {settings.world_graph_pristine} -> {settings.world_graph_live}")
    print("world ready")
    return 0


if __name__ == "__main__":
    sys.exit(main())
