"""Health API router for the Schema Health Dashboard Widget.

Registers GET /api/health/meta-types with the Unified Security Layer.

Rule 5.6 compliance: USL is applied at the router constructor level via the
``dependencies`` argument, ensuring every route under this router is protected.
This satisfies R-003 (Universal security — no route-level bypass possible).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from .auth import get_current_user
from .health_service import HealthService
from .models import DashboardUser, HealthPayloadResponse
from .security import unified_security

health_router = APIRouter(
    prefix="/api/health",
    tags=["health"],
    dependencies=[Depends(unified_security)],
)


@health_router.get(
    "/meta-types",
    response_model=HealthPayloadResponse,
    summary="Get MetaType health scores for the authenticated user's domain",
)
def get_health_meta_types(
    user: DashboardUser = Depends(get_current_user),
    health_service: HealthService = Depends(HealthService),
) -> HealthPayloadResponse:
    """Return health scores for all MetaTypes within the user's domain scope.

    Covers FR-001, FR-002, FR-011.
    The Unified Security Layer (Rule 5.6) is enforced at the router level.
    """
    return health_service.get_health_payload(user)
