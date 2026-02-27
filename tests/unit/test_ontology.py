"""Unit tests for MetaType registration and dynamic Pydantic model generation.

These tests must run against an ephemeral FalkorDB graph.
The `ephemeral_graph` fixture in conftest.py handles sandbox isolation.
"""
from __future__ import annotations

import pytest

from src.models.base import MetaTypeCreate, TypeCategory
from src.models.dynamic import get_or_create_dynamic_model
from src.graph.ontology import (
    create_meta_type,
    get_meta_type_by_name,
    get_meta_type_by_id,
    decrement_health_score,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _dashboard_create() -> MetaTypeCreate:
    return MetaTypeCreate(
        name="Dashboard",
        type_category=TypeCategory.NODE,
        schema_definition={
            "url": {"type": "string"},
            "title": {"type": "string"},
            "is_published": {"type": "boolean"},
        },
    )


# ---------------------------------------------------------------------------
# T009 – MetaType creation and retrieval
# ---------------------------------------------------------------------------

def test_create_meta_type_returns_meta_type():
    data = _dashboard_create()
    result = create_meta_type(data)
    assert result.id
    assert result.name == "Dashboard"
    assert result.type_category == TypeCategory.NODE
    assert result.health_score == 1.0
    assert result.version == 1


def test_get_meta_type_by_name_returns_created():
    data = _dashboard_create()
    created = create_meta_type(data)

    fetched = get_meta_type_by_name("Dashboard")
    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.name == "Dashboard"


def test_get_meta_type_by_id_returns_created():
    data = _dashboard_create()
    created = create_meta_type(data)

    fetched = get_meta_type_by_id(created.id)
    assert fetched is not None
    assert fetched.name == "Dashboard"


def test_get_meta_type_by_name_missing_returns_none():
    result = get_meta_type_by_name("NonExistent")
    assert result is None


def test_create_duplicate_meta_type_raises():
    data = _dashboard_create()
    create_meta_type(data)
    with pytest.raises(ValueError, match="already exists"):
        create_meta_type(data)


# ---------------------------------------------------------------------------
# T009 – Dynamic model generation
# ---------------------------------------------------------------------------

def test_dynamic_model_accepts_valid_payload():
    data = _dashboard_create()
    mt = create_meta_type(data)
    Model = get_or_create_dynamic_model(mt)

    instance = Model(url="https://example.com", title="Sales", is_published=True)
    assert instance.url == "https://example.com"


def test_dynamic_model_rejects_missing_required_field():
    data = MetaTypeCreate(
        name="Report",
        type_category=TypeCategory.NODE,
        schema_definition={
            "url": {"type": "string", "required": True},
        },
    )
    mt = create_meta_type(data)
    Model = get_or_create_dynamic_model(mt)

    with pytest.raises(Exception):
        Model()  # url is required


def test_dynamic_model_strips_extra_fields():
    data = _dashboard_create()
    mt = create_meta_type(data)
    Model = get_or_create_dynamic_model(mt)

    # Extra fields should be silently ignored (model_config forbids extras)
    instance = Model(url="https://example.com", title="x", is_published=False, unknown_field="noise")
    assert not hasattr(instance, "unknown_field")


# ---------------------------------------------------------------------------
# T009 – Health score management
# ---------------------------------------------------------------------------

def test_health_score_decrements_on_failure():
    data = _dashboard_create()
    mt = create_meta_type(data)
    assert mt.health_score == 1.0

    decrement_health_score(mt.id, delta=0.1)
    updated = get_meta_type_by_id(mt.id)
    assert updated is not None
    assert abs(updated.health_score - 0.9) < 0.001


def test_health_score_does_not_go_below_zero():
    data = _dashboard_create()
    mt = create_meta_type(data)

    for _ in range(15):
        decrement_health_score(mt.id, delta=0.1)

    updated = get_meta_type_by_id(mt.id)
    assert updated is not None
    assert updated.health_score >= 0.0
