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

    mcp_api_key: str = ""
    live_runs_per_hour_per_ip: int = 5


settings = Settings()
