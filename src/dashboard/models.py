"""Pydantic response models for the Visual Web Dashboard.

These are read-only serialisation models — they introduce no new graph entities.
See data-model.md for field-level specification.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# GraphNodeResponse
# ---------------------------------------------------------------------------

class GraphNodeResponse(BaseModel):
    """Single renderable node on the Cytoscape.js canvas."""

    id: str = Field(..., min_length=1)
    label: str
    business_name: str | None = None
    meta_type_name: str
    domain_scope: str
    properties: dict[str, Any] = Field(default_factory=dict)

    @field_validator("id")
    @classmethod
    def id_non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("GraphNodeResponse.id must not be blank")
        return v


# ---------------------------------------------------------------------------
# GraphEdgeResponse
# ---------------------------------------------------------------------------

class GraphEdgeResponse(BaseModel):
    """Single renderable edge on the Cytoscape.js canvas.

    Synthetic ID is ``"{source_id}__{edge_type}__{target_id}"``.
    Stigmergic fields (confidence_score, rationale_summary, last_accessed) are
    populated only when is_stigmergic=True; they must be None otherwise.
    """

    id: str
    source_id: str
    target_id: str
    edge_type: str
    is_stigmergic: bool

    # Stigmergic-only fields (None for structural edges)
    confidence_score: float | None = None
    rationale_summary: str | None = None
    last_accessed: str | None = None  # ISO-8601 string

    @field_validator("confidence_score")
    @classmethod
    def clamp_confidence(cls, v: float | None) -> float | None:
        """Clamp confidence_score to [0.0, 1.0]."""
        if v is None:
            return None
        return max(0.0, min(1.0, v))

    @model_validator(mode="after")
    def stigmergic_fields_consistent(self) -> "GraphEdgeResponse":
        """Structural edges must have all stigmergic fields as None."""
        if not self.is_stigmergic:
            if self.confidence_score is not None:
                raise ValueError("confidence_score must be None for non-stigmergic edges")
            if self.rationale_summary is not None:
                raise ValueError("rationale_summary must be None for non-stigmergic edges")
            if self.last_accessed is not None:
                raise ValueError("last_accessed must be None for non-stigmergic edges")
        return self


# ---------------------------------------------------------------------------
# GraphPayloadResponse
# ---------------------------------------------------------------------------

class GraphPayloadResponse(BaseModel):
    """Top-level response envelope returned by GET /api/graph."""

    nodes: list[GraphNodeResponse]
    edges: list[GraphEdgeResponse]
    meta_types: list[str]
    node_count: int
    truncated: bool
    scope: str


# ---------------------------------------------------------------------------
# DashboardUser — internal JWT claim model (never serialised to browser)
# ---------------------------------------------------------------------------

class DashboardUser(BaseModel):
    """Decoded JWT claims for the requesting dashboard user."""

    profile_id: str
    domain_scope: str


# ---------------------------------------------------------------------------
# MetaTypeHealthResponse — 001-schema-health-widget (T002)
# ---------------------------------------------------------------------------

_VALID_BANDS = {"green", "amber", "red"}


class MetaTypeHealthResponse(BaseModel):
    """Health summary for a single MetaType node returned by GET /api/health/meta-types."""

    id: str
    name: str
    type_category: str
    health_score: float = Field(..., ge=0.0, le=1.0)
    health_band: str  # "green" | "amber" | "red"
    domain_scope: str

    @field_validator("health_score")
    @classmethod
    def clamp_health_score(cls, v: float) -> float:
        """Clamp health_score to [0.0, 1.0]."""
        return max(0.0, min(1.0, v))

    @field_validator("health_band")
    @classmethod
    def validate_health_band(cls, v: str) -> str:
        if v not in _VALID_BANDS:
            raise ValueError(f"health_band must be one of {_VALID_BANDS}, got {v!r}")
        return v


class HealthPayloadResponse(BaseModel):
    """Top-level response envelope for GET /api/health/meta-types."""

    items: list[MetaTypeHealthResponse]
    total_available: int
    truncated: bool
    audit_status: str = "ok"  # "ok" | "failed"
