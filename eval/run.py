"""Run deterministic evaluation on private graphs. No LLM or paid API client is created."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import platform
import subprocess
import time
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import networkx as nx
from redis import Redis
from redis.backoff import NoBackoff
from redis.retry import Retry

from domino.allocators.greedy import allocate, build_problem
from domino.allocators.strategies import DEFAULT_BUDGET_CENTS
from domino.config import settings
from domino.engines.capacity import compute_true_capacity
from domino.engines.executor import approve_decision, execute_plan, propose_decision
from domino.engines.exposure import trace_exposure
from domino.engines.incident import declare_incident
from domino.engines.sandbox import score
from domino.engines.shortage import project_shortages
from domino.engines.verifier import verify_execution
from domino.graph.client import get_db, ping
from domino.graph.lifecycle import build_pristine, copy_graph, drop_graph
from domino.graph.run_query import capture_queries
from domino.seed.generator import generate
from domino.seed.motifs import MONSOON, PANEL_FIRE
from eval.fixtures import cases as adversarial_cases
from eval.oracle import World
from eval.report import render
from scripts.export_world_json import export_world, write_export

ROOT = Path(__file__).resolve().parents[1]
METHODS = {"B1": "S1", "B2": "S2", "S4": "S4"}


def classification(actual: set, expected: set) -> dict:
    return {"tp": len(actual & expected), "fp": len(actual - expected), "fn": len(expected - actual),
            "false_positive_ids": sorted(actual - expected), "false_negative_ids": sorted(expected - actual)}


def compare_projection(actual: dict, expected: dict) -> list[dict]:
    diffs = []
    got = {o["order_id"]: o["ready_day"] for o in actual["orders"]}
    for oid in sorted(set(got) | set(expected["ready"])):
        if got.get(oid, "missing") != expected["ready"].get(oid, "missing"):
            diffs.append({"order": oid, "field": "ready_day", "actual": got.get(oid, "missing"),
                          "expected": expected["ready"].get(oid, "missing")})
    if actual["totals"]["penalty_exposure_cents"] != expected["penalty_cents"]:
        diffs.append({"field": "penalty_cents", "actual": actual["totals"]["penalty_exposure_cents"],
                      "expected": expected["penalty_cents"]})
    rates = {p["po_id"]: p["realized_rate_wk"] for p in actual["pos"]}
    if rates != expected["rates"]:
        diffs.append({"field": "realized_rates", "actual": rates, "expected": expected["rates"]})
    return diffs


def traps(world: World, plan: dict, capacities: dict) -> list[dict]:
    bad = []
    orders = {o["id"]: o for o in world.demand(42)}
    for po in plan["pos"]:
        key = po["component_id"], po["plant_id"]
        if key not in capacities:
            capacities[key] = world.capacity(*key)
        if capacities[key]["sites"].get(po["site_id"], 0) <= 0:
            bad.append({"po": po["id"], "site": po["site_id"], "reason": "zero_clean_capacity"})
        for allocation in po["allocations"]:
            order = orders[allocation["order_id"]]
            allowed = set(order["needs"])
            allowed.update(e["dst"] for e in world.outgoing("ALLOWS_ALTERNATE", order["product"])
                           if e["props"].get("for_component") in order["needs"])
            if po["component_id"] not in allowed:
                bad.append({"po": po["id"], "order": order["id"], "reason": "incompatible"})
    return bad


class Evaluation:
    def __init__(self, output: Path):
        self.output = output
        self.namespace = "eval:" + uuid.uuid4().hex[:12]
        self.run_id = self.namespace.replace(":", "-")
        self.owned = set()
        self.results = []
        self.healthy = []
        self.failures = []
        self.scripted = []
        self.samples = defaultdict(lambda: defaultdict(list))
        self.exports = []

    def graph(self, suffix: str) -> str:
        name = self.namespace + ":" + suffix
        self.owned.add(name)
        return name

    def drop(self, graph: str) -> None:
        if not graph.startswith(self.namespace + ":"):
            raise ValueError("Refusing cleanup outside this evaluation namespace")
        drop_graph(graph)
        self.owned.discard(graph)

    def collect(self, phase: str, records: list) -> None:
        for r in records:
            self.samples[phase][r.name].append(r.ms)

    def issue(self, case: str, kind: str, details) -> None:
        self.failures.append({"case": case, "kind": kind, "details": details})

    def evaluate_case(self, base: str, data: dict, spec: dict) -> None:
        name = spec["name"]
        graph = self.graph("case")
        copy_graph(base, graph)
        records = []
        try:
            with capture_queries() as records:
                declaration = declare_incident(graph, incident_id="INC-EVAL", kind="synthetic",
                                               title=name, alert_text="Synthetic evaluation incident",
                                               entity_ids=spec["entity_ids"], capacity_factor=spec["factor"],
                                               duration_days=spec["duration"])
                oracle = World(data).disrupted(spec["entity_ids"], spec["factor"], spec["duration"])
                affected = oracle.expand(spec["entity_ids"])
                if declaration.get("site_ids") != affected:
                    self.issue(name, "incident_footprint", {"actual": declaration, "expected": affected})
                trace = trace_exposure(graph, "INC-EVAL")
                expected_exposure = oracle.exposure(affected)
                exposure = classification(set(trace["order_evidence"]), expected_exposure)
                evidence = oracle.validate_evidence(trace, affected)
                if exposure["fp"] or exposure["fn"] or evidence["invalid"]:
                    self.issue(name, "exposure_or_evidence", {"exposure": exposure, "evidence": evidence})
                started = time.perf_counter()
                baseline = project_shortages(graph)
                baseline_ms = (time.perf_counter() - started) * 1000
                expected = oracle.project()
                differences = compare_projection(baseline, expected)
                if "ready" in spec and expected["ready"] != spec["ready"]:
                    self.issue(name, "hand_worked_expectation", {"actual": expected["ready"], "expected": spec["ready"]})
                late = classification({o["order_id"] for o in baseline["orders"] if o["status"] == "projected_late"}, expected["late"])
                if differences:
                    self.issue(name, "baseline_oracle", differences)
                capacity_checks, capacities = [], {}
                for component in baseline["components"]:
                    if not component["reduced"]:
                        continue
                    key = component["component"], component["plant"]
                    actual = compute_true_capacity(graph, *key, run_id=self.run_id)
                    independent = oracle.capacity(*key)
                    capacities[key] = independent
                    matches = (actual["true_wk"] == independent["true_wk"]
                               and {s["site"]: s["site_clean_wk"] for s in actual["sites"]} == independent["sites"])
                    capacity_checks.append({"component": key[0], "plant": key[1], "actual_wk": actual["true_wk"],
                                            "oracle_wk": independent["true_wk"], "matches": matches,
                                            "warnings": actual["warnings"]})
                    if not matches:
                        self.issue(name, "capacity_oracle", capacity_checks[-1])
                common = {"case": name, "seed": spec.get("seed"), "scenario": spec["scenario"],
                          "exposure": exposure, "evidence": evidence, "late_classification": late,
                          "capacity_checks": capacity_checks}
                self.results.append({**common, "method": "B0", "strategy": "S0", "runtime_ms": baseline_ms,
                                     "score": score(baseline, baseline, None), "oracle_differences": differences,
                                     "traps": [], "verification": None, "plan": None})
                started = time.perf_counter()
                problem = build_problem(graph, run_id=self.run_id)
                setup_ms = (time.perf_counter() - started) * 1000
                for method, strategy in METHODS.items():
                    fork = self.graph("method")
                    copy_graph(graph, fork)
                    try:
                        started = time.perf_counter()
                        plan = allocate(problem, strategy, f"DEC-{strategy}", declaration["world_version"])
                        proposal = propose_decision(fork, "INC-EVAL", plan)
                        approval = approve_decision(fork, plan, "evaluation-isolated-graph")
                        receipt = execute_plan(fork, plan)
                        if proposal["outcome"] != "ok" or approval["outcome"] != "ok":
                            raise RuntimeError(f"Proposal/approval failed: {proposal}; {approval}")
                        if receipt["outcome"] not in {"executed", "nothing_to_execute"}:
                            raise RuntimeError(f"Execution failed: {receipt}")
                        projection = project_shortages(fork)
                        verification = verify_execution(fork, plan, receipt, run_id=self.run_id)
                        runtime_ms = (time.perf_counter() - started) * 1000
                        # Export the executed graph; never feed engine-extracted rows into the oracle.
                        realized = World(export_world(fork)).project()
                        differences = compare_projection(projection, realized)
                        selected_traps = traps(oracle, plan, capacities)
                        row = {**common, "method": method, "strategy": strategy, "runtime_ms": runtime_ms,
                               "common_problem_setup_ms": setup_ms, "score": score(projection, baseline, plan),
                               "oracle_differences": differences, "traps": selected_traps,
                               "verification": verification, "receipt": receipt, "plan": plan}
                        self.results.append(row)
                        if differences:
                            self.issue(name + "/" + method, "recovery_oracle", differences)
                        if method != "B1" and (not verification["ok"] or selected_traps):
                            self.issue(name + "/" + method, "graph_aware_safety", {"failed": verification["failed"], "traps": selected_traps})
                    finally:
                        self.drop(fork)
        except Exception as exc:
            self.issue(name, "exception", {"type": type(exc).__name__, "message": str(exc)})
        finally:
            self.collect("evaluation", records)
            self.drop(graph)

    def evaluate_world(self, world, specs: list[dict], seed: int | None) -> None:
        base = self.graph("base")
        records = []
        try:
            with capture_queries() as records:
                build_pristine(world, base)
                data = export_world(base)
            path = self.output.parent / "out" / "worlds" / (f"seed-{seed}.json.gz" if seed is not None else specs[0]["name"] + ".json.gz")
            digest = write_export(data, path)
            self.exports.append({"seed": seed, "case": specs[0]["name"], "path": str(path.relative_to(ROOT)),
                                 "sha256": digest, "world_fingerprint": world.fingerprint()})
            if seed is not None:
                with capture_queries() as healthy_records:
                    actual = project_shortages(base)
                self.collect("healthy", healthy_records)
                expected = World(data).project()
                differences = compare_projection(actual, expected)
                ok = not differences and not expected["late"] and actual["totals"]["projected_late"] == 0
                self.healthy.append({"seed": seed, "ok": ok, "late": actual["totals"]["projected_late"], "differences": differences})
                if not ok:
                    self.issue(f"healthy/{seed}", "healthy_baseline", self.healthy[-1])
            for spec in specs:
                self.evaluate_case(base, data, spec)
                print(f"Evaluated {spec['name']}; recorded failures={len(self.failures)}", flush=True)
        except Exception as exc:
            self.issue(f"world/{seed}", "exception", {"type": type(exc).__name__, "message": str(exc)})
        finally:
            self.collect("setup", records)
            self.drop(base)

    async def smoke(self, scenario: str, repeat: int) -> None:
        # This is a plumbing test (P-scripted), never an A/real-model measurement.
        from mcp.client.client import Client
        from domino.agent.context import CONTEXTS, get_context
        from domino.agent.loop import approve, new_run, run_phase
        from domino.agent.scenarios import SCENARIOS
        from domino.agent.scripted import ScriptedClient
        from domino.mcp.server import mcp
        graph, memory = self.graph("smoke"), self.graph("memory")
        records, run = [], None
        started = time.perf_counter()
        try:
            build_pristine(generate(42), graph)
            before = export_world(graph)
            run = new_run(scenario, SCENARIOS[scenario]["alert"], graph, scripted=True)
            ctx = get_context(run.id)
            ctx.memory_graph = memory
            client = ScriptedClient(scenario)
            with capture_queries() as records:
                async with Client(mcp) as mc:
                    await run_phase(run, client, mc)
                    waited = run.status == "awaiting_approval"
                    no_pos_before_approval = not World(export_world(graph)).purchase_orders()
                    if waited:
                        await approve(run, "evaluation-isolated-graph", client, mc)
            after = export_world(graph)
            projection = project_shortages(graph)
            independent = World(after).project()
            differences = compare_projection(projection, independent)
            verification = [r for r in ctx.results.values() if "all_pass" in r]
            report = ctx.report or {}
            event_tools = [e["data"]["tool"] for e in run.events if e["type"] == "tool.called"]
            ok = run.status == "completed" and bool(report) and not differences
            if scenario == "non_event":
                ok &= report.get("outcome") == "not_in_graph" and before == after and not waited
            else:
                ok &= waited and no_pos_before_approval and bool(verification) and all(r["all_pass"] for r in verification)
            row = {"scenario": scenario, "repeat": repeat, "ok": bool(ok), "status": run.status,
                   "outcome": report.get("outcome"), "waited_for_approval": waited,
                   "no_pos_before_approval": no_pos_before_approval, "unchanged_world": before == after,
                   "tool_calls": run.tool_calls, "tools": event_tools, "usage": run.usage,
                   "cost_usd": run.cost_usd, "runtime_ms": (time.perf_counter() - started) * 1000,
                   "oracle_differences": differences, "report": report, "error": run.error}
            self.scripted.append(row)
            if not ok:
                self.issue(f"scripted/{scenario}/{repeat}", "smoke_failure", row)
        except Exception as exc:
            self.issue(f"scripted/{scenario}/{repeat}", "exception", {"type": type(exc).__name__, "message": str(exc)})
        finally:
            self.collect("scripted", records)
            if run:
                CONTEXTS.pop(run.id, None)
            self.drop(graph)
            self.drop(memory)
        print(f"Scripted plumbing: {scenario} repeat {repeat}", flush=True)


def probe_connection() -> None:
    # FalkorDB's constructor performs discovery calls before returning its client.
    # Probe with explicit limits first so an offline server never enters that path.
    with Redis(host=settings.falkordb_host, port=settings.falkordb_port,
               socket_connect_timeout=3, socket_timeout=3, retry=Retry(NoBackoff(), 0)) as connection:
        connection.ping()


def bound_connection() -> None:
    probe_connection()
    # Only this CLI process's client is changed. No database CONFIG is written.
    pool = getattr(get_db().connection, "connection_pool", None)
    if pool is not None:
        pool.connection_kwargs.update(socket_connect_timeout=3, socket_timeout=35,
                                      retry=Retry(NoBackoff(), 0), retry_on_timeout=False)


def server_provenance() -> dict:
    try:
        probe_connection()
        return ping()
    except Exception as exc:
        return {"falkordb": "unavailable", "graph_module_ver": None, "error_type": type(exc).__name__}


def provenance() -> dict:
    paths = [p for parent in (ROOT / "backend/domino", ROOT / "eval", ROOT / "scripts")
             for p in parent.rglob("*") if p.is_file() and p.suffix in {".py", ".cypher"}]
    digest = hashlib.sha256()
    for p in sorted(paths):
        digest.update(p.relative_to(ROOT).as_posix().encode())
        digest.update(p.read_bytes())
    return {"git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
            "source_sha256": digest.hexdigest(), "python": platform.python_version(),
            "networkx": nx.__version__, "platform": platform.platform(), **server_provenance()}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed-start", type=int, default=42)
    parser.add_argument("--seed-count", type=int, default=20)
    parser.add_argument("--scripted-repeats", type=int, default=2)
    parser.add_argument("--output", type=Path, default=ROOT / "eval/results.json")
    args = parser.parse_args()
    if args.seed_count < 1 or args.scripted_repeats < 0:
        parser.error("seed-count must be positive; scripted-repeats cannot be negative")
    seeds = list(range(args.seed_start, args.seed_start + args.seed_count))
    ev = Evaluation(args.output.resolve())
    started = time.perf_counter()
    try:
        bound_connection()
        # Check persistence health before writes; never disable Redis write protections.
        persistence = get_db().connection.info("persistence")
        if persistence.get("rdb_last_bgsave_status") == "err":
            raise RuntimeError("FalkorDB persistence is failing (rdb_last_bgsave_status=err). "
                               "Database evaluation is blocked; preserve/repair the Docker host before retrying.")
        for seed in seeds:
            specs = []
            for name, motif in [("monsoon", MONSOON), ("panel_fire", PANEL_FIRE)]:
                inc = motif["incident"]
                specs.append({"name": f"seed-{seed}/{name}", "seed": seed, "scenario": name,
                              "entity_ids": [inc["zone_id"]] if "zone_id" in inc else inc["site_ids"],
                              "factor": inc["capacity_factor"], "duration": inc["duration_days"]})
            ev.evaluate_world(generate(seed), specs, seed)
        for case in adversarial_cases():
            ev.evaluate_world(case["world"], [{**case, "scenario": "adversarial"}], None)
        for scenario in ("monsoon", "panel_fire", "non_event"):
            for repeat in range(1, args.scripted_repeats + 1):
                asyncio.run(ev.smoke(scenario, repeat))
    except Exception as exc:
        ev.issue("run", "environment_or_runner", {"type": type(exc).__name__, "message": str(exc)})
    finally:
        for graph in list(ev.owned):
            try:
                ev.drop(graph)
            except Exception as exc:
                ev.issue(graph, "cleanup_failure", {"type": type(exc).__name__, "message": str(exc)})
        expected_rows = len(seeds) * 2 * 4 + len(adversarial_cases()) * 4
        if len(ev.results) != expected_rows or len(ev.scripted) != args.scripted_repeats * 3:
            ev.issue("run", "incomplete_coverage", {"expected_rows": expected_rows, "actual_rows": len(ev.results),
                     "expected_scripted_runs": args.scripted_repeats * 3, "actual_scripted_runs": len(ev.scripted)})
        data = {"format": 1, "generated_utc": datetime.now(timezone.utc).isoformat(),
                "seeds": seeds, "scripted_repeats": args.scripted_repeats, "budget_cents": DEFAULT_BUDGET_CENTS, "horizon_days": 42,
                "methods": {"B0": "do nothing", "B1": "S1: nominal tier-1, cheapest, sea",
                            "B2": "S2: graph-aware, cheapest, sea", "S4": "balanced, graph-aware, air when needed"},
                "provenance": provenance(), "elapsed_seconds": time.perf_counter() - started,
                "healthy": ev.healthy, "exports": ev.exports, "cases": ev.results,
                "scripted": ev.scripted, "failures": ev.failures,
                "query_samples_ms": {phase: dict(values) for phase, values in ev.samples.items()}}
        ev.output.parent.mkdir(parents=True, exist_ok=True)
        ev.output.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
        report_path = ev.output.with_name("RESULTS.md")
        report_path.write_text(render(data), encoding="utf-8", newline="\n")
        print(f"Saved {ev.output}; {len(ev.failures)} evaluation failures", flush=True)
    raise SystemExit(1 if ev.failures else 0)


if __name__ == "__main__":
    main()
