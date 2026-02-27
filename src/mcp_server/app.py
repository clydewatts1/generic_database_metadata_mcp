"""MCP application instance – imported by all tool modules.

Keeping the mcp instance in its own module breaks the circular import that
would arise if tools imported from server.py and server.py imported tools.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP  # Standard mcp.server.fastmcp from mcp package

mcp = FastMCP(
    name="StigmergicMetadataServer",
    instructions=(
        "You are connected to a stigmergic metadata graph. "
        "Use the available tools to register types, ingest nodes, create relationships, "
        "and query the graph. All responses are compact TOON-serialised JSON. "
        "Payloads are capped at 10 KB. Paginate large result sets using the `page` parameter."
    ),
)
