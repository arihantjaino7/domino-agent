"""One shared FalkorDB connection for the process."""

from functools import lru_cache

from falkordb import FalkorDB

from domino.config import settings


@lru_cache(maxsize=1)
def get_db() -> FalkorDB:
    return FalkorDB(host=settings.falkordb_host, port=settings.falkordb_port)


def ping() -> dict:
    """Round-trip to the server and report the graph module version."""
    conn = get_db().connection
    conn.ping()
    modules = conn.execute_command("MODULE", "LIST")
    graph_ver = None
    for mod in modules:
        fields = dict(zip(mod[::2], mod[1::2]))
        name = fields.get(b"name", fields.get("name"))
        if name in (b"graph", "graph"):
            graph_ver = fields.get(b"ver", fields.get("ver"))
    return {"falkordb": "ok", "graph_module_ver": graph_ver}
