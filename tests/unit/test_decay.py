"""Unit tests for stigmergic decay logic and bounded graph querying (US4).

Uses freezegun to mock time progression without real waits.
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta

import pytest
from freezegun import freeze_time

from src.models.base import MetaTypeCreate, ObjectNodeCreate, TypeCategory
from src.graph.ontology import create_meta_type
from src.graph.nodes import create_node
from src.graph.edges import (
    create_edge,
    get_edge_by_id,
    reinforce_edge,
    PRUNE_THRESHOLD,
)
from src.graph.decay import run_decay_pass
from src.graph.query import query_graph


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _setup_graph():
    """Create a MetaType and three nodes, plus one edge. Returns (mt, nodes, edge)."""
    mt = create_meta_type(
        MetaTypeCreate(
            name="Asset",
            type_category=TypeCategory.NODE,
            schema_definition={"name": {"type": "string", "required": True}},
        )
    )
    nodes = [
        create_node(mt, ObjectNodeCreate(meta_type_id=mt.id, properties={"name": f"node_{i}"}))
        for i in range(3)
    ]
    edge = create_edge(nodes[0].id, nodes[1].id, "RELATES_TO", "test edge")
    return mt, nodes, edge


# ---------------------------------------------------------------------------
# T020 – Decay tests using freezegun
# ---------------------------------------------------------------------------

def test_decay_does_not_affect_fresh_edge():
    """An edge accessed less than 24 hours ago should not decay."""
    _, nodes, edge = _setup_graph()

    now = datetime.now(timezone.utc)
    # Simulate 12 hours passing
    with freeze_time(now + timedelta(hours=12)):
        updated = run_decay_pass(edge.id)

    assert updated is not None
    assert abs(updated.confidence_score - 0.5) < 0.001


def test_decay_reduces_confidence_after_threshold():
    """After 24+ hours of no access, confidence should decrease."""
    _, nodes, edge = _setup_graph()

    now = datetime.now(timezone.utc)
    with freeze_time(now + timedelta(hours=48)):
        updated = run_decay_pass(edge.id)

    assert updated is not None
    # 2 days * 0.05/day = 0.10 decay → 0.5 - 0.10 = 0.40
    assert updated.confidence_score < 0.5


def test_decay_prunes_edge_below_threshold():
    """An edge that decays below PRUNE_THRESHOLD should be deleted."""
    _, nodes, edge = _setup_graph()

    now = datetime.now(timezone.utc)
    # Need enough days to drop from 0.5 to < 0.1
    # At 0.05/day: 0.5 - 0.05 * days < 0.1 → days > 8
    with freeze_time(now + timedelta(days=9)):
        result = run_decay_pass(edge.id)

    assert result is None  # edge was pruned
    assert get_edge_by_id(edge.id) is None


def test_reinforced_edge_decays_slower():
    """A reinforced edge (0.9) should survive longer than an unreinforced one (0.5)."""
    _, nodes, edge = _setup_graph()

    # Reinforce to 0.9
    for _ in range(4):
        edge = reinforce_edge(edge.id)
    assert edge.confidence_score == 0.9

    now = datetime.now(timezone.utc)
    # 9 days decay: 0.9 - 9*0.05 = 0.45 — still alive
    with freeze_time(now + timedelta(days=9)):
        result = run_decay_pass(edge.id)

    assert result is not None
    assert result.confidence_score > PRUNE_THRESHOLD


# ---------------------------------------------------------------------------
# T020 – Query tests
# ---------------------------------------------------------------------------

def test_query_graph_returns_nodes_by_type():
    mt, nodes, _ = _setup_graph()
    results = query_graph(meta_type_name="Asset")
    assert results["total"] >= 3


def test_query_graph_paginates_large_results():
    mt = create_meta_type(
        MetaTypeCreate(
            name="Report",
            type_category=TypeCategory.NODE,
            schema_definition={"title": {"type": "string", "required": True}},
        )
    )
    for i in range(20):
        create_node(mt, ObjectNodeCreate(meta_type_id=mt.id, properties={"title": f"Report {i}"}))

    results = query_graph(meta_type_name="Report", page=0, page_size=5)
    assert results["total"] == 20
    assert len(results["items"]) == 5
    assert results["has_more"] is True

    results_p2 = query_graph(meta_type_name="Report", page=1, page_size=5)
    assert len(results_p2["items"]) == 5


def test_query_graph_with_domain_scope_filter():
    mt = create_meta_type(
        MetaTypeCreate(
            name="FinancialItem",
            type_category=TypeCategory.NODE,
            schema_definition={"code": {"type": "string", "required": True}},
        )
    )
    create_node(mt, ObjectNodeCreate(meta_type_id=mt.id, domain_scope="Finance", properties={"code": "FIN001"}))
    create_node(mt, ObjectNodeCreate(meta_type_id=mt.id, domain_scope="Engineering", properties={"code": "ENG001"}))
    create_node(mt, ObjectNodeCreate(meta_type_id=mt.id, domain_scope="Global", properties={"code": "GLB001"}))

    finance_results = query_graph(meta_type_name="FinancialItem", domain_scope="Finance")
    # Finance scope should return Finance + Global nodes
    codes = [item.get("p", {}).get("code", item.get("properties", {}).get("code", "")) for item in finance_results["items"]]
    assert "ENG001" not in str(codes)
