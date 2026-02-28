"""FastAPI application for the Visual Web Dashboard.

Serves:
  - GET /health            → {"status": "ok"} or {"status": "degraded"} with 503
  - GET /api/graph         → GraphPayloadResponse (added Phase 3, T012)
  - Static files at /      → dashboard/ directory (index.html, app.js, style.css)

Environment variables:
  DASHBOARD_JWT_SECRET  — required; server.py validates this on startup
  DASHBOARD_PORT        — default 8080
  DASHBOARD_NODE_LIMIT  — default 500
  FALKORDB_HOST         — default localhost
  FALKORDB_PORT         — default 6379

Note: The DASHBOARD_JWT_SECRET startup guard lives in server.py (production entrypoint).
      Tests set the env var via monkeypatch before exercising auth endpoints.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------

def create_app() -> FastAPI:
    """Create and configure the FastAPI dashboard application."""
    app = FastAPI(
        title="Metadata Graph Dashboard",
        description="Read-only visual dashboard for the metadata graph.",
        version="1.0.0",
    )
    _mount_static(app)
    _register_routes(app)
    return app


def _mount_static(app: FastAPI) -> None:
    """Mount the frontend static files from the dashboard/ directory."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    dashboard_dir = repo_root / "dashboard"

    if dashboard_dir.is_dir():
        app.mount("/static", StaticFiles(directory=str(dashboard_dir)), name="dashboard_static")
    else:
        import logging
        logging.getLogger(__name__).warning(
            "dashboard/ directory not found at %s — static files will not be served",
            dashboard_dir,
        )


def _register_routes(app: FastAPI) -> None:
    """Register all API routes on the app."""
    from fastapi.responses import FileResponse, JSONResponse

    repo_root = Path(__file__).resolve().parent.parent.parent
    index_html = repo_root / "dashboard" / "index.html"

    @app.get("/", include_in_schema=False)
    async def serve_index():
        if index_html.is_file():
            return FileResponse(str(index_html))
        return JSONResponse({"detail": "Dashboard not found."}, status_code=404)

    @app.get("/health", tags=["health"])
    async def health():
        """Health check — probes FalkorDB and returns 200 ok or 503 degraded (T033)."""
        try:
            from src.graph.client import execute_query
            execute_query("RETURN 1", {})
            return {"status": "ok"}
        except Exception as exc:  # noqa: BLE001
            import logging
            logging.getLogger(__name__).warning("Health probe: FalkorDB unreachable: %s", exc)
            return JSONResponse(
                {"status": "degraded", "detail": "Graph engine unavailable"},
                status_code=503,
            )

    # /api/graph route registered from router.py (created in T012)
    try:
        from .router import api_router
        app.include_router(api_router, prefix="/api")
    except ImportError:
        pass  # router.py is created in Phase 3 (T012)


# ---------------------------------------------------------------------------
# Module-level app instance (used by uvicorn: src.dashboard.api:app)
# ---------------------------------------------------------------------------

app = create_app()


