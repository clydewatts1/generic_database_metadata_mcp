"""MCP server entry-point for the Stigmergic MCP Metadata Server.

Uses the standard mcp.server.fastmcp.FastMCP with SSE transport via uvicorn.
"""

import sys

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
    from .tools import ontology, ingestion, stigmergy, query, healing, lifecycle  # noqa: F401
    logger.info("All MCP tools registered.")


# Create ASGI app for SSE transport
def _create_app():
    """Create the ASGI application for SSE transport."""
    _register_tools()
    # mcp.sse_app is a method that returns the ASGI app
    return mcp.sse_app


# For uvicorn to find the app: uvicorn src.mcp_server.server:app
app = _create_app()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logger.info("Starting Stigmergic MCP Metadata Server on http://127.0.0.1:8000 (SSE)...")
    
    try:
        import uvicorn
        
        uvicorn.run(
            app,
            host="127.0.0.1",
            port=8000,
            log_level="info",
        )
    except ImportError:
        logger.error("uvicorn not installed. Install with: pip install uvicorn")
        sys.exit(1)
