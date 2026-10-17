"""Settings loaded from the repo-root .env (never committed)."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=REPO_ROOT / ".env", extra="ignore")

    anthropic_api_key: str = ""
    domino_model: str = "claude-opus-5-5"
    domino_effort: str = "medium"
    domino_max_tool_calls: int = 30

    falkordb_host: str = "localhost"
    falkordb_port: int = 6379

    world_seed: int = 42
    world_graph_pristine: str = "world:pristine"
    world_graph_live: str = "world:live"
    memory_graph: str = "memory"
    memory_graph_dryrun: str = "memory:dryrun"  # scripted (Demo) runs write here, never to `memory`
    record_replays: bool = True  # save each war-room run to backend/runs/replays/ for replay mode

    mcp_api_key: str = ""
    live_runs_per_hour_per_ip: int = 5
    live_runs_per_day: int = 40  # global daily cap on real (paid) agent runs

    # Deployment
    domino_public_host: str = ""  # e.g. 203-0-113-7.sslip.io; added to the MCP allowed Host headers
    domino_static_dir: str = ""   # built frontend (frontend/dist); served at / when set


settings = Settings()
