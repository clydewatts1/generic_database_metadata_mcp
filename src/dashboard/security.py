"""Unified Security Layer (USL) for the Visual Web Dashboard.

Implements Rule 5.6 (Dashboard Unified Security Layer) and Rule 5.7
(Human Audit Logging) from constitution v1.3.0.

Exports:
  - derive_session_id   — R-002: deterministic session identifier from JWT or IP
  - AuditService        — Rule 5.7: writes a (:HumanAuditLog) node before serving data
  - unified_security    — FastAPI dependency: JWT validation → AuditService write-through
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .auth import get_current_user, _bearer_scheme
from .models import DashboardUser

# ---------------------------------------------------------------------------
# R-002: Session ID derivation
# ---------------------------------------------------------------------------


def derive_session_id(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None,
) -> str:
    """Derive a deterministic session identifier from the request context.

    R-002 rules:
      - If a Bearer token is present: ``"tok:{sha256(token)[:8]}"`` (8 hex chars)
      - Otherwise: ``"ip:{client_ip}"`` from X-Forwarded-For or request.client.host
    """
    if credentials is not None and credentials.credentials:
        token_hash = hashlib.sha256(credentials.credentials.encode()).hexdigest()
        return f"tok:{token_hash[:8]}"

    # Fallback: derive from IP address
    forwarded_for = request.headers.get("X-Forwarded-For", "")
    if forwarded_for:
        ip = forwarded_for.split(",")[0].strip()
    elif request.client is not None:
        ip = request.client.host
    else:
        ip = "unknown"
    return f"ip:{ip}"


# ---------------------------------------------------------------------------
# AuditService — Rule 5.7: HumanAuditLog write-through
# ---------------------------------------------------------------------------


class AuditService:
    """Writes (:HumanAuditLog) nodes to FalkorDB before the data query executes.

    A new node is created for every authenticated dashboard request (Rule 5.7).
    Failure to write the audit log raises HTTP 503 — the request is aborted.
    """

    @staticmethod
    def write_audit(
        profile_id: str,
        domain_scope: str,
        endpoint_path: str,
        session_id: str,
        action_type: str = "READ",
    ) -> str:
        """Create a (:HumanAuditLog) node and return its generated ``audit_id``.

        Args:
            profile_id:    JWT ``profile_id`` claim.
            domain_scope:  JWT ``domain_scope`` claim.
            endpoint_path: ``Request.url.path`` value.
            session_id:    Value from :func:`derive_session_id`.
            action_type:   ``"READ"`` (default) or ``"MUTATION"``.

        Returns:
            The generated ``audit_id`` UUID string.

        Raises:
            HTTPException(503): If the FalkorDB write fails for any reason.
        """
        from src.graph.client import execute_query

        audit_id = str(uuid.uuid4())
        timestamp = datetime.now(tz=timezone.utc).isoformat()

        query = (
            "CREATE (a:HumanAuditLog {"
            "  id: $id,"
            "  profile_id: $profile_id,"
            "  domain_scope: $domain_scope,"
            "  action_type: $action_type,"
            "  endpoint_path: $endpoint_path,"
            "  human_session_id: $session_id,"
            "  timestamp: $timestamp,"
            "  entity_summary: null"
            "}) RETURN a.id"
        )
        params = {
            "id": audit_id,
            "profile_id": profile_id,
            "domain_scope": domain_scope,
            "action_type": action_type,
            "endpoint_path": endpoint_path,
            "session_id": session_id,
            "timestamp": timestamp,
        }

        try:
            execute_query(query, params)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "status": "degraded",
                    "message": "Audit log write failed — schema health data unavailable",
                    "audit_status": "failed",
                },
            ) from exc

        return audit_id


# ---------------------------------------------------------------------------
# unified_security — Rule 5.6 FastAPI dependency
# ---------------------------------------------------------------------------


async def unified_security(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    user: DashboardUser = Depends(get_current_user),
) -> DashboardUser:
    """FastAPI dependency implementing Rule 5.6 (Dashboard Unified Security Layer).

    Execution order (R-003):
      1. Validate Bearer token via ``get_current_user`` (raises 401 / 403 on failure)
      2. Derive ``session_id`` from token hash or client IP (R-002)
      3. Write (:HumanAuditLog) via ``AuditService.write_audit`` (raises 503 on failure)
      4. Return the authenticated ``DashboardUser``

    The ``get_current_user`` dependency handles all JWT 401/403 cases before
    this function body executes, so ``user`` is always a valid ``DashboardUser``
    when ``unified_security`` runs.
    """
    session_id = derive_session_id(request, credentials)
    AuditService.write_audit(
        profile_id=user.profile_id,
        domain_scope=user.domain_scope,
        endpoint_path=str(request.url.path),
        session_id=session_id,
    )
    return user
