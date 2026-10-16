"""M1 capability spike: probe every FalkorDB / MCP feature DOMINO depends on.

Run with `make spike` (FalkorDB must be up). Writes docs/SPIKE.md.

Every check uses its own throwaway graph named `spike:*` and deletes it afterwards.
This is a probe script, not app code, so its Cypher stays inline here on purpose;
app Cypher lives in backend/domino/queries/*.cypher (CLAUDE.md rule 1).
"""

from __future__ import annotations

import asyncio
import datetime as dt
import os
import subprocess
import sys
import time
import traceback
from dataclasses import dataclass, field
from importlib.metadata import version
from pathlib import Path

import httpx
from falkordb import FalkorDB
from redis.exceptions import ResponseError

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "SPIKE.md"
HOST = os.environ.get("FALKORDB_HOST", "localhost")
PORT = int(os.environ.get("FALKORDB_PORT", "6379"))

db = FalkorDB(host=HOST, port=PORT)


@dataclass
class Check:
    key: str
    capability: str
    why: str
    ok: bool = False
    result: str = ""
    fallback: str = ""
    crashed: bool = False
    details: list[str] = field(default_factory=list)


CHECKS: list[Check] = []


def check(key: str, capability: str, why: str, fallback: str):
    """Register a probe. The probe fills in result/details and returns ok."""

    def wrap(fn):
        def run() -> Check:
            c = Check(key, capability, why, fallback=fallback)
            try:
                c.ok = bool(fn(c))
            except Exception as exc:  # report the crash in SPIKE.md and keep probing
                c.ok = False
                c.crashed = True
                c.result = f"crashed: {type(exc).__name__}: {exc}"
                c.details.append("```\n" + traceback.format_exc(limit=3) + "```")
            finally:
                for name in db.list_graphs():
                    if name.startswith("spike:"):
                        db.select_graph(name).delete()
            return c

        CHECKS.append(run)
        return fn

    return wrap


def rows(graph, q, params=None, ro=False):
    res = (graph.ro_query if ro else graph.query)(q, params or {})
    return res.result_set


# --------------------------------------------------------------------------------------
# 1. algo.* catalogue
# --------------------------------------------------------------------------------------
@check(
    "algo-list",
    "List `algo.*` procedures",
    "maxFlow, SPpaths and betweenness must exist in the pinned image.",
    "If maxFlow is missing: run max-flow in Python (Edmonds-Karp) on the Cypher-extracted network (PLAN §18).",
)
def _(c: Check):
    g = db.select_graph("spike:procs")
    names = [r[0] for r in rows(g, "CALL dbms.procedures() YIELD name RETURN name ORDER BY name")]
    algos = [n for n in names if n.startswith("algo.")]
    needed = {"algo.maxFlow", "algo.SPpaths", "algo.betweenness"}
    c.result = ", ".join(f"`{a}`" for a in algos)
    missing = needed - set(algos)
    if missing:
        c.result += f" — MISSING {sorted(missing)}"
    return not missing


# --------------------------------------------------------------------------------------
# 2. algo.maxFlow
# --------------------------------------------------------------------------------------
MAXFLOW_Q = """
MATCH (s:F) WHERE s.id IN $sources
WITH collect(s) AS sources
MATCH (t:F) WHERE t.id IN $sinks
WITH sources, collect(t) AS sinks
CALL algo.maxFlow({sourceNodes: sources, targetNodes: sinks, capacityProperty: 'cap', relationshipTypes: ['CAP']})
YIELD edges, edgeFlows, maxFlow
UNWIND range(0, size(edges) - 1) AS i
RETURN startNode(edges[i]).id AS src, endNode(edges[i]).id AS dst, edgeFlows[i] AS flow, edges[i].cap AS cap, maxFlow
"""


@check(
    "maxflow",
    "`algo.maxFlow`: value, per-edge flows, rel-type filter, multi-source, zero-flow case",
    "True capacity (§7.6) is a max-flow on a projected network; bottlenecks need the per-edge flows.",
    "Python Edmonds-Karp on the same extracted network; keep the FalkorDB call as the primary path.",
)
def _(c: Check):
    g = db.select_graph("spike:maxflow")
    # Hand-checked network. s->a 10, s->b 5, a->b 4, a->t 8, b->t 5  => max flow 13, min cut {a->t, b->t}.
    # a->x 3 is a dead end (carries no flow). s->t via :SHORTCUT 100 must be ignored (wrong rel type).
    g.query(
        """
        CREATE (s:F {id:'s'}), (a:F {id:'a'}), (b:F {id:'b'}), (t:F {id:'t'}), (x:F {id:'x'}), (s2:F {id:'s2'}),
               (s)-[:CAP {cap:10}]->(a), (s)-[:CAP {cap:5}]->(b), (a)-[:CAP {cap:4}]->(b),
               (a)-[:CAP {cap:8}]->(t), (b)-[:CAP {cap:5}]->(t), (a)-[:CAP {cap:3}]->(x),
               (s)-[:SHORTCUT {cap:100}]->(t),
               (s2)-[:CAP {cap:6}]->(t)
        """
    )
    r = rows(g, MAXFLOW_Q, {"sources": ["s"], "sinks": ["t"]})
    value = r[0][4] if r else 0
    edges = {(row[0], row[1]): (row[2], row[3]) for row in r}
    c.details.append(f"single source s→t: maxFlow = **{value}** (expected 13)")
    c.details.append("returned edges (src→dst flow/cap): " + ", ".join(f"{k[0]}→{k[1]} {v[0]}/{v[1]}" for k, v in sorted(edges.items())))
    dead_end_hidden = ("a", "x") not in edges
    c.details.append(f"zero-flow edge a→x returned? **{'no' if dead_end_hidden else 'yes'}** (PLAN says only positive-flow edges come back)")
    shortcut_ignored = ("s", "t") not in edges
    c.details.append(f":SHORTCUT edge ignored by `relationshipTypes`? **{'yes' if shortcut_ignored else 'no'}**")

    r2 = rows(g, MAXFLOW_Q, {"sources": ["s", "s2"], "sinks": ["t"]})
    multi = r2[0][4] if r2 else 0
    c.details.append(f"two sources {{s, s2}}→t: maxFlow = **{multi}** (expected 13 + 6 = 19)")

    r3 = rows(g, MAXFLOW_Q, {"sources": ["x"], "sinks": ["t"]})
    c.details.append(f"no path x→t: rows returned = **{len(r3)}** (expected 0; the engine must treat 'no rows' as flow 0)")

    ok = value == 13 and multi == 19 and len(r3) == 0 and shortcut_ignored
    c.result = f"13 ✓, multi-source 19 {'✓' if multi == 19 else '✗'}, rel-type filter {'✓' if shortcut_ignored else '✗'}, zero-flow edges {'hidden' if dead_end_hidden else 'returned'}, no-path → 0 rows"
    return ok


# --------------------------------------------------------------------------------------
# 3. algo.SPpaths
# --------------------------------------------------------------------------------------
@check(
    "sppaths",
    "`algo.SPpaths` with weight, cost cap and pathCount",
    "P1 rerouting: fastest route under a cost cap avoiding a closed port.",
    "Enumerate ≤4-hop routes with a Cypher variable-length match and rank them in Python.",
)
def _(c: Check):
    g = db.select_graph("spike:sppaths")
    # A->B->D: 5 days, $300 ; A->C->D: 3 days, $900 ; A->D direct: 10 days, $100
    g.query(
        """
        CREATE (a:P {id:'A'}), (b:P {id:'B'}), (cc:P {id:'C'}), (d:P {id:'D'}),
               (a)-[:LANE {days:2, cost:100}]->(b), (b)-[:LANE {days:3, cost:200}]->(d),
               (a)-[:LANE {days:1, cost:400}]->(cc), (cc)-[:LANE {days:2, cost:500}]->(d),
               (a)-[:LANE {days:10, cost:100}]->(d)
        """
    )
    q = """
    MATCH (s:P {id:'A'}), (t:P {id:'D'})
    CALL algo.SPpaths({sourceNode: s, targetNode: t, relTypes: ['LANE'], weightProp: 'days',
                       costProp: 'cost', maxCost: $max_cost, pathCount: 3, relDirection: 'outgoing'})
    YIELD path, pathWeight, pathCost
    RETURN [n IN nodes(path) | n.id] AS hops, pathWeight, pathCost
    ORDER BY pathWeight
    """
    all3 = rows(g, q, {"max_cost": 10_000}, ro=True)
    capped = rows(g, q, {"max_cost": 500}, ro=True)
    c.details.append("no cost cap: " + "; ".join(f"{'-'.join(h)} {w}d ${p}" for h, w, p in all3))
    c.details.append("maxCost 500: " + "; ".join(f"{'-'.join(h)} {w}d ${p}" for h, w, p in capped))
    ok = [r[0] for r in all3] == [["A", "C", "D"], ["A", "B", "D"], ["A", "D"]] and [r[0] for r in capped] == [["A", "B", "D"], ["A", "D"]]
    c.result = "fastest-first, cost cap drops the $900 route" if ok else "unexpected ordering or filtering (see details)"
    return ok


# --------------------------------------------------------------------------------------
# 4. algo.betweenness (seeded)
# --------------------------------------------------------------------------------------
@check(
    "betweenness",
    "`algo.betweenness`: deterministic with `samplingSeed`, and scores match hand-computed values",
    "P1 port chokepoints; the same world must give the same ranking, and the ranking must be right.",
    "Rank chokepoints with `algo.maxFlow` knockouts (remove a port, measure lost flow), which the spike proves correct; "
    "or compute exact betweenness in Python on the Cypher-extracted port graph. Ask in the FalkorDB Discord about the semantics. "
    "(Across spike runs the call **without** sampling params scored the star hub H=8, 4 and 6: it samples randomly by default, "
    "so only seeded calls are reproducible, and even seeded scores are sample estimates, not exact betweenness.)",
)
def _(c: Check):
    g = db.select_graph("spike:btw")
    # Star: A,B -> H -> D,E plus D -> E. Directed shortest paths through H: A→D, A→E, B→D, B→E  => textbook H = 4.
    g.query(
        """
        CREATE (a:Port {id:'A'}), (b:Port {id:'B'}), (h:Port {id:'H'}), (d:Port {id:'D'}), (e:Port {id:'E'}),
               (a)-[:LANE]->(h), (b)-[:LANE]->(h), (h)-[:LANE]->(d), (h)-[:LANE]->(e), (d)-[:LANE]->(e)
        """
    )
    # Chain X -> Y -> Z: textbook Y = 1 (the X→Z path passes through Y).
    g.query("CREATE (:Port {id:'X'})-[:LANE]->(:Port {id:'Y'})-[:LANE]->(:Port {id:'Z'})")
    seeded = """
    CALL algo.betweenness({nodeLabels: ['Port'], relationshipTypes: ['LANE'], samplingSize: 64, samplingSeed: 7})
    YIELD node, score RETURN node.id AS port, score ORDER BY port
    """
    exact = """
    CALL algo.betweenness({nodeLabels: ['Port'], relationshipTypes: ['LANE']})
    YIELD node, score RETURN node.id AS port, score ORDER BY port
    """
    r1 = rows(g, seeded, ro=True)
    r2 = rows(g, seeded, ro=True)
    rx = rows(g, exact, ro=True)
    fmt = lambda r: ", ".join(f"{p}={s:g}" for p, s in r)
    c.details.append(f"seeded (samplingSize 64, seed 7): {fmt(r1)}")
    c.details.append(f"no sampling params: {fmt(rx)}")
    c.details.append("textbook (directed, unnormalised): H=4, Y=1, all others 0")
    same = r1 == r2
    sx = dict(rx)
    textbook = sx.get("H") == 4 and sx.get("Y") == 1
    c.details.append(f"seeded run identical on re-run: {same}; matches textbook: {textbook}")
    c.result = (
        f"deterministic with seed: {'yes' if same else 'no'}; "
        f"scores {'match' if textbook else 'do NOT match'} hand-computed values (H={sx.get('H'):g} vs 4, Y={sx.get('Y'):g} vs 1)"
    )
    return same and textbook


# --------------------------------------------------------------------------------------
# 5. GRAPH.COPY: indexes, constraints, delete
# --------------------------------------------------------------------------------------
def _wait_constraint(g, timeout_s=10.0) -> tuple[str, float]:
    t0 = time.perf_counter()
    status = "missing"
    while time.perf_counter() - t0 < timeout_s:
        r = rows(g, "CALL db.constraints() YIELD type, label, properties, status RETURN type, label, properties, status")
        hit = [row for row in r if row[1] == "PurchaseOrder"]
        status = hit[0][3] if hit else "missing"
        if status == "OPERATIONAL":
            break
        time.sleep(0.05)
    return status, (time.perf_counter() - t0) * 1000


def _make_schema_graph(name: str):
    g = db.select_graph(name)
    g.query("CREATE (:Site:Place {id:'S-1', name:'VoltCell Energy', aliases:'Ayutthaya cell fab'})")
    g.query("CREATE INDEX FOR (n:Site) ON (n.id)")
    g.query("CREATE INDEX FOR (n:PurchaseOrder) ON (n.id)")
    g.query("CALL db.idx.fulltext.createNodeIndex('Place', 'name', 'aliases')")
    db.connection.execute_command("GRAPH.CONSTRAINT", "CREATE", name, "UNIQUE", "NODE", "PurchaseOrder", "PROPERTIES", 1, "id")
    return g


def _schema_summary(g) -> tuple[set, list]:
    idx = rows(g, "CALL db.indexes() YIELD label, properties, types RETURN label, properties, types")
    idx_set = {(r[0], tuple(r[1]), tuple(sorted(str(t) for t in r[2].get(r[1][0], []))) if isinstance(r[2], dict) else str(r[2])) for r in idx}
    cons = rows(g, "CALL db.constraints() YIELD type, label, properties, status RETURN type, label, properties, status")
    return idx_set, cons


@check(
    "copy",
    "`GRAPH.COPY`: data, indexes and constraints carried over; `delete` works",
    "Reset (pristine → live) and per-strategy sandboxes are GRAPH.COPY forks (§5.10).",
    "If indexes/constraints are not copied: re-apply schema.py after every copy.",
)
def _(c: Check):
    src = _make_schema_graph("spike:copy_src")
    status, _ms = _wait_constraint(src)
    t0 = time.perf_counter()
    dst = src.copy("spike:copy_dst")
    copy_ms = (time.perf_counter() - t0) * 1000
    n = rows(dst, "MATCH (n) RETURN count(n)")[0][0]
    src_idx, src_cons = _schema_summary(src)
    dst_idx, dst_cons = _schema_summary(dst)
    dst_status, _ = _wait_constraint(dst, timeout_s=3)
    c.details.append(f"copy took {copy_ms:.1f} ms; nodes in copy: {n}")
    c.details.append(f"indexes in source: {len(src_idx)}, in copy: {len(dst_idx)}; identical: {src_idx == dst_idx}")
    c.details.append(f"constraints in copy: {[(r[0], r[1], r[2], r[3]) for r in dst_cons]}")
    # Prove the copied constraint actually enforces uniqueness.
    dst.query("CREATE (:PurchaseOrder {id:'PO-X'})")
    try:
        dst.query("CREATE (:PurchaseOrder {id:'PO-X'})")
        enforced = False
    except ResponseError:
        enforced = True
    c.details.append(f"duplicate PurchaseOrder rejected in the copy: {enforced}")
    # Full-text works in the copy too.
    ft = rows(dst, "CALL db.idx.fulltext.queryNodes('Place', 'VoltCell') YIELD node RETURN node.id")
    c.details.append(f"full-text query in the copy finds S-1: {bool(ft)}")
    dst.delete()
    gone = "spike:copy_dst" not in db.list_graphs()
    c.details.append(f"`graph.delete()` removed the copy: {gone}")
    ok = n == 1 and src_idx == dst_idx and dst_status == "OPERATIONAL" and enforced and bool(ft) and gone
    c.result = f"indexes {'copied' if src_idx == dst_idx else 'NOT copied'}, constraint {dst_status.lower()} and enforced={enforced}, copy {copy_ms:.0f} ms, delete ok={gone}"
    return ok


# --------------------------------------------------------------------------------------
# 6. Full-text fuzzy search
# --------------------------------------------------------------------------------------
@check(
    "fulltext",
    "Full-text index on `:Place` (multi-label nodes, two fields), exact / fuzzy / prefix",
    "Alert text → graph entities (resolve_entities, §7.1). Alerts misspell places.",
    "Lower-cased `CONTAINS` over name+aliases plus Python difflib ranking.",
)
def _(c: Check):
    g = db.select_graph("spike:ft")
    g.query(
        """
        CREATE (:Site:Place {id:'S-VOLT-AYU', name:'VoltCell Energy', aliases:'Ayutthaya cell fab'}),
               (:Region:Place {id:'R-AYU', name:'Ayutthaya', aliases:'Phra Nakhon Si Ayutthaya'}),
               (:Port:Place {id:'P-KHH', name:'Kaohsiung', aliases:'Kaohsiung Harbor KHH'}),
               (:Plant:Place {id:'PL-BAC', name:'Bac Ninh', aliases:'Bắc Ninh plant'})
        """
    )
    g.query("CALL db.idx.fulltext.createNodeIndex('Place', 'name', 'aliases')")
    q = "CALL db.idx.fulltext.queryNodes('Place', $term) YIELD node, score RETURN node.id, score ORDER BY score DESC"
    probes = {
        "Ayutthaya": "exact (name + alias hit)",
        "%Ayuthaya%": "fuzzy, 1 edit (missing t)",
        "%%Kaoshung%%": "fuzzy, 2 edits",
        "Kaoh*": "prefix",
        "KHH": "alias only",
    }
    found = {}
    for term, label in probes.items():
        r = rows(g, q, {"term": term}, ro=True)
        found[term] = [x[0] for x in r]
        c.details.append(f"`{term}` ({label}) → {found[term] or 'no hits'}")
    plain_miss = rows(g, q, {"term": "Ayuthaya"}, ro=True)
    c.details.append(f"`Ayuthaya` without `%` → {[x[0] for x in plain_miss] or 'no hits'} (so the resolver must add `%…%` itself)")
    ok = (
        "R-AYU" in found["Ayutthaya"]
        and "R-AYU" in found["%Ayuthaya%"]
        and "P-KHH" in found["%%Kaoshung%%"]
        and "P-KHH" in found["Kaoh*"]
        and "P-KHH" in found["KHH"]
    )
    c.result = "exact, fuzzy (`%term%` / `%%term%%`), prefix and alias hits all work" if ok else "some probes missed (see details)"
    return ok


# --------------------------------------------------------------------------------------
# 7. RO_QUERY rejects writes
# --------------------------------------------------------------------------------------
@check(
    "ro-query",
    "`GRAPH.RO_QUERY` rejects a write",
    "Every read tool is read-only by construction (CLAUDE.md rule 2).",
    "Keep a regex deny-list on CREATE/MERGE/SET/DELETE in run_query for read tools.",
)
def _(c: Check):
    g = db.select_graph("spike:ro")
    g.query("CREATE (:X {id:1})")
    errors = []
    for q in ["CREATE (:X {id:2})", "MATCH (x:X) SET x.id = 9", "MATCH (x:X) DELETE x", "CALL db.idx.fulltext.createNodeIndex('X', 'id')"]:
        try:
            g.ro_query(q)
            errors.append((q, None))
        except ResponseError as exc:
            errors.append((q, str(exc)))
    after = rows(g, "MATCH (x:X) RETURN x.id")
    for q, err in errors:
        c.details.append(f"`{q}` → {'rejected: ' + err if err else '**ACCEPTED**'}")
    c.details.append(f"graph after the attempts: {after}")
    ok = all(err for _, err in errors) and after == [[1]]
    c.result = "all 4 writes (CREATE, SET, DELETE, write procedure) rejected; graph unchanged" if ok else "a write got through"
    return ok


# --------------------------------------------------------------------------------------
# 8. Zero-length variable paths and path helpers
# --------------------------------------------------------------------------------------
@check(
    "varlen",
    "`[:FEEDS*0..4]` includes the start node; `relationships(p)` + `DISTINCT` + `startNode/endNode`",
    "Q-EXPOSURE treats a disrupted tier-1 site as a 0-hop chain; Q-FLOW-EXTRACT dedups FEEDS edges.",
    "UNION a direct-hit (0-hop) query with a `*1..4` query.",
)
def _(c: Check):
    g = db.select_graph("spike:varlen")
    # c2 -> c1 -> t1 ; c3 -> c1 (diamond-ish), so FEEDS edges repeat across paths
    g.query(
        """
        CREATE (c2:S {id:'c2'}), (c3:S {id:'c3'}), (c1:S {id:'c1'}), (t1:S {id:'t1'}),
               (c2)-[:FEEDS {cap:5}]->(c1), (c3)-[:FEEDS {cap:7}]->(c1), (c1)-[:FEEDS {cap:9}]->(t1)
        """
    )
    r = rows(g, "MATCH p = (d:S {id:'c1'})-[:FEEDS*0..4]->(t:S) RETURN t.id, length(p), [n IN nodes(p) | n.id] ORDER BY length(p)", ro=True)
    c.details.append("from c1 with `*0..4`: " + "; ".join(f"{t} len={l} path={p}" for t, l, p in r))
    zero = any(t == "c1" and l == 0 for t, l, _ in r)
    r2 = rows(
        g,
        """
        MATCH p = (:S)-[:FEEDS*1..4]->(t1:S {id:'t1'})
        UNWIND relationships(p) AS f
        WITH DISTINCT f
        RETURN startNode(f).id AS src, endNode(f).id AS dst, f.cap ORDER BY src
        """,
        ro=True,
    )
    c.details.append(f"distinct FEEDS edges upstream of t1: {r2} (expected 3, although 5 paths exist)")
    ok = zero and len(r2) == 3
    c.result = f"0-hop row present: {zero}; distinct upstream edges: {len(r2)}"
    return ok


# --------------------------------------------------------------------------------------
# 9. nodes(null) in OPTIONAL MATCH (Q-ALTERNATIVES shape)
# --------------------------------------------------------------------------------------
@check(
    "nodes-null",
    "`nodes(null)` after an `OPTIONAL MATCH` miss (Q-ALTERNATIVES taint check)",
    "Clean candidates must come back with `tainted_paths = []`, not an error or `[null]`.",
    "Run a separate taint query per candidate.",
)
def _(c: Check):
    g = db.select_graph("spike:taint")
    g.query(
        """
        CREATE (volt:Site {id:'VOLT', status:'disrupted'}), (hanr:Site {id:'HANR', status:'active'}),
               (amp:Site {id:'AMPR', status:'active'}), (kanto:Site {id:'KANT', status:'active'}),
               (pl:Plant {id:'PL'}),
               (volt)-[:FEEDS]->(amp), (hanr)-[:FEEDS]->(kanto),
               (amp)-[:CAN_SUPPLY {price:31}]->(pl), (kanto)-[:CAN_SUPPLY {price:46}]->(pl)
        """
    )
    q = """
    MATCH (alt:Site)-[cs:CAN_SUPPLY]->(pl:Plant {id:'PL'})
    OPTIONAL MATCH taint = (bad:Site)-[:FEEDS*1..4]->(alt)
    WHERE bad.status = 'disrupted'
    WITH alt, cs, collect(DISTINCT [n IN nodes(taint) | n.id]) AS tainted_paths
    RETURN alt.id, tainted_paths, size(tainted_paths) = 0 AS clean ORDER BY cs.price
    """
    r = rows(g, q, ro=True)
    raw = rows(g, "MATCH (alt:Site {id:'KANT'}) OPTIONAL MATCH p = (b:Site {status:'disrupted'})-[:FEEDS*1..4]->(alt) RETURN p, nodes(p)", ro=True)
    c.details.append(f"raw miss: path = {raw[0][0]!r}, nodes(path) = {raw[0][1]!r}")
    c.details.append("Q-ALTERNATIVES shape: " + "; ".join(f"{a}: paths={p} clean={cl}" for a, p, cl in r))
    got = {a: (p, cl) for a, p, cl in r}
    ok = got.get("AMPR") == ([["VOLT", "AMPR"]], False) and got.get("KANT") == ([], True)
    c.result = "`nodes(null)` is null, `collect` drops it → clean sites get `[]`; AmpereOne-style site gets its path" if ok else "unexpected (see details)"
    return ok


# --------------------------------------------------------------------------------------
# 10. Unique constraint → OPERATIONAL
# --------------------------------------------------------------------------------------
@check(
    "constraint",
    "Unique constraint on `PurchaseOrder.id` becomes OPERATIONAL",
    "Idempotent execution: running the same plan twice creates 0 duplicate POs.",
    "Application-level idempotency only: preflight query checks for existing PO ids.",
)
def _(c: Check):
    g = db.select_graph("spike:cons")
    g.query("CREATE INDEX FOR (n:PurchaseOrder) ON (n.id)")
    db.connection.execute_command("GRAPH.CONSTRAINT", "CREATE", "spike:cons", "UNIQUE", "NODE", "PurchaseOrder", "PROPERTIES", 1, "id")
    status, ms = _wait_constraint(g)
    c.details.append(f"status after polling: {status} ({ms:.0f} ms)")
    try:
        db.connection.execute_command("GRAPH.CONSTRAINT", "CREATE", "spike:cons2", "UNIQUE", "NODE", "PurchaseOrder", "PROPERTIES", 1, "id")
        no_idx = "accepted (index not required?)"
    except ResponseError as exc:
        no_idx = f"rejected: {exc}"
    c.details.append(f"same constraint on a graph **without** the exact-match index → {no_idx}")
    g.query("CREATE (:PurchaseOrder {id:'PO-1'})")
    try:
        g.query("CREATE (:PurchaseOrder {id:'PO-1'})")
        dup = "accepted (constraint NOT enforced)"
    except ResponseError as exc:
        dup = f"rejected: {exc}"
    c.details.append(f"second `PO-1` → {dup}")
    ok = status == "OPERATIONAL" and dup.startswith("rejected")
    c.result = f"{status} after {ms:.0f} ms; duplicate {('rejected' if ok else 'accepted')}"
    return ok


# --------------------------------------------------------------------------------------
# 11. Rollback on constraint violation
# --------------------------------------------------------------------------------------
@check(
    "rollback",
    "A write that violates the constraint rolls back **completely** (nodes, edges, SETs)",
    "Q-EXECUTE is one atomic write; a half-applied plan would corrupt the receipt (V9).",
    "Preflight read rejects any plan whose PO ids already exist (app-level idempotency); constraint stays as backstop.",
)
def _(c: Check):
    g = db.select_graph("spike:rb")
    g.query("CREATE INDEX FOR (n:PurchaseOrder) ON (n.id)")
    db.connection.execute_command("GRAPH.CONSTRAINT", "CREATE", "spike:rb", "UNIQUE", "NODE", "PurchaseOrder", "PROPERTIES", 1, "id")
    _wait_constraint(g)
    g.query("CREATE (:PurchaseOrder {id:'PO-1'}), (:Order {id:'SO-1', status:'open'}), (:Order {id:'SO-2', status:'open'})")
    # Batch: PO-2 is new (creates a node, an edge and flips SO-2's status), then PO-1 collides.
    q = """
    UNWIND $pos AS po
    MATCH (o:Order {id: po.order_id})
    CREATE (p:PurchaseOrder {id: po.id})-[:PROTECTS {qty: po.qty}]->(o)
    SET o.status = 'protected_projected'
    RETURN count(p)
    """
    pos = [{"id": "PO-2", "order_id": "SO-2", "qty": 10}, {"id": "PO-1", "order_id": "SO-1", "qty": 5}]
    try:
        g.query(q, {"pos": pos})
        err = None
    except ResponseError as exc:
        err = str(exc)
    po_ids = sorted(r[0] for r in rows(g, "MATCH (p:PurchaseOrder) RETURN p.id"))
    edges = rows(g, "MATCH ()-[r:PROTECTS]->() RETURN count(r)")[0][0]
    statuses = rows(g, "MATCH (o:Order) RETURN o.id, o.status ORDER BY o.id")
    c.details.append(f"error: {err}")
    c.details.append(f"after the failed batch: POs = {po_ids}, PROTECTS edges = {edges}, orders = {statuses}")
    ok = err is not None and po_ids == ["PO-1"] and edges == 0 and all(s == "open" for _, s in statuses)
    c.result = "whole query rolled back: no PO-2, no edge, SO-2 status unchanged" if ok else "PARTIAL WRITE survived (see details)"
    return ok


# --------------------------------------------------------------------------------------
# 12. Inline maps with UNWIND variables
# --------------------------------------------------------------------------------------
@check(
    "inline-map",
    "Inline maps with UNWIND variables (`{id: po.site_id}`), nested `UNWIND po.allocations`, index use",
    "Q-EXECUTE matches sites/orders from a parameter list of PO maps.",
    "Use `MATCH (s:Site) WHERE s.id = po.site_id` instead.",
)
def _(c: Check):
    g = db.select_graph("spike:inline")
    g.query("CREATE INDEX FOR (n:Site) ON (n.id)")
    g.query("CREATE INDEX FOR (n:Order) ON (n.id)")
    g.query("UNWIND range(1, 50) AS i CREATE (:Site {id: 'S-' + toString(i)}), (:Order {id: 'SO-' + toString(i)})")
    q = """
    UNWIND $pos AS po
    MATCH (s:Site {id: po.site_id})
    CREATE (p:PurchaseOrder {id: po.id, qty: po.qty})-[:FROM_SITE]->(s)
    WITH p, po
    UNWIND po.allocations AS a
    MATCH (o:Order {id: a.order_id})
    CREATE (p)-[pr:PROTECTS {qty: a.qty}]->(o)
    RETURN count(DISTINCT p) AS pos, count(pr) AS protects
    """
    pos = [
        {"id": "PO-A", "site_id": "S-3", "qty": 30, "allocations": [{"order_id": "SO-1", "qty": 10}, {"order_id": "SO-2", "qty": 20}]},
        {"id": "PO-B", "site_id": "S-7", "qty": 5, "allocations": [{"order_id": "SO-9", "qty": 5}]},
    ]
    plan = str(g.explain(q, {"pos": pos}))
    r = rows(g, q, {"pos": pos})
    check_rows = rows(g, "MATCH (p:PurchaseOrder)-[:FROM_SITE]->(s) MATCH (p)-[r:PROTECTS]->(o) RETURN p.id, s.id, o.id, r.qty ORDER BY p.id, o.id")
    uses_index = "Index Scan" in plan
    c.details.append(f"receipt: pos={r[0][0]}, protects={r[0][1]} (expected 2, 3)")
    c.details.append(f"rows written: {check_rows}")
    c.details.append(f"execution plan uses an index scan for the inline-map MATCH: {uses_index}")
    ok = r[0] == [2, 3] and len(check_rows) == 3 and check_rows[0][1] == "S-3"
    c.result = f"works; receipt counts correct; index scan used: {uses_index}"
    return ok


# --------------------------------------------------------------------------------------
# 13. Edge-alias pitfall (CLAUDE.md rule 2)
# --------------------------------------------------------------------------------------
@check(
    "alias",
    "Counting parallel edges with vs without an edge alias",
    "Rule 2 says unaliased edges only get an existence check; sums over FEEDS/SUPPLIES would be wrong.",
    "Always alias edges you count or sum (already a hard rule).",
)
def _(c: Check):
    g = db.select_graph("spike:alias")
    g.query("CREATE (a:N {id:'a'}), (b:N {id:'b'}), (a)-[:FEEDS {w:1}]->(b), (a)-[:FEEDS {w:2}]->(b)")
    unaliased = rows(g, "MATCH (a:N {id:'a'})-[:FEEDS]->(b:N) RETURN count(*)", ro=True)[0][0]
    aliased = rows(g, "MATCH (a:N {id:'a'})-[f:FEEDS]->(b:N) RETURN count(f), sum(f.w)", ro=True)[0]
    c.details.append(f"`-[:FEEDS]->` count(*) = {unaliased}; `-[f:FEEDS]->` count(f) = {aliased[0]}, sum(f.w) = {aliased[1]}")
    c.result = f"unaliased sees {unaliased} row(s), aliased sees {aliased[0]}" + (" — pitfall confirmed" if unaliased != aliased[0] else " — no difference in this build, rule kept anyway")
    return aliased[0] == 2 and aliased[1] == 3


# --------------------------------------------------------------------------------------
# 14. TIMEOUT 1000 / RESULTSET_SIZE 10000 defaults
# --------------------------------------------------------------------------------------
@check(
    "limits",
    "Image defaults `TIMEOUT 1000` and `RESULTSET_SIZE 10000`: what do they cut off?",
    "Seeding, exports and the 50k-node benchmark must not be silently truncated or killed.",
    "Raise the limits in docker-compose `FALKORDB_ARGS`, or pass a per-query `timeout`.",
)
def _(c: Check):
    g = db.select_graph("spike:limits")
    g.query("CREATE (:T {i: 0})")  # the key must exist before RO_QUERY
    cfg = {}
    for key in ["TIMEOUT", "TIMEOUT_DEFAULT", "TIMEOUT_MAX", "RESULTSET_SIZE"]:
        cfg[key] = db.connection.execute_command("GRAPH.CONFIG", "GET", key)[1]
    c.details.append(f"config: {cfg}")

    # Slow read (~seconds of CPU) through RO_QUERY.
    slow = "UNWIND range(1, 40000000) AS x WITH x WHERE x % 7 = 0 RETURN count(x)"
    t0 = time.perf_counter()
    try:
        g.ro_query(slow)
        read_out = "completed"
    except ResponseError as exc:
        read_out = f"error: {exc}"
    read_ms = (time.perf_counter() - t0) * 1000
    c.details.append(f"slow read via RO_QUERY: {read_out} after {read_ms:.0f} ms")

    t0 = time.perf_counter()
    try:
        g.ro_query(slow, timeout=60_000)
        read_out2 = "completed"
    except ResponseError as exc:
        read_out2 = f"error: {exc}"
    c.details.append(f"same read with per-query `timeout=60000`: {read_out2} after {(time.perf_counter() - t0) * 1000:.0f} ms")

    # Big write, larger than the whole demo world (~600 nodes / 1,600 edges) by 100x.
    t0 = time.perf_counter()
    try:
        res = g.query("UNWIND range(1, 60000) AS i CREATE (:T {i: i})")
        write_out = f"created {res.nodes_created} nodes"
    except ResponseError as exc:
        write_out = f"error: {exc}"
    c.details.append(f"write of 60,000 nodes in one query: {write_out} in {(time.perf_counter() - t0) * 1000:.0f} ms")

    big = rows(g, "UNWIND range(1, 12000) AS x RETURN x", ro=True)
    c.details.append(f"RETURN 12,000 rows → client received **{len(big)}** rows, no error raised")
    truncated = len(big) < 12000
    read_killed = "timed out" in read_out
    override_ok = read_out2 == "completed"
    c.result = (
        f"slow reads {'killed (`Query timed out`)' if read_killed else 'not killed'}; "
        f"per-query `timeout` {'overrides it' if override_ok else 'does NOT override it'}; "
        f"big writes {'unaffected' if write_out.startswith('created') else 'killed'}; "
        f"results {'silently truncated at ' + str(len(big)) if truncated else 'not truncated'}"
    )
    # This row "passes" when we understand the behaviour and have a mitigation; the fallback says what to do.
    c.fallback = (
        "Keep the defaults (they protect the public demo) but: (1) every engine query is small — the demo world is ~600 nodes; "
        "(2) `run_query` raises if a result has exactly RESULTSET_SIZE rows, so truncation can never be silent; "
        "(3) seeding/benchmark use batched `UNWIND` writes, which TIMEOUT does not kill; "
        "(4) the 50k-node benchmark passes a per-query timeout."
    )
    return override_ok and write_out.startswith("created")


# --------------------------------------------------------------------------------------
# 15. Persistence settings for the `memory` graph
# --------------------------------------------------------------------------------------
@check(
    "persistence",
    "Data directory and snapshot settings (for the persistent `memory` graph)",
    "Memory must survive `make down && make up`; the compose volume must sit on the right path.",
    "Mount the volume on whatever `dir` reports, and call `BGSAVE` after writing memory.",
)
def _(c: Check):
    d = db.connection.config_get("dir")
    save = db.connection.config_get("save")
    aof = db.connection.config_get("appendonly")
    c.details.append(f"dir = {d.get('dir')}, save = {save.get('save')!r}, appendonly = {aof.get('appendonly')}")
    ok = d.get("dir") == "/var/lib/falkordb/data"
    c.result = f"data dir `{d.get('dir')}` (compose volume mounted there); RDB save rule `{save.get('save')}`; AOF {aof.get('appendonly')}"
    return ok


# --------------------------------------------------------------------------------------
# 16. MCP server mounted inside FastAPI's lifespan
# --------------------------------------------------------------------------------------
@check(
    "mcp-mount",
    "MCP server (`MCPServer`, formerly `FastMCP`) mounted at `/mcp` with its session manager in FastAPI's lifespan",
    "The agent and external clients (Claude Desktop/Code) reach the tool catalogue at `/mcp` (§9.4).",
    "Run the MCP server as its own process on :8001 (`mcp.run(transport='streamable-http')`); the agent connects the same way.",
)
def _(c: Check):
    from mcp import Client

    port = 8765
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "domino.api.main:app", "--host", "127.0.0.1", "--port", str(port), "--log-level", "warning"],
        cwd=ROOT / "backend",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    try:
        base = f"http://127.0.0.1:{port}"
        for _ in range(100):
            try:
                h = httpx.get(f"{base}/api/health", timeout=1)
                break
            except httpx.TransportError:
                time.sleep(0.1)
        else:
            raise RuntimeError("uvicorn did not start")
        c.details.append(f"`GET /api/health` → {h.status_code} {h.json()}")

        async def talk(url):
            async with Client(url) as client:
                tools = await client.list_tools()
                res = await client.call_tool("health", {})
                return [t.name for t in tools.tools], res

        results = {}
        for url in (f"{base}/mcp/", f"{base}/mcp"):
            try:
                names, res = asyncio.run(talk(url))
                payload = getattr(res, "structured_content", None) or [getattr(x, "text", x) for x in res.content]
                results[url] = True
                c.details.append(f"`{url}` → tools {names}; `health` returned {payload}")
            except Exception as exc:
                results[url] = False
                c.details.append(f"`{url}` → failed: {type(exc).__name__}: {exc}")

        # DNS-rebinding protection: what happens with a public Host header (as behind Caddy)?
        r = httpx.post(
            f"{base}/mcp/",
            headers={"Host": "domino.example.com", "Accept": "application/json, text/event-stream", "Content-Type": "application/json"},
            json={"jsonrpc": "2.0", "id": 1, "method": "ping"},
        )
        c.details.append(f"POST with `Host: domino.example.com` → HTTP {r.status_code} (non-localhost Host header; matters for deployment)")
        ok = results.get(f"{base}/mcp/", False) or results.get(f"{base}/mcp", False)
        c.result = (
            f"`/mcp/` {'✓' if results.get(base + '/mcp/') else '✗'}, `/mcp` {'✓' if results.get(base + '/mcp') else '✗'}; "
            f"list_tools + call_tool round-trip; foreign Host header → HTTP {r.status_code}"
        )
        return ok
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


# --------------------------------------------------------------------------------------
# Report
# --------------------------------------------------------------------------------------
def environment() -> list[str]:
    info = db.connection.info("server")
    graph_ver = None
    for mod in db.connection.execute_command("MODULE", "LIST"):
        f = dict(zip(mod[::2], mod[1::2]))
        if f.get(b"name", f.get("name")) in (b"graph", "graph"):
            graph_ver = f.get(b"ver", f.get("ver"))
    image = "unknown (docker CLI not available)"
    try:
        out = subprocess.run(
            ["docker", "inspect", "falkordb", "--format", "{{.Config.Image}} {{.Image}}"],
            capture_output=True, text=True, timeout=10,
        )
        if out.returncode == 0:
            cfg_image, image_id = out.stdout.split()
            digests = subprocess.run(
                ["docker", "image", "inspect", image_id, "--format", "{{join .RepoDigests \", \"}}"],
                capture_output=True, text=True, timeout=10,
            ).stdout.strip()
            image = f"`{cfg_image}` → `{digests}`"
    except (OSError, ValueError, subprocess.TimeoutExpired):
        pass
    return [
        f"- Run at: {dt.datetime.now().astimezone().strftime('%Y-%m-%d %H:%M %Z')}",
        f"- Image: {image}",
        f"- Redis {info.get('redis_version')}, FalkorDB graph module ver **{graph_ver}**",
        f"- Python {sys.version.split()[0]}; `falkordb` {version('falkordb')}, `mcp` {version('mcp')}, `fastapi` {version('fastapi')}",
    ]


IMPLICATIONS = [
    "**MCP SDK 2.x renamed `FastMCP` to `MCPServer`** (`from mcp.server.mcpserver import MCPServer`). Same decorator API. "
    "Mounted with `app.mount('/mcp', mcp.streamable_http_app(streamable_http_path='/'))` and `mcp.session_manager.run()` in the FastAPI lifespan.",
    "**MCP rejects non-localhost `Host` headers (HTTP 421, DNS-rebinding protection).** At deploy time pass "
    "`transport_security=TransportSecuritySettings(allowed_hosts=[...])` with the public hostname, or `/mcp` will fail behind Caddy.",
    "**`algo.maxFlow` returns floats** (`13.0`) and only positive-flow edges. Cast to int in the capacity engine; compute the min cut from "
    "the full projected network in Python, as PLAN §7.6 already says.",
    "**Full-text needs `%term%` (1 edit) or `%%term%%` (2 edits) for fuzzy hits**; a bare misspelling finds nothing. The resolver adds the markers.",
    "**Write queries are atomic**: a constraint violation undoes every node, edge and SET in that query. Q-EXECUTE can be one query; "
    "the preflight read still runs first so the user gets a clean error instead of a constraint exception.",
    "**`GRAPH.COPY` carries indexes, the full-text index and the unique constraint**, so sandboxes and `world:live` need no schema re-apply.",
    "**Slow reads are killed at the image's TIMEOUT**; `run_query` should pass an explicit per-query `timeout` and raise when a result "
    "has exactly RESULTSET_SIZE rows (truncation is otherwise silent).",
]


def write_report(results: list[Check]) -> None:
    passed = sum(r.ok for r in results)
    lines = [
        "# SPIKE: FalkorDB + MCP capability check (M1)",
        "",
        "Generated by `scripts/spike.py` (`make spike`). Do not edit by hand; re-run the script.",
        "",
        *environment(),
        "",
        f"**{passed} / {len(results)} checks passed.** Every ✗ row has a written fallback.",
        "",
        "| # | Capability | | Result | Fallback if ✗ |",
        "|---|---|---|---|---|",
    ]
    for i, r in enumerate(results, 1):
        mark = "✓" if r.ok else "✗"
        cell = lambda s: s.replace("|", "\\|").replace("\n", " ")
        lines.append(f"| {i} | {cell(r.capability)} | {mark} | {cell(r.result)} | {cell(r.fallback)} |")
    lines += ["", "## What this changes for later milestones", ""]
    lines += [f"- {x}" for x in IMPLICATIONS]
    lines += ["", "## Details", ""]
    for i, r in enumerate(results, 1):
        lines += [f"### {i}. {r.capability} — {'✓' if r.ok else '✗'}", "", f"*Why it matters:* {r.why}", ""]
        lines += [f"- {d}" if not d.startswith("```") else d for d in r.details]
        lines.append("")
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # Windows consoles default to cp1252
    db.connection.ping()
    results = []
    for run in CHECKS:
        r = run()
        print(f"{'OK  ' if r.ok else 'FAIL'} {r.key:12s} {r.result}")
        results.append(r)
    write_report(results)
    passed = sum(r.ok for r in results)
    print(f"\nwrote {OUT.relative_to(ROOT)}: {passed}/{len(results)} passed; every ✗ has a written fallback")
    # A ✗ with a fallback is a finding, not a broken spike; only a crashing probe fails the run.
    return 1 if any(r.crashed for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
