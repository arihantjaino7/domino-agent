"""MCP server (official SDK; in mcp 2.x `FastMCP` is called `MCPServer`).

M1 only registers a read-only `health` tool so the spike can prove the mount works.
The real tool catalogue (PLAN §9.4) lands in M7.
"""

from mcp.server.mcpserver import MCPServer

from domino.graph.client import ping

mcp = MCPServer(name="domino")


@mcp.tool()
def health() -> dict:
    """Check that DOMINO can reach FalkorDB."""
    return ping()
