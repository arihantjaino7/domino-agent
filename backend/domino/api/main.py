"""FastAPI app: REST under /api, MCP (streamable HTTP) under /mcp."""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from domino.api.runs import router as runs_router
from domino.graph.client import ping
from domino.mcp.server import mcp

# Build the MCP sub-app first: this also creates its session manager.
mcp_app = mcp.streamable_http_app(streamable_http_path="/")
_mcp_started = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    # The MCP session manager must run inside FastAPI's lifespan or /mcp errors (PLAN §9.4).
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


@app.get("/api/health")
async def health():
    try:
        info = await asyncio.to_thread(ping)
    except Exception as exc:  # FalkorDB down or unreachable
        return JSONResponse({"status": "degraded", "falkordb": "down", "error": str(exc)}, status_code=503)
    return {"status": "ok", **info}


app.mount("/mcp", mcp_app)
