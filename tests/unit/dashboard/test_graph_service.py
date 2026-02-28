"""Unit tests for src/dashboard/graph_service.py — DashboardGraphService.

Tests:
- Scope filter passed through correctly (Finance user never gets Marketing nodes)
- 500-node cap sets truncated=True
- business_name=None when absent in properties
- confidence_score clamped to [0.0, 1.0]
- meta_types deduplicated
- StigmergicEdge → is_stigmergic=True (all fields populated)
- Structural edge → is_stigmergic=False (confidence_score / rationale / last_accessed = None)
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.dashboard.graph_service import DashboardGraphService, _NODE_CAP
from src.dashboard.models import DashboardUser


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user(profile_id: str = "user-001", domain_scope: str = "Finance") -> DashboardUser:
    return DashboardUser(profile_id=profile_id, domain_scope=domain_scope)


def _raw_node(
    node_id: str = "n1",
    meta_type_name: str = "Table",
    domain_scope: str = "Finance",
    label: str = "my_table",
    business_name: str | None = None,
) -> dict[str, Any]:
    """Build a raw FalkorDB node dict as returned by _fetch_nodes()."""
    import json
    props: dict[str, Any] = {"label": label}
    if business_name is not None:
        props["business_name"] = business_name
    return {
        "id": node_id,
        "_id": node_id,
        "meta_type_name": meta_type_name,
        "domain_scope": domain_scope,
        "properties": json.dumps(props),
    }


def _raw_stigmergic_edge(
    src: str = "n1",
    tgt: str = "n2",
    confidence: float = 0.75,
    edge_type: str = "RELATES_TO",
) -> dict[str, Any]:
    return {
        "id": f"edge-{src}-{tgt}",
        "source_id": src,
        "target_id": tgt,
        "edge_type": edge_type,
        "confidence_score": confidence,
        "rationale_summary": "Some rationale",
        "last_accessed": "2026-01-01T00:00:00+00:00",
        "domain_scope": "Finance",
    }


# ---------------------------------------------------------------------------
# Scope filter tests
# ---------------------------------------------------------------------------

class TestScopeFilter:
    def test_scope_uses_jwt_domain_scope(self):
        """get_graph() passes domain_scope from DashboardUser to fetch_nodes."""
        svc = DashboardGraphService()
        user = _make_user(domain_scope="Finance")

        with patch.object(svc, "_fetch_nodes", return_value=[]) as mock_fetch, \
             patch.object(svc, "_fetch_stigmergic_edges", return_value=[]), \
             patch.object(svc, "_fetch_structural_edges", return_value=[]):
            result = svc.get_graph(user)
            mock_fetch.assert_called_once_with("Finance")
            assert result.scope == "Finance"

    def test_marketing_user_scope_passed(self):
        svc = DashboardGraphService()
        user = _make_user(domain_scope="Marketing")

        with patch.object(svc, "_fetch_nodes", return_value=[]) as mock_fetch, \
             patch.object(svc, "_fetch_stigmergic_edges", return_value=[]), \
             patch.object(svc, "_fetch_structural_edges", return_value=[]):
            result = svc.get_graph(user)
            mock_fetch.assert_called_once_with("Marketing")
            assert result.scope == "Marketing"


# ---------------------------------------------------------------------------
# 500-node cap tests
# ---------------------------------------------------------------------------

class TestNodeCap:
    def test_under_cap_not_truncated(self):
        svc = DashboardGraphService()
        user = _make_user()
        nodes = [_raw_node(node_id=f"n{i}", business_name=None) for i in range(10)]

        with patch.object(svc, "_fetch_nodes", return_value=nodes), \
             patch.object(svc, "_fetch_stigmergic_edges", return_value=[]), \
             patch.object(svc, "_fetch_structural_edges", return_value=[]):
            result = svc.get_graph(user)
            assert result.truncated is False
            assert result.node_count == 10

    def test_exactly_at_cap_not_truncated(self):
        svc = DashboardGraphService()
        user = _make_user()
        nodes = [_raw_node(node_id=f"n{i}") for i in range(_NODE_CAP)]

        with patch.object(svc, "_fetch_nodes", return_value=nodes), \
             patch.object(svc, "_fetch_stigmergic_edges", return_value=[]), \
             patch.object(svc, "_fetch_structural_edges", return_value=[]):
            result = svc.get_graph(user)
            assert result.truncated is False
            assert result.node_count == _NODE_CAP

    def test_over_cap_truncated_to_500(self):
        svc = DashboardGraphService()
        user = _make_user()
        nodes = [_raw_node(node_id=f"n{i}") for i in range(_NODE_CAP + 50)]

        with patch.object(svc, "_fetch_nodes", return_value=nodes), \
             patch.object(svc, "_fetch_stigmergic_edges", return_value=[]), \
             patch.object(svc, "_fetch_structural_edges", return_value=[]):
            result = svc.get_graph(user)
            assert result.truncated is True
            assert result.node_count == _NODE_CAP
            assert len(result.nodes) == _NODE_CAP


# ---------------------------------------------------------------------------
# business_name tests
# ---------------------------------------------------------------------------

class TestBusinessName:
    def test_business_name_none_when_absent(self):
        svc = DashboardGraphService()
        raw = _raw_node("n1", business_name=None)
        node_response = svc._to_node_response(raw)
        assert node_response.business_name is None

    def test_business_name_populated_when_present(self):
        svc = DashboardGraphService()
        raw = _raw_node("n1", business_name="Customer Revenue Table")
        node_response = svc._to_node_response(raw)
        assert node_response.business_name == "Customer Revenue Table"

    def test_label_used_as_fallback(self):
        svc = DashboardGraphService()
        raw = _raw_node("n1", label="technical_name", business_name=None)
        node_response = svc._to_node_response(raw)
        assert node_response.label == "technical_name"
        assert node_response.business_name is None


# ---------------------------------------------------------------------------
# confidence_score clamp tests
# ---------------------------------------------------------------------------

class TestConfidenceScoreClamp:
    def test_normal_score_unchanged(self):
        svc = DashboardGraphService()
        raw = _raw_stigmergic_edge(confidence=0.85)
        edge = svc._to_stigmergic_edge_response(raw)
        assert edge.confidence_score == pytest.approx(0.85, abs=1e-6)

    def test_score_above_1_clamped_to_1(self):
        svc = DashboardGraphService()
        raw = _raw_stigmergic_edge(confidence=1.5)
        edge = svc._to_stigmergic_edge_response(raw)
        assert edge.confidence_score == pytest.approx(1.0, abs=1e-6)

    def test_score_below_0_clamped_to_0(self):
        svc = DashboardGraphService()
        raw = _raw_stigmergic_edge(confidence=-0.1)
        edge = svc._to_stigmergic_edge_response(raw)
        assert edge.confidence_score == pytest.approx(0.0, abs=1e-6)

    def test_exactly_0_and_1_allowed(self):
        svc = DashboardGraphService()
        raw_zero = _raw_stigmergic_edge(confidence=0.0)
        raw_one = _raw_stigmergic_edge(confidence=1.0)
        assert svc._to_stigmergic_edge_response(raw_zero).confidence_score == pytest.approx(0.0)
        assert svc._to_stigmergic_edge_response(raw_one).confidence_score == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# meta_types deduplication
# ---------------------------------------------------------------------------

class TestMetaTypes:
    def test_meta_types_deduplicated(self):
        svc = DashboardGraphService()
        user = _make_user()
        nodes = [
            _raw_node("n1", meta_type_name="Table"),
            _raw_node("n2", meta_type_name="Table"),  # duplicate
            _raw_node("n3", meta_type_name="Dashboard"),
            _raw_node("n4", meta_type_name="Column"),
        ]

        with patch.object(svc, "_fetch_nodes", return_value=nodes), \
             patch.object(svc, "_fetch_stigmergic_edges", return_value=[]), \
             patch.object(svc, "_fetch_structural_edges", return_value=[]):
            result = svc.get_graph(user)
            assert sorted(result.meta_types) == ["Column", "Dashboard", "Table"]
            assert len(result.meta_types) == 3  # deduplicated


# ---------------------------------------------------------------------------
# Edge mapping tests
# ---------------------------------------------------------------------------

class TestEdgeMapping:
    def test_stigmergic_edge_all_fields_populated(self):
        svc = DashboardGraphService()
        raw = {
            "source_id": "n1",
            "target_id": "n2",
            "edge_type": "RELATES_TO",
            "confidence_score": 0.85,
            "rationale_summary": "Frequently co-accessed",
            "last_accessed": "2026-01-01T12:00:00+00:00",
        }
        edge = svc._to_stigmergic_edge_response(raw)
        assert edge.is_stigmergic is True
        assert edge.confidence_score == pytest.approx(0.85)
        assert edge.rationale_summary == "Frequently co-accessed"
        assert edge.last_accessed == "2026-01-01T12:00:00+00:00"
        assert edge.source_id == "n1"
        assert edge.target_id == "n2"
        assert edge.edge_type == "RELATES_TO"

    def test_full_graph_includes_stigmergic_edges(self):
        svc = DashboardGraphService()
        user = _make_user()
        nodes = [_raw_node("n1"), _raw_node("n2")]
        raw_edges = [_raw_stigmergic_edge("n1", "n2")]

        with patch.object(svc, "_fetch_nodes", return_value=nodes), \
             patch.object(svc, "_fetch_stigmergic_edges", return_value=raw_edges), \
             patch.object(svc, "_fetch_structural_edges", return_value=[]):
            result = svc.get_graph(user)
            assert len(result.edges) == 1
            assert result.edges[0].is_stigmergic is True
            assert result.edges[0].confidence_score is not None

    def test_structural_edge_is_stigmergic_false_null_fields(self):
        """T023: structural edges → is_stigmergic=False, stigmergic fields all None."""
        from src.dashboard.models import GraphEdgeResponse

        svc = DashboardGraphService()
        user = _make_user()
        nodes = [_raw_node("n1"), _raw_node("n2")]

        # Simulate a structural edge returned directly by _fetch_structural_edges
        structural = [
            GraphEdgeResponse(
                id="n1__OWNS__n2",
                source_id="n1",
                target_id="n2",
                edge_type="OWNS",
                is_stigmergic=False,
                confidence_score=None,
                rationale_summary=None,
                last_accessed=None,
            )
        ]

        with patch.object(svc, "_fetch_nodes", return_value=nodes), \
             patch.object(svc, "_fetch_stigmergic_edges", return_value=[]), \
             patch.object(svc, "_fetch_structural_edges", return_value=structural):
            result = svc.get_graph(user)
            assert len(result.edges) == 1
            edge = result.edges[0]
            assert edge.is_stigmergic is False
            assert edge.confidence_score is None
            assert edge.rationale_summary is None
            assert edge.last_accessed is None
            assert edge.edge_type == "OWNS"

    def test_confidence_score_1_5_clamped_to_1_0_via_mapper(self):
        """T023: confidence_score=1.5 → clamped to 1.0 by _to_stigmergic_edge_response."""
        svc = DashboardGraphService()
        raw = _raw_stigmergic_edge(confidence=1.5)
        edge = svc._to_stigmergic_edge_response(raw)
        assert edge.confidence_score == pytest.approx(1.0)
        assert edge.is_stigmergic is True

    def test_confidence_score_negative_clamped_to_0_0_via_mapper(self):
        """T023: confidence_score=-0.1 → clamped to 0.0 by _to_stigmergic_edge_response."""
        svc = DashboardGraphService()
        raw = _raw_stigmergic_edge(confidence=-0.1)
        edge = svc._to_stigmergic_edge_response(raw)
        assert edge.confidence_score == pytest.approx(0.0)
        assert edge.is_stigmergic is True
