"""Dashboard server entrypoint.

Usage:
    DASHBOARD_JWT_SECRET=<secret> python -m src.dashboard.server

Or via uvicorn directly:
    DASHBOARD_JWT_SECRET=<secret> uvicorn src.dashboard.api:app --port 8080

Environment variables (see src/dashboard/config.py for full list):
    DASHBOARD_JWT_SECRET  — required JWT signing secret
    DASHBOARD_PORT        — default 8080
"""

from __future__ import annotations

import uvicorn

from .api import app
from .config import get_dashboard_port, get_jwt_secret


def main() -> None:
    """Start the dashboard uvicorn server.

    Validates DASHBOARD_JWT_SECRET before starting — fails loudly if absent.
    """
    get_jwt_secret()  # Raises RuntimeError with helpful message if absent

    port = get_dashboard_port()
    print(f"[dashboard] Starting on http://localhost:{port}")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
