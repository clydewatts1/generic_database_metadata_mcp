"""MCP application instance – imported by all tool modules and exposed as ASGI app.

Keeping the mcp instance in its own module breaks the circular import that
would arise if tools imported from server.py and server.py imported tools.

For SSE transport, the FastMCP instance is run as an ASGI app via uvicorn.
"""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    name="GlossaryWeaver",
    instructions=(
        "You are connected to a stigmergic metadata graph via GlossaryWeaver. "
        "Use the available tools to register types, ingest nodes, create relationships, "
        "and query the graph. All responses are compact TOON-serialised JSON. "
        "Payloads are capped at 10 KB. Paginate large result sets using the `page` parameter."
    ),
)

# Expose the FastMCP instance as an ASGI app for SSE transport
app = mcp.sse_app
