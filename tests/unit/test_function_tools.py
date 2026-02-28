"""Unit tests for FunctionObject MCP tools with monkeypatched graph layer."""

from __future__ import annotations

import json

from src.mcp_server.tools import functions as function_tools
from src.models.base import FunctionObject
from src.utils.logging import NotFoundError, ValidationError


def test_create_function_success(monkeypatch):
    created = FunctionObject(
        id="func-1",
        name="TransformSalary",
        logic_description="Converts salary",
        input_schema={"type": "object"},
        output_schema={"type": "object"},
        created_by_profile_id="u1",
        domain_scope="Finance",
    )

    monkeypatch.setattr(function_tools, "create_function_graph", lambda data, domain_scope="Global": created)

    raw = function_tools.create_function(
        name="TransformSalary",
        logic_description="Converts salary",
        input_schema={"type": "object"},
        output_schema={"type": "object"},
        profile_id="u1",
        domain_scope="Finance",
    )
    payload = json.loads(raw)

    assert payload["status"] == "SUCCESS"
    assert payload["function_id"] == "func-1"


def test_create_function_validation_error(monkeypatch):
    def raise_error(data, domain_scope="Global"):
        raise ValueError("FunctionObject already exists")

    monkeypatch.setattr(function_tools, "create_function_graph", raise_error)

    raw = function_tools.create_function(
        name="TransformSalary",
        logic_description="Converts salary",
        input_schema={"type": "object"},
        output_schema={"type": "object"},
        profile_id="u1",
    )
    payload = json.loads(raw)

    assert payload["status"] == "VALIDATION_ERROR"
    assert payload["error"] == "VALIDATION_ERROR"


def test_query_functions_success(monkeypatch):
    items = [
        FunctionObject(
            id="func-1",
            name="TransformSalary",
            logic_description="Converts salary",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            created_by_profile_id="u1",
            domain_scope="Finance",
            version=2,
        )
    ]

    monkeypatch.setattr(function_tools, "search_functions", lambda **kwargs: (items, 1))

    raw = function_tools.query_functions(
        profile_id="u1",
        domain_scope="Finance",
        filter="salary",
        page=1,
        page_size=5,
    )
    payload = json.loads(raw)

    assert payload["total_count"] == 1
    assert payload["current_page"] == 1
    assert payload["total_pages"] == 1
    assert isinstance(payload["functions"], list)


def test_attach_function_to_nodes_partial_success(monkeypatch):
    outcomes = {
        "n1": True,
        "n2": ValidationError("bad scope"),
        "n3": NotFoundError("ObjectNode", "n3"),
    }

    def fake_attach(function_id: str, node_id: str, relationship_type: str):
        outcome = outcomes[node_id]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    monkeypatch.setattr(function_tools, "attach_function_to_node", fake_attach)

    raw = function_tools.attach_function_to_nodes(
        function_id="func-1",
        target_node_ids=["n1", "n2", "n3"],
        relationship_type="TRANSFORMS",
        profile_id="u1",
    )
    payload = json.loads(raw)

    assert payload["status"] == "PARTIAL_SUCCESS"
    assert payload["attachments_created"] == 1
    assert payload["attachments_failed"] == 2
    assert set(payload["failed_node_ids"]) == {"n2", "n3"}


def test_attach_function_to_nodes_validation_error_when_all_fail(monkeypatch):
    def always_fail(function_id: str, node_id: str, relationship_type: str):
        raise ValidationError("bad relationship")

    monkeypatch.setattr(function_tools, "attach_function_to_node", always_fail)

    raw = function_tools.attach_function_to_nodes(
        function_id="func-1",
        target_node_ids=["n1", "n2"],
        relationship_type="INVALID",
        profile_id="u1",
    )
    payload = json.loads(raw)

    assert payload["status"] == "VALIDATION_ERROR"
    assert payload["attachments_created"] == 0
    assert payload["attachments_failed"] == 2
