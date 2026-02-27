"""MCP server entry-point for the Stigmergic MCP Metadata Server.

Uses the standard mcp.server.fastmcp.FastMCP from the mcp package.
"""

from __future__ import annotations

from .app import mcp  # noqa: F401 – re-export for convenience
from ..utils.logging import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Tool registration – tools are registered in their own modules and imported
# here so that @mcp.tool decorators fire against the shared mcp instance.
# ---------------------------------------------------------------------------

def _register_tools() -> None:
    """Import tool modules so their @mcp.tool decorators fire."""
    # Imported for side-effects (decorator registration)
    from .tools import ontology, ingestion, stigmergy, query  # noqa: F401
    logger.info("All MCP tools registered.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    _register_tools()
    logger.info("Starting Stigmergic MCP Metadata Server...")
    mcp.run()
