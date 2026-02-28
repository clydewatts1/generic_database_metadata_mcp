"""Dashboard configuration loader.

Reads environment variables and exposes them as typed settings.
Raises ``RuntimeError`` on startup if ``DASHBOARD_JWT_SECRET`` is absent.
"""

from __future__ import annotations

import os


def get_jwt_secret() -> str:
    """Return the JWT signing secret; raises RuntimeError if absent."""
    secret = os.environ.get("DASHBOARD_JWT_SECRET", "")
    if not secret:
        raise RuntimeError(
            "DASHBOARD_JWT_SECRET environment variable must be set before starting "
            "the dashboard server. Generate a token with: "
            "python -c \"import secrets; print(secrets.token_hex(32))\""
        )
    return secret


def get_dashboard_port() -> int:
    """Return DASHBOARD_PORT (default 8080)."""
    return int(os.environ.get("DASHBOARD_PORT", "8080"))


def get_node_limit() -> int:
    """Return DASHBOARD_NODE_LIMIT (default 500)."""
    return int(os.environ.get("DASHBOARD_NODE_LIMIT", "500"))


def get_falkordb_host() -> str:
    """Return FALKORDB_HOST (default localhost)."""
    return os.environ.get("FALKORDB_HOST", "localhost")


def get_falkordb_port() -> int:
    """Return FALKORDB_PORT (default 6379)."""
    return int(os.environ.get("FALKORDB_PORT", "6379"))
