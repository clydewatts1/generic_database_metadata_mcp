"""Dashboard API router — registers GET /api/graph.

T012: Scoped graph endpoint (US4, Phase 3).

Security: domain_scope is injected ONLY from the JWT claim via get_current_user()
dependency (Rule 5.2). Query-param scope override is not permitted.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from .auth import get_current_user
from .graph_service import DashboardGraphService
from .models import DashboardUser, GraphPayloadResponse

logger = logging.getLogger(__name__)

api_router = APIRouter()

_graph_service = DashboardGraphService()


@api_router.get(
    "/graph",
    response_model=GraphPayloadResponse,
    summary="Scoped metadata graph payload",
    description=(
        "Returns all ObjectNodes and edges within the caller's permitted "
        "domain_scope (from JWT). Capped at 500 nodes. "
        "Rule 5.2: domain_scope is read from the JWT claim only."
    ),
    tags=["graph"],
)
async def get_graph(
    user: DashboardUser = Depends(get_current_user),
) -> GraphPayloadResponse:
    """Return scoped graph payload for the authenticated user.

    Raises 503 if the graph engine is unreachable.
    """
    try:
        payload = _graph_service.get_graph(user)
    except Exception as exc:
        # Catch connection errors from FalkorDB and return 503
        logger.error("Graph engine error during GET /api/graph: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Graph engine unavailable — please try again later.",
        ) from exc

    logger.debug(
        "GET /api/graph: scope=%s nodes=%d edges=%d truncated=%s",
        user.domain_scope,
        payload.node_count,
        len(payload.edges),
        payload.truncated,
    )
    return payload
