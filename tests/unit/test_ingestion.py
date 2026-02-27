"""Unit tests for Object Node insertion and bulk seed ingestion (US2).

These tests run against an ephemeral FalkorDB graph (see conftest.py).
"""
from __future__ import annotations

import pytest

from src.models.base import MetaTypeCreate, ObjectNodeCreate, TypeCategory
from src.graph.ontology import create_meta_type
from src.graph.nodes import (
    create_node,
    get_node_by_id,
    list_nodes_by_type,
    bulk_ingest,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _setup_dashboard_type():
    return create_meta_type(
        MetaTypeCreate(
            name="Dashboard",
            type_category=TypeCategory.NODE,
            schema_definition={
                "url": {"type": "string", "required": True},
                "title": {"type": "string"},
            },
        )
    )


# ---------------------------------------------------------------------------
# T013 – Node insertion
# ---------------------------------------------------------------------------

def test_create_node_returns_object_node():
    mt = _setup_dashboard_type()
    data = ObjectNodeCreate(
        meta_type_id=mt.id,
        domain_scope="Finance",
        properties={"url": "https://example.com/dash", "title": "Sales"},
    )
    node = create_node(mt, data)
    assert node.id
    assert node.meta_type_id == mt.id
    assert node.properties["url"] == "https://example.com/dash"


def test_create_node_rejects_invalid_properties():
    mt = _setup_dashboard_type()
    data = ObjectNodeCreate(
        meta_type_id=mt.id,
        properties={},  # url is required – should fail validation
    )
    with pytest.raises(Exception):
        create_node(mt, data)


def test_create_node_strips_extra_properties():
    mt = _setup_dashboard_type()
    data = ObjectNodeCreate(
        meta_type_id=mt.id,
        properties={"url": "https://example.com", "title": "T", "unknown_field": "noise"},
    )
    node = create_node(mt, data)
    assert "unknown_field" not in node.properties


def test_get_node_by_id_returns_created():
    mt = _setup_dashboard_type()
    data = ObjectNodeCreate(
        meta_type_id=mt.id,
        properties={"url": "https://example.com", "title": "T"},
    )
    created = create_node(mt, data)
    fetched = get_node_by_id(created.id)
    assert fetched is not None
    assert fetched.id == created.id


def test_get_node_by_id_missing_returns_none():
    result = get_node_by_id("non-existent-id")
    assert result is None


def test_list_nodes_by_type_returns_all():
    mt = _setup_dashboard_type()
    for i in range(3):
        create_node(
            mt,
            ObjectNodeCreate(
                meta_type_id=mt.id,
                properties={"url": f"https://example.com/{i}", "title": f"D{i}"},
            ),
        )
    nodes = list_nodes_by_type(mt.id)
    assert len(nodes) == 3


# ---------------------------------------------------------------------------
# T013 – Bulk ingest
# ---------------------------------------------------------------------------

def test_bulk_ingest_returns_summary_not_full_graph():
    mt = _setup_dashboard_type()
    specs = [
        {"url": f"https://example.com/{i}", "title": f"Dashboard {i}"}
        for i in range(20)
    ]
    summary = bulk_ingest(mt, specs)
    assert summary["inserted"] == 20
    assert summary["failed"] == 0
    # Response must NOT include full node data (context frugality)
    assert "items" not in summary


def test_bulk_ingest_counts_failures():
    mt = _setup_dashboard_type()
    specs = [
        {"url": "https://example.com/valid", "title": "Good"},
        {"title": "No URL – should fail"},   # missing required url
        {"url": "https://example.com/v2"},
    ]
    summary = bulk_ingest(mt, specs)
    assert summary["inserted"] == 2
    assert summary["failed"] == 1


def test_bulk_ingest_payload_under_10kb():
    """Prove that even a large bulk ingest summary stays under 10 KB."""
    mt = _setup_dashboard_type()
    specs = [{"url": f"https://example.com/{i}", "title": f"T{i}"} for i in range(500)]
    from src.models.serialization import serialise
    summary = bulk_ingest(mt, specs)
    payload = serialise(summary)
    assert len(payload.encode()) <= 10_000
