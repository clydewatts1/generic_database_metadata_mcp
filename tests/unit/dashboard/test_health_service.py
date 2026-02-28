"""Unit tests for src/dashboard/health_service.py.

T009: HealthService.get_health_payload() behaviour
T013: compute_health_band() colour band boundaries (SC-002)

Coverage:
  - FR-005: In-scope MetaTypes returned
  - FR-007: FalkorDB exceptions → HTTP 503
  - FR-010: Degraded state shape
  - FR-012: Cap + truncation
  - SC-002: All six boundary scores map to correct band
  - SC-004: Domain isolation (handled upstream by list_meta_types; tested here indirectly)
"""

from __future__ import annotations

import pytest

from src.models.base import MetaType, TypeCategory


# ---------------------------------------------------------------------------
# Helper: build a minimal MetaType for testing
# ---------------------------------------------------------------------------

def _mt(
    name: str = "TestType",
    health_score: float = 1.0,
    domain_scope: str = "Finance",
    type_category: TypeCategory = TypeCategory.NODE,
) -> MetaType:
    return MetaType(
        name=name,
        type_category=type_category,
        schema_definition={"type": "object", "properties": {}},
        health_score=health_score,
        domain_scope=domain_scope,
    )


def _user(domain_scope: str = "Finance", profile_id: str = "analyst_1"):
    from src.dashboard.models import DashboardUser
    return DashboardUser(profile_id=profile_id, domain_scope=domain_scope)


# ---------------------------------------------------------------------------
# TestComputeHealthBand — boundary tests (T013 / SC-002)
# ---------------------------------------------------------------------------

class TestComputeHealthBand:
    """SC-002: Colour band boundaries."""

    @pytest.mark.parametrize("score,expected_band", [
        (0.0, "red"),
        (0.1, "red"),
        (0.49, "red"),
        (0.4999, "red"),
        (0.5, "amber"),
        (0.5001, "amber"),
        (0.65, "amber"),
        (0.79, "amber"),
        (0.7999, "amber"),
        (0.8, "green"),
        (0.8001, "green"),
        (1.0, "green"),
    ])
    def test_band_boundary(self, score: float, expected_band: str):
        from src.dashboard.health_service import compute_health_band
        assert compute_health_band(score) == expected_band

    def test_all_sc002_required_boundary_scores(self):
        """SC-002: Explicitly assert all six boundary values from spec."""
        from src.dashboard.health_service import compute_health_band
        required = [
            (0.0, "red"),
            (0.49, "red"),
            (0.5, "amber"),
            (0.79, "amber"),
            (0.8, "green"),
            (1.0, "green"),
        ]
        for score, band in required:
            result = compute_health_band(score)
            assert result == band, f"compute_health_band({score}) = {result!r}, expected {band!r}"

    def test_colour_band_via_service_end_to_end(self, monkeypatch):
        """End-to-end: health_band in response matches compute_health_band."""
        from src.dashboard.health_service import HealthService, compute_health_band
        items = [
            _mt("GreenType", health_score=1.0, domain_scope="Finance"),
            _mt("AmberType", health_score=0.65, domain_scope="Finance"),
            _mt("RedType", health_score=0.2, domain_scope="Finance"),
        ]
        monkeypatch.setattr(
            "src.dashboard.health_service.list_meta_types",
            lambda scope: items,
        )
        svc = HealthService()
        payload = svc.get_health_payload(_user("Finance"))
        bands = {item.name: item.health_band for item in payload.items}
        assert bands["GreenType"] == "green"
        assert bands["AmberType"] == "amber"
        assert bands["RedType"] == "red"


# ---------------------------------------------------------------------------
# TestHealthServiceGetHealthPayload — T009
# ---------------------------------------------------------------------------

class TestHealthServiceGetHealthPayload:
    """FR-005, FR-007, FR-010, FR-012, SC-004."""

    def test_returns_items_for_domain(self, monkeypatch):
        """Finance MetaTypes are returned as MetaTypeHealthResponse items."""
        from src.dashboard.health_service import HealthService
        items = [
            _mt("CustomerLoan", health_score=1.0, domain_scope="Finance"),
            _mt("LoanProduct", health_score=0.3, domain_scope="Finance"),
        ]
        monkeypatch.setattr(
            "src.dashboard.health_service.list_meta_types",
            lambda scope: items,
        )
        svc = HealthService()
        payload = svc.get_health_payload(_user("Finance"))
        assert payload.total_available == 2
        assert len(payload.items) == 2
        assert payload.truncated is False

    def test_empty_domain_returns_empty_items(self, monkeypatch):
        """Empty domain → items=[], truncated=False, total_available=0."""
        from src.dashboard.health_service import HealthService
        monkeypatch.setattr(
            "src.dashboard.health_service.list_meta_types",
            lambda scope: [],
        )
        svc = HealthService()
        payload = svc.get_health_payload(_user("HR"))
        assert payload.items == []
        assert payload.total_available == 0
        assert payload.truncated is False

    def test_cap_truncation(self, monkeypatch):
        """Cap of 2 with 3 MetaTypes → truncated=True, total_available=3, 2 items."""
        import os
        from src.dashboard.health_service import HealthService
        monkeypatch.setenv("DASHBOARD_NODE_LIMIT", "2")
        monkeypatch.setattr(
            "src.dashboard.health_service.list_meta_types",
            lambda scope: [_mt(f"Type{i}", health_score=0.1 * i) for i in range(1, 4)],
        )
        svc = HealthService()
        payload = svc.get_health_payload(_user("Finance"))
        assert payload.total_available == 3
        assert len(payload.items) == 2
        assert payload.truncated is True

    def test_exact_cap_not_truncated(self, monkeypatch):
        """Exactly at the cap → truncated=False."""
        from src.dashboard.health_service import HealthService
        monkeypatch.setenv("DASHBOARD_NODE_LIMIT", "3")
        monkeypatch.setattr(
            "src.dashboard.health_service.list_meta_types",
            lambda scope: [_mt(f"T{i}", health_score=0.1 * i) for i in range(1, 4)],
        )
        svc = HealthService()
        payload = svc.get_health_payload(_user("Finance"))
        assert payload.total_available == 3
        assert payload.truncated is False

    def test_connection_error_raises_503(self, monkeypatch):
        """FR-010: ConnectionError → HTTPException(503, degraded)."""
        from fastapi import HTTPException
        from src.dashboard.health_service import HealthService
        monkeypatch.setattr(
            "src.dashboard.health_service.list_meta_types",
            MagicMock(side_effect=ConnectionError("DB unreachable")),
        )
        svc = HealthService()
        with pytest.raises(HTTPException) as exc_info:
            svc.get_health_payload(_user("Finance"))
        assert exc_info.value.status_code == 503
        assert exc_info.value.detail["status"] == "degraded"

    def test_runtime_error_raises_503(self, monkeypatch):
        """FR-010: Any unexpected exception → HTTPException(503)."""
        from fastapi import HTTPException
        from src.dashboard.health_service import HealthService
        monkeypatch.setattr(
            "src.dashboard.health_service.list_meta_types",
            MagicMock(side_effect=RuntimeError("unexpected")),
        )
        svc = HealthService()
        with pytest.raises(HTTPException) as exc_info:
            svc.get_health_payload(_user("Finance"))
        assert exc_info.value.status_code == 503

    def test_items_sorted_ascending_by_health_score(self, monkeypatch):
        """FR-008: Items sorted ascending (unhealthiest first)."""
        from src.dashboard.health_service import HealthService
        items = [
            _mt("HealthyType", health_score=1.0),
            _mt("SickType", health_score=0.1),
            _mt("MediocreType", health_score=0.5),
        ]
        monkeypatch.setattr(
            "src.dashboard.health_service.list_meta_types",
            lambda scope: items,
        )
        svc = HealthService()
        payload = svc.get_health_payload(_user("Finance"))
        scores = [item.health_score for item in payload.items]
        assert scores == sorted(scores), "Items must be sorted ascending by health_score"
        assert payload.items[0].name == "SickType"

    def test_health_score_preserved_in_response(self, monkeypatch):
        """Health score value from MetaType is preserved in the response item."""
        from src.dashboard.health_service import HealthService
        monkeypatch.setattr(
            "src.dashboard.health_service.list_meta_types",
            lambda scope: [_mt("MyType", health_score=0.73)],
        )
        svc = HealthService()
        payload = svc.get_health_payload(_user("Finance"))
        assert len(payload.items) == 1
        assert abs(payload.items[0].health_score - 0.73) < 1e-6


# Import MagicMock at module level for test_connection_error_raises_503
from unittest.mock import MagicMock
