"""FastAPI app: REST under /api, MCP (streamable HTTP) under /mcp, and the built frontend at /."""

import asyncio
import hmac
import json
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import parse_qs

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from mcp.server.transport_security import TransportSecuritySettings

from domino.api.delivery import router as delivery_router
from domino.api.live import router as live_router
from domino.api.memory import router as memory_router
from domino.api.replays import router as replays_router
from domino.api.runs import router as runs_router
from domino.api.world import router as world_router
from domino.api.xray import router as xray_router
from domino.config import settings
from domino.graph.client import ping
from domino.mcp.server import mcp

# The SDK rejects foreign Host headers with 421 (DNS-rebinding protection), so the public
# hostname must be listed when deployed behind Caddy.
_hosts = ["127.0.0.1:*", "localhost:*", "127.0.0.1", "localhost"]
if settings.domino_public_host:
    _hosts += [settings.domino_public_host, f"{settings.domino_public_host}:*"]
_security = TransportSecuritySettings(
    enable_dns_rebinding_protection=True, allowed_hosts=_hosts,
    allowed_origins=[f"https://{h}" for h in _hosts if "*" not in h] + [f"http://{h}" for h in _hosts if "*" not in h])

# Build the MCP sub-app first: this also creates its session manager.
mcp_app = mcp.streamable_http_app(streamable_http_path="/", transport_security=_security)
_mcp_started = False


class RequireMcpKey:
    """If MCP_API_KEY is set, /mcp needs `Authorization: Bearer <key>`, `X-API-Key: <key>` or `?key=<key>`.

    The public demo exposes tools that change the live world, so external MCP clients must hold the key.
    The query form is for clients that cannot send headers (custom connectors in claude.ai / Claude Desktop).
    (DOMINO's own agent calls the same server in-process and never goes through this door.)
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        key = settings.mcp_api_key
        if scope["type"] == "http" and key:
            headers = {k.decode().lower(): v.decode() for k, v in scope.get("headers", [])}
            query = parse_qs(scope.get("query_string", b"").decode())
            ok = (hmac.compare_digest(headers.get("x-api-key", ""), key)
                  or hmac.compare_digest(headers.get("authorization", ""), f"Bearer {key}")
                  or hmac.compare_digest((query.get("key") or [""])[0], key))
            if not ok:
                body = json.dumps({"error": "MCP API key required"}).encode()
                await send({"type": "http.response.start", "status": 401,
                            "headers": [(b"content-type", b"application/json")]})
                await send({"type": "http.response.body", "body": body})
                return
        await self.app(scope, receive, send)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # The MCP session manager must run inside FastAPI's lifespan or /mcp errors.
    # It can run only once per process; a second app start in the same process (several TestClients in
    # one pytest session) then serves /api without HTTP /mcp. The agent uses in-process MCP either way.
    global _mcp_started
    if _mcp_started:
        yield
        return
    _mcp_started = True
    async with mcp.session_manager.run():
        yield


app = FastAPI(title="DOMINO", lifespan=lifespan)
app.include_router(runs_router)
app.include_router(world_router)
app.include_router(live_router)
app.include_router(memory_router)
app.include_router(replays_router)
app.include_router(xray_router)
app.include_router(delivery_router)


# HEAD too: uptime monitors (UptimeRobot's default) check with HEAD and would see 404 otherwise.
@app.api_route("/api/health", methods=["GET", "HEAD"])
async def health():
    try:
        info = await asyncio.to_thread(ping)
    except Exception as exc:  # FalkorDB down or unreachable
        return JSONResponse({"status": "degraded", "falkordb": "down", "error": str(exc)}, status_code=503)
    return {"status": "ok", **info}


app.mount("/mcp", RequireMcpKey(mcp_app))

# One origin in production: the built frontend is served by the same app (no CORS). Mounted last.
if settings.domino_static_dir and Path(settings.domino_static_dir).is_dir():
    app.mount("/", StaticFiles(directory=settings.domino_static_dir, html=True), name="frontend")
