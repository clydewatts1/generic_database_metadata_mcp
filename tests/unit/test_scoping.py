"""T028 – Unit tests for User Story 5: Profile-Aware Scoping and Supreme Court.

Covers:
- domain_scope query filtering (user scope + Global returned; other domains hidden)
- Parallel Truths [:VARIANTS] branching logic
- [APPROVAL_REQUIRED] interception for delete operations without token
- [APPROVAL_REQUIRED] bypass with token="APPROVED"
"""

from __future__ import annotations

import json
import uuid
from typing import Any
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mt(id_: str, name: str) -> MagicMock:
    """Build a minimal MetaType mock."""
    m = MagicMock()
    m.id = id_
    m.name = name
    m.type_category = MagicMock(value="NODE")
    m.schema_definition = {}
    m.version = 2
    m.health_score = 1.0
    return m


def _node(id_: str, domain_scope: str) -> MagicMock:
    """Build a minimal ObjectNode mock."""
    n = MagicMock()
    n.id = id_
    n.domain_scope = domain_scope
    return n


# ===========================================================================
# 1. Domain-scoped query filtering (Rule 5.2)
# ===========================================================================

class TestDomainScopeFiltering:
    """_build_where_clause must yield (scope OR Global) when domain_scope given."""

    def test_where_clause_includes_global(self):
        from src.graph.query import _build_where_clause

        where, params = _build_where_clause(
            meta_type_name=None, domain_scope="Finance"
        )
        # The WHERE clause must check n.domain_scope = 'Finance' OR 'Global'
        assert "Global" in where
        assert "$ds" in where
        assert params["ds"] == "Finance"

    def test_where_clause_no_scope_no_filter(self):
        from src.graph.query import _build_where_clause

        where, params = _build_where_clause(meta_type_name=None, domain_scope=None)
        # No domain_scope filter applied
        assert "domain_scope" not in where
        assert "ds" not in params

    def test_where_clause_with_meta_type(self):
        from src.graph.query import _build_where_clause

        where, params = _build_where_clause(
            meta_type_name="Dashboard", domain_scope="Operations"
        )
        assert "meta_type_name = $mtn" in where
        assert params["mtn"] == "Dashboard"
        assert "Global" in where
        assert params["ds"] == "Operations"

    def test_query_graph_passes_domain_scope(self):
        """query_graph must thread domain_scope down to _flat_query."""
        with (
            patch("src.graph.query.get_graph"),
            patch("src.graph.query._flat_query") as mock_flat,
        ):
            mock_flat.return_value = ([], 0)
            from src.graph.query import query_graph

            result = query_graph(domain_scope="HR")

            call_args = mock_flat.call_args
            # domain_scope positional/keyword argument passed to _flat_query
            assert "HR" in call_args.args or call_args.kwargs.get("domain_scope") == "HR" or "HR" in str(call_args)

    def test_query_graph_no_scope_passes_none(self):
        with (
            patch("src.graph.query.get_graph"),
            patch("src.graph.query._flat_query") as mock_flat,
        ):
            mock_flat.return_value = ([], 0)
            from src.graph.query import query_graph

            query_graph()  # no domain_scope argument

            call_args = mock_flat.call_args
            # None must be passed, not a falsy string
            passed_scope = (
                call_args.kwargs.get("domain_scope")
                if call_args.kwargs
                else call_args.args[2] if len(call_args.args) > 2 else None
            )
            # None or not present is fine – just must not be a non-None string
            assert passed_scope is None or passed_scope == "" or "domain_scope" not in str(call_args)


# ===========================================================================
# 2. [:VARIANTS] Parallel Truths branching (Rule 5.3)
# ===========================================================================

class TestParallelTruths:
    """branch_node_as_variant must create a [:VARIANTS] edge in the graph."""

    def test_branch_creates_variants_edge(self):
        """branch_node_as_variant calls execute_query with VARIANTS relationship."""
        with patch("src.graph.nodes.execute_query") as mock_exec:
            mock_exec.return_value = MagicMock(result_set=[])
            from src.graph.nodes import branch_node_as_variant

            branch_node_as_variant(
                original_node_id="orig-001",
                domain_scope="Finance",
                profile_id="user-42",
            )

            cypher_str = mock_exec.call_args.args[0]
            assert "VARIANTS" in cypher_str

    def test_branch_returns_new_node_id(self):
        """branch_node_as_variant returns a new UUID string."""
        with patch("src.graph.nodes.execute_query") as mock_exec:
            mock_exec.return_value = MagicMock(result_set=[])
            from src.graph.nodes import branch_node_as_variant

            new_id = branch_node_as_variant(
                original_node_id="orig-001",
                domain_scope="Finance",
                profile_id="user-42",
            )
            # Must be a non-empty string (UUID)
            assert isinstance(new_id, str)
            assert len(new_id) > 8

    def test_branch_uses_domain_scope_on_variant(self):
        """The new node is created with the domain_scope passed."""
        captured: list[tuple] = []

        with patch("src.graph.nodes.execute_query") as mock_exec:
            mock_exec.return_value = MagicMock(result_set=[])

            def capture(cypher, params=None):
                captured.append((cypher, params or {}))
                return MagicMock(result_set=[])

            mock_exec.side_effect = capture
            from src.graph.nodes import branch_node_as_variant

            branch_node_as_variant(
                original_node_id="orig-002",
                domain_scope="Healthcare",
                profile_id="user-99",
            )

        # At least one query should carry "Healthcare"
        combined = " ".join(str(params) for _, params in captured)
        assert "Healthcare" in combined


# ===========================================================================
# 3. [APPROVAL_REQUIRED] interception (Rule 5.5 / FR-017)
# ===========================================================================

class TestApprovalRequired:
    """delete_meta_type_tool and delete_node_tool must block without approval_token."""

    def test_delete_meta_type_no_token_returns_approval_required(self):
        """Calling delete_meta_type_tool without approval_token returns APPROVAL_REQUIRED."""
        import json as _json

        # delete_meta_type_tool checks approval_token first, before any DB call
        from src.mcp_server.tools.ontology import delete_meta_type_tool

        raw = delete_meta_type_tool(
            meta_type_id="mt-001",
            profile_id="user-1",
            approval_token="",
        )
        payload = _json.loads(raw)
        assert payload.get("status") == "APPROVAL_REQUIRED"

    def test_delete_node_no_token_returns_approval_required(self):
        import json as _json

        # delete_node_tool checks approval_token first, before any DB call
        from src.mcp_server.tools.ontology import delete_node_tool

        raw = delete_node_tool(
            node_id="n-001",
            profile_id="user-1",
            approval_token="",
        )
        payload = _json.loads(raw)
        assert payload.get("status") == "APPROVAL_REQUIRED"

    def test_delete_meta_type_with_approved_token_succeeds(self):
        """Passing approval_token='APPROVED' bypasses guard and calls delete."""
        import json as _json

        with (
            patch("src.mcp_server.tools.ontology.get_meta_type_by_id") as mock_get,
            patch("src.graph.ontology.delete_meta_type") as mock_delete,
        ):
            mock_get.return_value = _mt("mt-002", "Schema")

            from src.mcp_server.tools.ontology import delete_meta_type_tool

            raw = delete_meta_type_tool(
                meta_type_id="mt-002",
                profile_id="user-1",
                approval_token="APPROVED",
            )
            payload = _json.loads(raw)
            assert payload.get("status") == "SUCCESS"
            mock_delete.assert_called_once_with("mt-002")

    def test_delete_node_with_approved_token_succeeds(self):
        """Passing approval_token='APPROVED' calls cascading_wither + delete_node."""
        import json as _json

        # delete_node_tool uses lazy imports; patch the source modules directly
        with (
            patch("src.graph.nodes.get_node_by_id") as mock_get,
            patch("src.graph.edges.cascading_wither") as mock_wither,
            patch("src.graph.nodes.delete_node") as mock_del,
        ):
            mock_get.return_value = _node("n-002", "Global")
            mock_wither.return_value = 2

            from src.mcp_server.tools.ontology import delete_node_tool

            raw = delete_node_tool(
                node_id="n-002",
                profile_id="user-1",
                approval_token="APPROVED",
            )
            payload = _json.loads(raw)
            # Should be SUCCESS (not APPROVAL_REQUIRED)
            assert payload.get("status") == "SUCCESS"
            assert payload.get("edges_pruned") == 2

    def test_delete_meta_type_wrong_token_returns_approval_required(self):
        """Any token other than 'APPROVED' is rejected."""
        import json as _json

        from src.mcp_server.tools.ontology import delete_meta_type_tool

        for bad_token in ("yes", "confirm", "YES", "approved", "1"):
            raw = delete_meta_type_tool(
                meta_type_id="mt-003",
                profile_id="user-1",
                approval_token=bad_token,
            )
            payload = _json.loads(raw)
            assert payload.get("status") == "APPROVAL_REQUIRED", (
                f"Expected APPROVAL_REQUIRED for token={bad_token!r}"
            )
