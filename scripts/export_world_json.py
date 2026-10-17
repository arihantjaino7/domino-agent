"""Export raw graph data for evaluation. Read-only; no engine imports or credentials in output."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path

from domino.graph.run_query import run_query


def canonical(data: dict) -> bytes:
    return (json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def export_world(graph: str) -> dict:
    nodes = run_query("eval/nodes", graph=graph)
    edges = run_query("eval/edges", graph=graph)
    for node in nodes:
        node["labels"].sort()
    edges.sort(key=lambda e: (e["src"], e["dst"], e["type"], json.dumps(e["props"], sort_keys=True)))
    return {"format": 1, "nodes": nodes, "edges": edges}


def write_export(data: dict, path: Path) -> str:
    blob = canonical(data)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(gzip.compress(blob, mtime=0) if path.suffix == ".gz" else blob)
    return hashlib.sha256(blob).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--graph", required=True, help="Graph to read; this command never writes to it")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    data = export_world(args.graph)
    digest = write_export(data, args.output)
    print(f"Exported {len(data['nodes'])} nodes, {len(data['edges'])} edges; sha256={digest}")


if __name__ == "__main__":
    main()
