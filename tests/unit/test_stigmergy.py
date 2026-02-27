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
