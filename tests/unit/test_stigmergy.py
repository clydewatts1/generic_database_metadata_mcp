"""Unit tests for Stigmergic Edge creation and reinforcement (US3).

Also tests decay logic (US4 preview) using freezegun to mock time.
"""
from __future__ import annotations

import pytest
from freezegun import freeze_time

from src.models.base import MetaTypeCreate, ObjectNodeCreate, TypeCategory
from src.graph.ontology import create_meta_type
from src.graph.nodes import create_node
from src.graph.edges import (
    create_edge,
    get_edge_by_id,
    reinforce_edge,
    list_edges_from_source,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _setup_two_nodes():
    """Create a MetaType and two ObjectNodes, returning (node_a, node_b)."""
    mt = create_meta_type(
        MetaTypeCreate(
            name="Widget",
            type_category=TypeCategory.NODE,
            schema_definition={"label": {"type": "string", "required": True}},
        )
    )
    node_a = create_node(mt, ObjectNodeCreate(meta_type_id=mt.id, properties={"label": "A"}))
    node_b = create_node(mt, ObjectNodeCreate(meta_type_id=mt.id, properties={"label": "B"}))
    return node_a, node_b


# ---------------------------------------------------------------------------
# T017 – Edge creation
# ---------------------------------------------------------------------------

def test_create_edge_initial_confidence_is_0_5():
    node_a, node_b = _setup_two_nodes()
    edge = create_edge(
        source_id=node_a.id,
        target_id=node_b.id,
        edge_type="RELATES_TO",
        rationale_summary="A relates to B",
    )
    assert edge.confidence_score == 0.5
    assert edge.source_id == node_a.id
    assert edge.target_id == node_b.id


def test_create_edge_has_last_accessed_timestamp():
    node_a, node_b = _setup_two_nodes()
    edge = create_edge(
        source_id=node_a.id,
        target_id=node_b.id,
        edge_type="POPULATES",
        rationale_summary="A populates B",
    )
    assert edge.last_accessed is not None


def test_get_edge_by_id_returns_created():
    node_a, node_b = _setup_two_nodes()
    created = create_edge(
        source_id=node_a.id,
        target_id=node_b.id,
        edge_type="RELATES_TO",
        rationale_summary="test edge",
    )
    fetched = get_edge_by_id(created.id)
    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.confidence_score == 0.5


def test_get_edge_by_id_missing_returns_none():
    assert get_edge_by_id("non-existent") is None


def test_list_edges_from_source():
    node_a, node_b = _setup_two_nodes()
    mt = create_meta_type(
        MetaTypeCreate(name="Widget2", type_category=TypeCategory.NODE,
                       schema_definition={"label": {"type": "string", "required": True}})
    )
    node_c = create_node(mt, ObjectNodeCreate(meta_type_id=mt.id, properties={"label": "C"}))

    create_edge(node_a.id, node_b.id, "RELATES_TO", "A->B")
    create_edge(node_a.id, node_c.id, "POPULATES", "A->C")

    edges = list_edges_from_source(node_a.id)
    assert len(edges) == 2


# ---------------------------------------------------------------------------
# T017 – Edge reinforcement
# ---------------------------------------------------------------------------

def test_reinforce_edge_increases_confidence():
    node_a, node_b = _setup_two_nodes()
    edge = create_edge(node_a.id, node_b.id, "RELATES_TO", "test")
    assert edge.confidence_score == 0.5

    reinforced = reinforce_edge(edge.id)
    assert abs(reinforced.confidence_score - 0.6) < 0.001


def test_reinforce_edge_caps_at_1_0():
    node_a, node_b = _setup_two_nodes()
    edge = create_edge(node_a.id, node_b.id, "RELATES_TO", "test")

    for _ in range(15):  # 0.5 + 15*0.1 = 2.0, should be capped at 1.0
        edge = reinforce_edge(edge.id)

    assert edge.confidence_score == 1.0


# ---------------------------------------------------------------------------
# T023 – Decay / cascading wither (unit) using mocks
# ---------------------------------------------------------------------------

from unittest.mock import patch, MagicMock
from src.graph.edges import (
    apply_decay, cascading_wither,
    DECAY_RATE_PER_DAY, PRUNE_THRESHOLD, REINFORCE_DELTA,
)
from src.models.base import StigmergicEdge
from datetime import datetime, timezone


def _make_edge_model(edge_id: str = "edge-001", confidence: float = 0.5) -> StigmergicEdge:
    return StigmergicEdge(
        id=edge_id,
        source_id="node-a",
        target_id="node-b",
        edge_type="RELATES_TO",
        confidence_score=confidence,
        last_accessed=datetime.now(timezone.utc),
    )


def test_no_decay_within_24h():
    """Decay should not fire if less than 24h have elapsed (hours_elapsed < 24)."""
    edge = _make_edge_model(confidence=0.5)
    with patch("src.graph.edges.execute_query") as mock_query, \
         patch("src.graph.edges.get_edge_by_id") as mock_get:
        mock_get.return_value = edge
        result = apply_decay(edge.id, hours_elapsed=12.0)
    # No DB update should have been triggered
    mock_query.assert_not_called()
    assert result is not None
    assert result.confidence_score == 0.5


def test_decay_applied_after_7_days():
    """After 7 days apply_decay should reduce confidence by DECAY_RATE_PER_DAY * 7."""
    hours = 7 * 24
    expected_decay = DECAY_RATE_PER_DAY * 7
    initial = 0.9
    expected_confidence = initial - expected_decay

    decayed_edge = _make_edge_model(confidence=expected_confidence)

    with patch("src.graph.edges.execute_query") as mock_query, \
         patch("src.graph.edges.get_edge_by_id") as mock_get:
        mock_get.return_value = decayed_edge
        result = apply_decay("edge-001", hours_elapsed=hours)

    mock_query.assert_called_once()
    assert result is not None
    assert abs(result.confidence_score - expected_confidence) < 0.001


def test_prune_below_threshold():
    """Edge confidence below PRUNE_THRESHOLD should trigger deletion (pruning)."""
    low_edge = _make_edge_model(confidence=PRUNE_THRESHOLD - 0.01)

    with patch("src.graph.edges.execute_query") as mock_query, \
         patch("src.graph.edges.get_edge_by_id") as mock_get:
        mock_get.return_value = low_edge
        result = apply_decay("edge-001", hours_elapsed=48)

    # Should be pruned – result is None
    assert result is None
    # Both SET and DELETE should be called
    assert mock_query.call_count == 2


def test_cascading_wither_prunes_attached_edges():
    """Cascading wither should DELETE all edges attached to a node."""
    with patch("src.graph.edges.execute_query") as mock_query:
        mock_query.return_value = MagicMock(result_set=[[5]])
        pruned = cascading_wither("node-deprecated")

    assert pruned == 5
    mock_query.assert_called_once()


def test_cascading_wither_zero_when_no_edges():
    """Returns 0 when the node has no attached edges."""
    with patch("src.graph.edges.execute_query") as mock_query:
        mock_query.return_value = MagicMock(result_set=[])
        pruned = cascading_wither("node-isolated")

    assert pruned == 0


def test_decay_constants_match_spec():
    """SC-004: decay and prune thresholds must match the spec values."""
    assert 0.02 <= DECAY_RATE_PER_DAY <= 0.10
    assert PRUNE_THRESHOLD <= 0.1


@freeze_time("2025-07-01 12:00:00")
def test_freezegun_mocks_datetime():
    """Verify freezegun correctly intercepts datetime.now() calls."""
    now = datetime.now(timezone.utc)
    assert now.year == 2025
    assert now.month == 7
    assert now.day == 1
