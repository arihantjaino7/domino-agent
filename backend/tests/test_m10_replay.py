"""Replay mode: a run is recorded with world snapshots, and only published recordings can be read back.

Uses the scripted stand-in (free) on test:m10:* graphs; recordings go to pytest's tmp_path.
"""

import asyncio
import json

import pytest
from fastapi.testclient import TestClient
from mcp.client.client import Client

from domino.agent.context import get_context
from domino.agent.loop import approve, emit, new_run, run_phase
from domino.agent.scenarios import SCENARIOS
from domino.agent.scripted import ScriptedClient
from domino.api import replays
from domino.api.main import app
from domino.config import settings
from domino.graph.lifecycle import build_pristine, drop_graph
from domino.mcp.server import mcp
from domino.seed.generator import generate

WORLD, MEM = "test:m10:world", "test:m10:memory"


@pytest.fixture(scope="module")
def recording(tmp_path_factory):
    out = tmp_path_factory.mktemp("replays")
    build_pristine(generate(42), WORLD)
    mp = pytest.MonkeyPatch()
    mp.setattr(settings, "world_graph_live", WORLD)     # the recorder snapshots the live world view
    mp.setattr(settings, "memory_graph_dryrun", MEM)

    async def go():
        run = new_run("monsoon", SCENARIOS["monsoon"]["alert"], WORLD, scripted=True)
        replays.attach_recorder(run, out)
        emit(run, "run.started", {"scenario": "monsoon", "alert": run.alert_text, "dry_run": True, "model": "scripted"})
        client = ScriptedClient("monsoon")
        async with Client(mcp) as mc:
            await run_phase(run, client, mc)
            assert run.status == "awaiting_approval"
            await approve(run, "tester", client, mc)
        return run

    run = asyncio.run(go())
    assert run.status == "completed", run.error
    rec = json.loads((out / f"{run.id}.json").read_text(encoding="utf-8"))
    yield run, rec
    mp.undo()
    for g in (WORLD, MEM):
        drop_graph(g)


def _seq_of(rec, kind, tool=None):
    return next(e["seq"] for e in rec["events"] if e["type"] == kind and (tool is None or e["data"].get("tool") == tool))


def test_recording_keeps_every_event_and_says_who_drove_it(recording):
    run, rec = recording
    assert rec["format"] == 1 and rec["id"] == run.id and rec["title"] == SCENARIOS["monsoon"]["title"]
    assert [e["seq"] for e in rec["events"]] == [e["seq"] for e in run.events]
    assert rec["agent"] == "Scripted stand-in (no model)" and rec["real_model"] is False
    assert rec["status"] == "completed"


def test_world_snapshots_are_taken_where_the_live_war_room_refreshes(recording):
    _, rec = recording
    at = [f["after_seq"] for f in rec["frames"]]
    assert at[0] == 0                                                       # before the first event
    for seq in (_seq_of(rec, "tool.result", "declare_incident"), _seq_of(rec, "tool.result", "verify_execution"),
                _seq_of(rec, "action.executed"), _seq_of(rec, "run.completed")):
        assert seq in at
    assert at == sorted(at)


def test_snapshots_show_the_world_as_it_was_at_that_moment(recording):
    _, rec = recording
    def volt(frame):
        return next(n for n in frame["graph"]["nodes"] if n["id"] == "S-VOLT-AYU")["data"]["status"]
    declared = _seq_of(rec, "tool.result", "declare_incident")
    first, after = rec["frames"][0], next(f for f in rec["frames"] if f["after_seq"] == declared)
    assert volt(first) != "disrupted" and volt(after) == "disrupted"
    assert first["summary"]["incidents"] == [] and after["summary"]["incidents"]
    executed = next(f for f in rec["frames"] if f["after_seq"] == _seq_of(rec, "action.executed"))
    assert executed["summary"]["totals"]["projected_late"] < after["summary"]["totals"]["projected_late"]


def test_only_published_recordings_can_be_read(recording, tmp_path, monkeypatch):
    _, rec = recording
    (tmp_path / "monsoon-demo.json").write_text(json.dumps({**rec, "title": "Flood, scripted"}), encoding="utf-8")
    (tmp_path / "Bad Name.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(replays, "PUBLISHED_DIR", tmp_path)
    with TestClient(app) as c:
        listed = c.get("/api/replays").json()["replays"]
        assert [r["id"] for r in listed] == ["monsoon-demo"]                # names that fail the id rule are skipped
        assert listed[0]["title"] == "Flood, scripted" and listed[0]["events"] == len(rec["events"])
        full = c.get("/api/replays/monsoon-demo").json()
        assert full["frames"] and full["events"]
        assert c.get("/api/replays/nope").status_code == 404
        assert c.get("/api/replays/..%2F..%2F.env").status_code == 404
