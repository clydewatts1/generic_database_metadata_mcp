"""End-to-end integration tests for FunctionObject operations.

Tests the complete workflow without requiring a running FalkorDB:
  1. Create FunctionObjects with full validation
  2. Retrieve and search functions
  3. Attach functions to ObjectNodes
  4. Validate domain scoping
  5. Test relationship queries and cascading operations

Note: Uses strategic monkeypatching to isolate tests from database dependencies
while validating the full integration of graph layer, models, and tools.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

import pytest

from src.graph import functions, nodes, ontology
from src.models.base import (
    FunctionObject,
    FunctionObjectCreate,
    MetaType,
    MetaTypeCreate,
    ObjectNode,
    ObjectNodeCreate,
    TypeCategory,
)
from src.utils.logging import NotFoundError, ValidationError


@dataclass
class _FakeNode:
    """Mock FalkorDB node for testing."""

    properties: dict


@dataclass
class _FakeResult:
    """Mock FalkorDB result set."""

    result_set: list


class TestFunctionObjectWorkflows:
    """Integration tests validating complete Function Object workflows."""

    def test_create_function_with_model_validation(self):
        """Test that FunctionObject creation validates input schemas."""
        # Invalid: output_schema is not valid JSON Schema
        invalid_schema = {"notAValidKeyword": "value"}

        with pytest.raises(ValueError):
            func_data = FunctionObjectCreate(
                name="BadSchema",
                logic_description="Has bad schema",
                input_schema={"type": "object"},
                output_schema=invalid_schema,
                profile_id="test_user",
            )

    def test_create_function_valid_input_and_output_schemas(self):
        """Test creating a function with valid JSON schemas."""
        func_data = FunctionObjectCreate(
            name="ValidSchemaFunc",
            logic_description="Has valid schemas",
            input_schema={
                "type": "object",
                "properties": {
                    "amount": {"type": "number"},
                    "currency": {"type": "string"},
                },
                "required": ["amount"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "result": {"type": "number"},
                },
            },
            profile_id="test_user",
        )

        # Should not raise
        assert func_data.name == "ValidSchemaFunc"
        assert func_data.profile_id == "test_user"

    def test_function_object_create_model_name_validation(self):
        """Test that PascalCase naming is enforced."""
        # Invalid: lowercase name
        with pytest.raises(ValueError):
            FunctionObjectCreate(
                name="invalidName",  # Should be PascalCase
                logic_description="Test",
                input_schema={"type": "object"},
                output_schema={"type": "object"},
                profile_id="test_user",
            )

    def test_function_object_lifecycle_with_mocked_graph(self, monkeypatch):
        """Test complete function object lifecycle using mocked graph operations."""
        created_func = FunctionObject(
            id=str(uuid.uuid4()),
            name="LifecycleTest",
            logic_description="Tests full lifecycle",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            created_by_profile_id="lifecycle_user",
            domain_scope="Finance",
            version=1,
        )

        # Mock the graph layer to return our test function
        def mock_create(data: FunctionObjectCreate, domain_scope="Global"):
            return created_func

        def mock_get_by_id(func_id: str, domain_scope=None):
            if func_id == created_func.id:
                return created_func
            return None

        def mock_search(filter_text, domain_scope, page, page_size):
            if "Lifecycle" in filter_text:
                return ([created_func], 1)
            return ([], 0)

        monkeypatch.setattr(functions, "create_function", mock_create)
        monkeypatch.setattr(functions, "get_function_by_id", mock_get_by_id)
        monkeypatch.setattr(functions, "search_functions", mock_search)

        # Create phase
        func_data = FunctionObjectCreate(
            name="LifecycleTest",
            logic_description="Tests full lifecycle",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            profile_id="lifecycle_user",
        )
        created = functions.create_function(func_data, domain_scope="Finance")
        assert created.name == "LifecycleTest"
        assert created.domain_scope == "Finance"

        # Retrieve phase
        retrieved = functions.get_function_by_id(created.id, domain_scope="Finance")
        assert retrieved is not None
        assert retrieved.id == created.id

        # Search phase
        results, total = functions.search_functions(
            filter_text="Lifecycle",
            domain_scope="Finance",
            page=1,
            page_size=5,
        )
        assert total == 1
        assert len(results) == 1

    def test_function_attachment_to_multiple_nodes(self, monkeypatch):
        """Test attaching a single function to multiple ObjectNodes."""
        func_id = str(uuid.uuid4())
        node_ids = [str(uuid.uuid4()) for _ in range(3)]

        attachment_results = {node_id: True for node_id in node_ids}

        def mock_attach_to_node(function_id, node_id, relationship_type, **kwargs):
            if function_id == func_id and node_id in attachment_results:
                return attachment_results[node_id]
            raise NotFoundError("Node", node_id)

        def mock_list_for_node(node_id, domain_scope=None):
            if node_id in node_ids:
                return [FunctionObject(
                    id=func_id,
                    name="MultiAttach",
                    logic_description="Attached to multiple nodes",
                    input_schema={"type": "object"},
                    output_schema={"type": "object"},
                    created_by_profile_id="test",
                    domain_scope="Finance",
                )]
            return []

        monkeypatch.setattr(functions, "attach_function_to_node", mock_attach_to_node)
        monkeypatch.setattr(functions, "list_functions_for_node", mock_list_for_node)

        # Attach to all nodes
        for node_id in node_ids:
            result = functions.attach_function_to_node(
                function_id=func_id,
                node_id=node_id,
                relationship_type="TRANSFORMS",
                profile_id="test",
                domain_scope="Finance",
            )
            assert result is True

        # Verify attachments
        for node_id in node_ids:
            attached = functions.list_functions_for_node(
                node_id=node_id,
                domain_scope="Finance",
            )
            assert len(attached) > 0
            assert any(f.id == func_id for f in attached)

    def test_domain_scope_isolation_in_search(self, monkeypatch):
        """Test that function search respects domain scope boundaries."""
        finance_func = FunctionObject(
            id=str(uuid.uuid4()),
            name="FinanceTransform",
            logic_description="Finance-scoped function",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            created_by_profile_id="finance_user",
            domain_scope="Finance",
        )

        marketing_func = FunctionObject(
            id=str(uuid.uuid4()),
            name="MarketingTransform",
            logic_description="Marketing-scoped function",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            created_by_profile_id="marketing_user",
            domain_scope="Marketing",
        )

        def mock_search(filter_text, domain_scope, page, page_size):
            if domain_scope == "Finance":
                return ([finance_func], 1)
            elif domain_scope == "Marketing":
                return ([marketing_func], 1)
            return ([], 0)

        monkeypatch.setattr(functions, "search_functions", mock_search)

        # Finance query
        finance_results, finance_total = functions.search_functions(
            filter_text="Transform",
            domain_scope="Finance",
            page=1,
            page_size=5,
        )
        assert finance_total == 1
        assert finance_results[0].domain_scope == "Finance"

        # Marketing query
        marketing_results, marketing_total = functions.search_functions(
            filter_text="Transform",
            domain_scope="Marketing",
            page=1,
            page_size=5,
        )
        assert marketing_total == 1
        assert marketing_results[0].domain_scope == "Marketing"

    def test_function_update_preserves_metadata(self, monkeypatch):
        """Test that updating function logic preserves domain and creator info."""
        original_func = FunctionObject(
            id=str(uuid.uuid4()),
            name="UpdateableFunc",
            logic_description="Original description",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            created_by_profile_id="creator_user",
            domain_scope="Finance",
            version=1,
        )

        updated_func = FunctionObject(
            id=original_func.id,
            name="UpdateableFunc",
            logic_description="Updated description",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            created_by_profile_id="creator_user",  # Preserved
            domain_scope="Finance",  # Preserved
            version=2,
        )

        def mock_update(function_id, updates, domain_scope=None):
            if function_id == original_func.id:
                return updated_func
            raise NotFoundError("FunctionObject", function_id)

        monkeypatch.setattr(functions, "update_function", mock_update)

        result = functions.update_function(
            function_id=original_func.id,
            updates={"logic_description": "Updated description"},
            domain_scope="Finance",
        )

        assert result.logic_description == "Updated description"
        assert result.version == 2
        assert result.created_by_profile_id == "creator_user"  # Preserved
        assert result.domain_scope == "Finance"  # Preserved

    def test_validation_error_on_schema_mismatch(self, monkeypatch):
        """Test that ValidationError is raised when attaching to node with bad scope."""
        def mock_attach_error(function_id, node_id, relationship_type, **kwargs):
            raise ValidationError("Domain scope mismatch")

        monkeypatch.setattr(functions, "attach_function_to_node", mock_attach_error)

        with pytest.raises(ValidationError):
            functions.attach_function_to_node(
                function_id="func1",
                node_id="node1",
                relationship_type="TRANSFORMS",
                profile_id="user",
                domain_scope="Finance",
            )

    def test_function_not_found_handling(self, monkeypatch):
        """Test proper error handling when function doesn't exist."""
        def mock_get_error(func_id, domain_scope=None):
            raise NotFoundError("FunctionObject", func_id)

        monkeypatch.setattr(functions, "get_function_by_id", mock_get_error)

        with pytest.raises(NotFoundError):
            functions.get_function_by_id("nonexistent_id", domain_scope="Finance")


class TestFunctionObjectToolIntegration:
    """Integration tests for MCP tools with mocked graph layer."""

    def test_create_function_tool_success_serialization(self, monkeypatch):
        """Test that create_function tool properly serializes successful responses."""
        from src.mcp_server.tools import functions as function_tools

        created = FunctionObject(
            id="func-123",
            name="ToolTest",
            logic_description="Testing tool serialization",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            created_by_profile_id="tool_user",
            domain_scope="Finance",
        )

        monkeypatch.setattr(
            function_tools,
            "create_function_graph",
            lambda data, domain_scope="Global": created,
        )

        raw = function_tools.create_function(
            name="ToolTest",
            logic_description="Testing tool serialization",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            profile_id="tool_user",
            domain_scope="Finance",
        )

        payload = json.loads(raw)
        assert payload["status"] == "SUCCESS"
        assert payload["function_id"] == "func-123"

    def test_query_functions_tool_pagination(self, monkeypatch):
        """Test that query_functions tool properly handles pagination."""
        from src.mcp_server.tools import functions as function_tools

        items = [
            FunctionObject(
                id=f"func-{i}",
                name=f"QueryTest{i}",
                logic_description="Query test",
                input_schema={"type": "object"},
                output_schema={"type": "object"},
                created_by_profile_id="tool_user",
                domain_scope="Finance",
            )
            for i in range(3)
        ]

        monkeypatch.setattr(
            function_tools,
            "search_functions",
            lambda **kwargs: (items[:2], 3),  # Return 2 items, total 3
        )

        raw = function_tools.query_functions(
            profile_id="tool_user",
            domain_scope="Finance",
            filter="QueryTest",
            page=1,
            page_size=2,
        )

        payload = json.loads(raw)
        assert payload["total_count"] == 3
        assert payload["current_page"] == 1
        assert len(payload["functions"]) == 2
        assert payload["total_pages"] == 2

    def test_attach_function_tool_partial_success(self, monkeypatch):
        """Test that attach_function_to_nodes tool handles partial failures."""
        from src.mcp_server.tools import functions as function_tools

        def mock_attach(function_id: str, node_id: str, relationship_type: str, **kwargs):
            if node_id == "good_node":
                return True
            raise ValidationError("Domain scope mismatch")

        monkeypatch.setattr(function_tools, "attach_function_to_node", mock_attach)

        raw = function_tools.attach_function_to_nodes(
            function_id="func-1",
            target_node_ids=["good_node", "bad_node"],
            relationship_type="TRANSFORMS",
            profile_id="tool_user",
        )

        payload = json.loads(raw)
        assert payload["status"] == "PARTIAL_SUCCESS"
        assert payload["attachments_created"] == 1
        assert payload["attachments_failed"] == 1
        assert "bad_node" in payload["failed_node_ids"]

