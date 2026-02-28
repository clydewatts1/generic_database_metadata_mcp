"""Health service for the Schema Health Dashboard Widget.

Implements FR-001, FR-004, FR-005, FR-007, FR-010, FR-011, FR-012 from
spec.md (001-schema-health-widget).

Exports:
  - compute_health_band  — FR-003: map health_score → "green" / "amber" / "red"
  - HealthService        — FastAPI injectable service
"""

from __future__ import annotations

import os

from fastapi import HTTPException, status

from .models import DashboardUser, HealthPayloadResponse, MetaTypeHealthResponse


# Module-level patchable wrapper — allows tests to monkeypatch
# ``src.dashboard.health_service.list_meta_types`` without importing the
# FalkorDB client at module load time (avoids connection attempts during import).
def list_meta_types(domain_scope: str):  # type: ignore[return]
    """Thin wrapper around ``src.graph.ontology.list_meta_types`` for test patching."""
    from src.graph.ontology import list_meta_types as _real_list_meta_types
    return _real_list_meta_types(domain_scope)

# ---------------------------------------------------------------------------
# FR-003: Health band computation
# ---------------------------------------------------------------------------

_DEFAULT_NODE_LIMIT = 500


def compute_health_band(score: float) -> str:
    """Map a health_score to a colour band string.

    Thresholds (FR-003, data-model.md §MetaTypeHealthRecord):
        score >= 0.8  → "green"
        score >= 0.5  → "amber"   (0.5 is inclusive lower bound)
        score <  0.5  → "red"
    """
    if score >= 0.8:
        return "green"
    if score >= 0.5:
        return "amber"
    return "red"


# ---------------------------------------------------------------------------
# HealthService — FastAPI-injectable service class
# ---------------------------------------------------------------------------


class HealthService:
    """Provides health payload data for the health widget endpoint.

    Designed for FastAPI ``Depends(HealthService)`` injection.
    """

    def get_health_payload(self, user: DashboardUser) -> HealthPayloadResponse:
        """Fetch MetaType health data scoped to the user's domain.

        Behaviour:
          - Calls ``list_meta_types(user.domain_scope)`` from ``src.graph.ontology``
          - Sorts results by ``health_score`` ascending (unhealthiest first — FR-008)
          - Applies ``DASHBOARD_NODE_LIMIT`` cap (default 500)
          - Sets ``truncated`` and ``total_available`` accordingly (FR-012)
          - Computes ``health_band`` for each item (FR-003)
          - Wraps any exception as HTTP 503 (FR-010)

        Args:
            user: Authenticated DashboardUser from the USL dependency.

        Returns:
            HealthPayloadResponse envelope.

        Raises:
            HTTPException(503): On any FalkorDB failure or unexpected exception.
        """
        node_limit = int(os.environ.get("DASHBOARD_NODE_LIMIT", str(_DEFAULT_NODE_LIMIT)))

        try:
            meta_types = list_meta_types(user.domain_scope)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "status": "degraded",
                    "message": "Schema health data temporarily unavailable",
                },
            ) from exc

        # Sort ascending by health_score so unhealthiest MetaTypes appear first (FR-008)
        meta_types.sort(key=lambda mt: mt.health_score)

        total_available = len(meta_types)
        truncated = total_available > node_limit
        visible = meta_types[:node_limit]

        items = [
            MetaTypeHealthResponse(
                id=mt.id,
                name=mt.name,
                type_category=mt.type_category.value if hasattr(mt.type_category, "value") else str(mt.type_category),
                health_score=mt.health_score,
                health_band=compute_health_band(mt.health_score),
                domain_scope=mt.domain_scope,
            )
            for mt in visible
        ]

        return HealthPayloadResponse(
            items=items,
            total_available=total_available,
            truncated=truncated,
        )
