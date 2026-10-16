"""`make demo-headless SCENARIO=monsoon`: the whole agent run in the terminal.

Resets world:live from pristine, runs the agent over MCP, prints each tool call as it happens,
asks YOU to approve the plan, then lets the agent verify and report. Prints tokens and $ cost.

    --dry-run   use the scripted stand-in model (offline, $0) to check the plumbing.
                Without it, this calls the Anthropic API and costs money (needs ANTHROPIC_API_KEY).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys

from mcp.client.client import Client

from domino.agent.context import get_context
from domino.agent.loop import approve, new_run, reject, run_phase
from domino.agent.scenarios import SCENARIOS
from domino.config import settings
from domino.graph.lifecycle import reset_live
from domino.mcp.server import mcp


def _print(ev: dict) -> None:
    d, t = ev["data"], ev["type"]
    if t == "tool.called":
        print(f"  → [{d['step']:>2}] {d['tool']}({json.dumps(d['args'], ensure_ascii=False)[:160]})")
    elif t == "tool.result":
        mark = "✗" if d["is_error"] else "✓"
        print(f"    {mark} {d['result_ref'] or ''} {d['duration_ms']} ms  {d['summary'][:140].replace(chr(10), ' ')}")
    elif t == "agent.note":
        print(f"  ✎ {d['text'][:600]}")
    elif t in ("plan.proposed", "action.executed", "run.error", "approval.failed", "plan.rejected"):
        print(f"  ● {t}: {json.dumps(d, default=str)[:300]}")


async def main_async(scenario: str, dry_run: bool) -> int:
    if dry_run:
        from domino.agent.scripted import ScriptedClient
        client = ScriptedClient(scenario)
        settings.memory_graph = "memory:dryrun"  # scripted lessons must never reach the real memory graph
    else:
        if not settings.anthropic_api_key:
            print("ANTHROPIC_API_KEY is not set in .env. Use DRY_RUN=1 for the free scripted check.")
            return 2
        from anthropic import AsyncAnthropic
        client = AsyncAnthropic(api_key=settings.anthropic_api_key)

    live = reset_live()
    sc = SCENARIOS[scenario]
    run = new_run(scenario, sc["alert"], live)
    run.listeners.append(_print)
    print(f"DOMINO agent  scenario={scenario}  run={run.id}  model={'scripted (dry run)' if dry_run else settings.domino_model}")
    print(f"alert: {sc['alert']}\n")
    async with Client(mcp) as mcp_client:
        await run_phase(run, client, mcp_client)
        while run.status == "awaiting_approval":
            plan = get_context(run.id).pending
            print(f"\n  APPROVAL NEEDED: {plan['decision_id']} ({plan['name']}), spend ${plan['spend_cents'] / 100:,.0f}, "
                  f"{len(plan['pos'])} purchase orders, {len(plan['protected_orders'])} orders protected (projected)")
            for p in plan["pos"]:
                print(f"     {p['site_id']} {p['component_id']} -> {p['plant_id']} {p['rate_wk']}/wk x {p['qty']} "
                      f"by {p['mode']}, ${p['unit_price_cents'] / 100:.2f}/unit")
            answer = "y" if dry_run else input("  Approve? [y = approve / anything else = reject with that feedback] ")
            print()
            if answer.strip().lower() in ("y", "yes"):
                await approve(run, "cli-human" if not dry_run else "dry-run", client, mcp_client)
            else:
                await reject(run, answer.strip() or "rejected", client, mcp_client)
    ctx = get_context(run.id)
    print(f"\nstatus: {run.status}" + (f"  ({run.error})" if run.error else ""))
    if ctx.report:
        print(f"report ({ctx.report['outcome']}): {ctx.report['headline']}")
        for c in ctx.report["claims"]:
            print(f"  - [{c['type']}] {c['text']}  evidence={c.get('evidence_ids', [])} metrics={c.get('metric_refs', [])}")
    u = run.usage
    print(f"\nrequests {u['requests']}  tool calls {run.tool_calls}  tokens: input {u['input']:,}, output {u['output']:,}, "
          f"cache read {u['cache_read']:,}, cache write {u['cache_write']:,}  cost ${run.cost_usd:.4f}")
    return 0 if run.status == "completed" else 1


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("scenario", nargs="?", default="monsoon", choices=sorted(SCENARIOS))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    return asyncio.run(main_async(args.scenario, args.dry_run))


if __name__ == "__main__":
    raise SystemExit(main())
