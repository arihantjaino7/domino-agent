"""FastAPI app: REST under /api, MCP (streamable HTTP) under /mcp."""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from domino.graph.client import ping
from domino.mcp.server import mcp

# Build the MCP sub-app first: this also creates its session manager.
mcp_app = mcp.streamable_http_app(streamable_http_path="/")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # The MCP session manager must run inside FastAPI's lifespan or /mcp errors (PLAN §9.4).
    async with mcp.session_manager.run():
        yield


app = FastAPI(title="DOMINO", lifespan=lifespan)


@app.get("/api/health")
async def health():
    try:
        info = await asyncio.to_thread(ping)
    except Exception as exc:  # FalkorDB down or unreachable
        return JSONResponse({"status": "degraded", "falkordb": "down", "error": str(exc)}, status_code=503)
    return {"status": "ok", **info}


app.mount("/mcp", mcp_app)
