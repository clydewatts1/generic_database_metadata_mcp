"""Unit tests for FunctionObject graph operations with mocked query execution."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from src.graph import functions
from src.models.base import FunctionObjectCreate


@dataclass
class _FakeNode:
    properties: dict


@dataclass
class _FakeResult:
    result_set: list


def test_create_function_success(monkeypatch):
    calls: list[tuple[str, dict]] = []

    def fake_execute_query(query: str, params: dict | None = None):
        params = params or {}
        calls.append((query, params))
        if "MATCH (f:FunctionObject {name:" in query:
            return _FakeResult([])
        return _FakeResult([])

    monkeypatch.setattr(functions, "execute_query", fake_execute_query)

    created = functions.create_function(
        FunctionObjectCreate(
            name="TransformSalary",
            logic_description="Converts salary to USD",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            profile_id="u1",
        ),
        domain_scope="Finance",
    )

    assert created.name == "TransformSalary"
    assert created.created_by_profile_id == "u1"
    assert created.domain_scope == "Finance"
    assert len(calls) == 2


def test_create_function_duplicate_name(monkeypatch):
    existing = _FakeNode(
        {
            "id": "f-1",
            "name": "TransformSalary",
            "logic_description": "x",
            "input_schema": "{}",
            "output_schema": "{}",
            "created_by_profile_id": "u1",
            "domain_scope": "Finance",
            "created_at": "2026-02-28T00:00:00+00:00",
            "version": "1",
        }
    )

    def fake_execute_query(query: str, params: dict | None = None):
        if "MATCH (f:FunctionObject {name:" in query:
            return _FakeResult([[existing]])
        return _FakeResult([])

    monkeypatch.setattr(functions, "execute_query", fake_execute_query)

    with pytest.raises(ValueError):
        functions.create_function(
            FunctionObjectCreate(
                name="TransformSalary",
                logic_description="Converts salary to USD",
                input_schema={"type": "object"},
                output_schema={"type": "object"},
            )
        )


def test_list_functions_returns_items_and_count(monkeypatch):
    node = _FakeNode(
        {
            "id": "f-1",
            "name": "TransformSalary",
            "logic_description": "Converts salary to USD",
            "input_schema": "{}",
            "output_schema": "{}",
            "created_by_profile_id": "u1",
            "domain_scope": "Finance",
            "created_at": "2026-02-28T00:00:00+00:00",
            "version": "1",
        }
    )

    def fake_execute_query(query: str, params: dict | None = None):
        if "RETURN count(f)" in query:
            return _FakeResult([[1]])
        if "RETURN f ORDER BY f.name" in query:
            return _FakeResult([[node]])
        return _FakeResult([])

    monkeypatch.setattr(functions, "execute_query", fake_execute_query)

    items, total = functions.list_functions(domain_scope="Finance", page=1, page_size=5)
    assert total == 1
    assert len(items) == 1
    assert items[0].name == "TransformSalary"


def test_search_functions_blank_filter_falls_back_to_list(monkeypatch):
    called = {"list": False}

    def fake_list(*args, **kwargs):
        called["list"] = True
        return ([], 0)

    monkeypatch.setattr(functions, "list_functions", fake_list)

    items, total = functions.search_functions("  ", domain_scope="Global")
    assert called["list"] is True
    assert items == []
    assert total == 0


def test_attach_function_to_node_rejects_invalid_rel_type():
    with pytest.raises(Exception):
        functions.attach_function_to_node("f1", "n1", "INVALID")


def test_attach_function_to_node_scope_mismatch(monkeypatch):
    monkeypatch.setattr(functions, "_get_function_domain_scope", lambda _id: "Finance")
    monkeypatch.setattr(functions, "_get_object_node_domain_scope", lambda _id: "Global")

    with pytest.raises(Exception):
        functions.attach_function_to_node("f1", "n1", "TRANSFORMS")


def test_detach_function_from_node_success(monkeypatch):
    def fake_execute_query(query: str, params: dict | None = None):
        return _FakeResult([[1]])

    monkeypatch.setattr(functions, "execute_query", fake_execute_query)

    assert functions.detach_function_from_node("f1", "n1", "TRANSFORMS") is True
