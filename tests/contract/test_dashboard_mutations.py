"""Contract test: zero-mutation assertion for the dashboard API (SC-006, FR-001).

Instruments the FalkorDB execute_query function to capture all Cypher statements
issued during dashboard API requests. Asserts that NO CREATE, SET, MERGE, or
DELETE statements are ever issued — the dashboard is strictly read-only.

This test does NOT require a live FalkorDB instance — execute_query is monkeypatched
to track calls and return empty result sets.
"""

from __future__ import annotations

import os
import re
import time
from typing import Any
from unittest.mock import MagicMock, patch

import jwt
import pytest
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_SECRET = "contract-test-secret"
_ALGORITHM = "HS256"
_MUTATION_PATTERN = re.compile(
    r"\b(CREATE|SET|MERGE|DELETE|DETACH\s+DELETE|REMOVE)\b",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def set_jwt_secret(monkeypatch):
    monkeypatch.setenv("DASHBOARD_JWT_SECRET", _SECRET)


def _make_token(domain_scope: str = "Finance", profile_id: str = "user-001") -> str:
    now = int(time.time())
    payload = {
        "profile_id": profile_id,
        "domain_scope": domain_scope,
        "exp": now + 3600,
        "iat": now,
    }
    return jwt.encode(payload, _SECRET, algorithm=_ALGORITHM)


def _make_test_client(captured_queries: list[str]) -> TestClient:
    """Build a TestClient with execute_query monkeypatched to capture all Cypher."""
    from src.dashboard.api import create_app

    app = create_app()

    # Patch execute_query BEFORE creating client (covers route handler calls)
    mock_result = MagicMock()
    mock_result.result_set = []

    def capturing_execute_query(query: str, params: Any = None) -> Any:
        captured_queries.append(query)
        return mock_result

    # We use a context patch; the test itself applies it via the caller
    return TestClient(app, raise_server_exceptions=False), capturing_execute_query


# ---------------------------------------------------------------------------
# Zero-mutation contract tests
# ---------------------------------------------------------------------------

class TestZeroMutationContract:
    """Assert no CREATE/SET/MERGE/DELETE Cypher is issued by any dashboard route."""

    def _run_with_capture(self, monkeypatch) -> tuple[list[str], TestClient]:
        """Set up a test client that captures all Cypher queries."""
        os.environ["DASHBOARD_JWT_SECRET"] = _SECRET
        from src.dashboard.api import create_app

        app = create_app()
        captured: list[str] = []
        mock_result = MagicMock()
        mock_result.result_set = []

        def capturing_execute_query(query: str, params: Any = None) -> Any:
            captured.append(query.strip())
            return mock_result

        monkeypatch.setattr(
            "src.dashboard.graph_service.execute_query",
            capturing_execute_query,
        )
        client = TestClient(app, raise_server_exceptions=False)
        return captured, client

    def test_get_health_issues_no_mutations(self, monkeypatch):
        captured, client = self._run_with_capture(monkeypatch)
        token = _make_token()
        client.get("/health", headers={"Authorization": f"Bearer {token}"})
        _assert_no_mutations(captured)

    def test_get_api_graph_issues_no_mutations(self, monkeypatch):
        """GET /api/graph must never issue CREATE/SET/MERGE/DELETE Cypher."""
        captured, client = self._run_with_capture(monkeypatch)
        token = _make_token()
        response = client.get("/api/graph", headers={"Authorization": f"Bearer {token}"})
        # Response may be 200 or 503 (if graph returns empty) — either is fine
        assert response.status_code in (200, 503)
        _assert_no_mutations(captured)

    def test_unauthenticated_request_issues_no_mutations(self, monkeypatch):
        """Unauthenticated requests (401) must also issue no mutations."""
        captured, client = self._run_with_capture(monkeypatch)
        client.get("/api/graph")  # no auth header → 401
        _assert_no_mutations(captured)

    def test_all_routes_combined_no_mutations(self, monkeypatch):
        """Combine health + graph requests in one session — still zero mutations."""
        captured, client = self._run_with_capture(monkeypatch)
        token = _make_token()
        auth = {"Authorization": f"Bearer {token}"}

        client.get("/health")
        client.get("/health", headers=auth)
        client.get("/api/graph", headers=auth)
        client.get("/api/graph")  # unauthenticated

        _assert_no_mutations(captured)

    def test_mutation_detection_regex_works(self):
        """Sanity-check: the mutation detection regex correctly flags mutations."""
        assert _MUTATION_PATTERN.search("CREATE (n:ObjectNode {id: '1'})")
        assert _MUTATION_PATTERN.search("SET n.name = 'foo'")
        assert _MUTATION_PATTERN.search("MERGE (n:ObjectNode {id: '1'})")
        assert _MUTATION_PATTERN.search("DELETE e")
        assert _MUTATION_PATTERN.search("DETACH DELETE n")
        assert not _MUTATION_PATTERN.search("MATCH (n:ObjectNode) WHERE n.id = '1' RETURN n")


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _assert_no_mutations(queries: list[str]) -> None:
    """Raise AssertionError if any captured Cypher query is a mutation."""
    mutations_found = [q for q in queries if _MUTATION_PATTERN.search(q)]
    assert not mutations_found, (
        f"Dashboard issued {len(mutations_found)} mutation Cypher statement(s):\n"
        + "\n".join(f"  - {q}" for q in mutations_found)
    )
