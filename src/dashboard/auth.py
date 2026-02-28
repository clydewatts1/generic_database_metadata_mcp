"""JWT authentication dependency for the Visual Web Dashboard.

Decodes HS256 Bearer tokens and extracts ``profile_id`` + ``domain_scope``
claims into a ``DashboardUser`` instance.

Rules enforced:
- HTTP 401 for missing, malformed, or expired tokens.
- HTTP 403 for tokens that lack ``profile_id`` or ``domain_scope`` claims.
- Rule 5.2: ``domain_scope`` is read from the JWT claim only — never from
  query params or request body.
"""

from __future__ import annotations

import os

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .models import DashboardUser

_bearer_scheme = HTTPBearer(auto_error=False)

_ALGORITHM = "HS256"


def _get_secret() -> str:
    """Return the JWT signing secret from the environment.

    Raises:
        RuntimeError: if ``DASHBOARD_JWT_SECRET`` is not set (startup guard is
            in api.py, but auth.py also guards defensively at decode-time).
    """
    secret = os.environ.get("DASHBOARD_JWT_SECRET", "")
    if not secret:
        raise RuntimeError(
            "DASHBOARD_JWT_SECRET environment variable is not set. "
            "Cannot validate JWT tokens."
        )
    return secret


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> DashboardUser:
    """FastAPI dependency: decode JWT and return the authenticated DashboardUser.

    Raises:
        HTTPException 401: token absent, malformed, or expired.
        HTTPException 403: token valid but missing ``profile_id`` or
            ``domain_scope`` claims.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    try:
        secret = _get_secret()
        payload = jwt.decode(token, secret, algorithms=[_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except RuntimeError as exc:
        # Secret not configured — treat as server-side auth failure
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )

    profile_id: str | None = payload.get("profile_id")
    domain_scope: str | None = payload.get("domain_scope")

    if not profile_id or not domain_scope:
        missing = []
        if not profile_id:
            missing.append("profile_id")
        if not domain_scope:
            missing.append("domain_scope")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Token is missing required claims: {', '.join(missing)}",
        )

    return DashboardUser(profile_id=profile_id, domain_scope=domain_scope)
