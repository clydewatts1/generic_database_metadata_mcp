"""FastMCP server entry-point for the Stigmergic MCP Metadata Server."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from src.utils.logging import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Server Instance
# ---------------------------------------------------------------------------

mcp = FastMCP(
    name="StigmergicMetadataServer",
    instructions=(
        "You are connected to a stigmergic metadata graph. "
        "Use the available tools to register types, ingest nodes, create relationships, "
        "and query the graph. All responses are compact TOON-serialised JSON. "
        "Payloads are capped at 10 KB. Paginate large result sets using the `page` parameter."
    ),
)


# ---------------------------------------------------------------------------
# Tool registration – tools are registered in their own modules and imported
# here so that the @mcp.tool decorator has access to the server instance.
# ---------------------------------------------------------------------------

def _register_tools() -> None:
    """Import tool modules so their @mcp.tool decorators fire."""
    # Imported for side-effects (decorator registration)
    import src.mcp_server.tools.ontology  # noqa: F401
    import src.mcp_server.tools.ingestion  # noqa: F401
    import src.mcp_server.tools.stigmergy  # noqa: F401
    import src.mcp_server.tools.query  # noqa: F401
    logger.info("All MCP tools registered.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    _register_tools()
    logger.info("Starting Stigmergic MCP Metadata Server...")
    mcp.run()
