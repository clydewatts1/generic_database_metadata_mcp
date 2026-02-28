"""Integration tests for the dashboard API endpoints.

Tests T014, T019, T020, T024, T028 (appended progressively from Phases 3-6).

These tests use FastAPI TestClient with:
- DASHBOARD_JWT_SECRET injected via monkeypatch
- DashboardGraphService._fetch_nodes / _fetch_stigmergic_edges mocked to avoid
  requiring a live FalkorDB instance

Test coverage:
  Phase 3 / T014: Scope isolation — Finance JWT → Finance+Global nodes only
  Phase 3 / T014: Marketing JWT → Marketing+Global nodes only
  Phase 3 / T014: Unauthenticated → 401
  Phase 3 / T014: Missing JWT claims → 403
  Phase 4 / T019: GET /api/graph response shape + Content-Type + no TOON sentinels
  Phase 4 / T019: GET /health returns {"status": "ok"}
  Phase 4 / T020: business_name in response reflects node properties
  Phase 5 / T024: is_stigmergic / confidence_score on edges
  Phase 6 / T028: meta_types present and deduplicated
"""

from __future__ import annotations

import json
import time
from typing import Any
from unittest.mock import patch

import jwt
import pytest
from fastapi.testclient import TestClient

_SECRET = "integration-test-secret"
_ALGORITHM = "HS256"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def set_jwt_secret(monkeypatch):
    monkeypatch.setenv("DASHBOARD_JWT_SECRET", _SECRET)


@pytest.fixture()
def client(monkeypatch) -> TestClient:
    """TestClient backed by the real dashboard app with env var set."""
    from src.dashboard.api import create_app
    app = create_app()
    return TestClient(app, raise_server_exceptions=False)


def _token(
    domain_scope: str = "Finance",
    profile_id: str = "user-001",
    include_scope: bool = True,
    include_profile: bool = True,
) -> str:
    now = int(time.time())
    payload: dict[str, Any] = {"exp": now + 3600, "iat": now}
    if include_profile:
        payload["profile_id"] = profile_id
    if include_scope:
        payload["domain_scope"] = domain_scope
    return jwt.encode(payload, _SECRET, algorithm=_ALGORITHM)


def _make_raw_node(
    node_id: str,
    meta_type_name: str = "Table",
    domain_scope: str = "Finance",
    label: str = "tbl",
    business_name: str | None = None,
) -> dict[str, Any]:
    inner: dict[str, Any] = {"label": label}
    if business_name:
        inner["business_name"] = business_name
    return {
        "id": node_id,
        "_id": node_id,
        "meta_type_name": meta_type_name,
        "domain_scope": domain_scope,
        "properties": json.dumps(inner),
    }


# ---------------------------------------------------------------------------
# T014: Scope isolation
# ---------------------------------------------------------------------------

class TestScopeIsolation:
    def test_finance_jwt_returns_finance_and_global_nodes(self, monkeypatch):
        finance_nodes = [
            _make_raw_node("f1", domain_scope="Finance"),
            _make_raw_node("g1", domain_scope="Global", meta_type_name="Schema"),
        ]
        monkeypatch.setattr(
            "src.dashboard.graph_service.DashboardGraphService._fetch_nodes",
            lambda self, scope: finance_nodes if scope == "Finance" else [],
        )
        monkeypatch.setattr(
            "src.dashboard.graph_service.DashboardGraphService._fetch_stigmergic_edges",
            lambda self, ids: [],
        )
        monkeypatch.setattr(
            "src.dashboard.graph_service.DashboardGraphService._fetch_structural_edges",
            lambda self, ids: [],
        )

        from src.dashboard.api import create_app
        app = create_app()
        client = TestClient(app, raise_server_exceptions=False)

        response = client.get(
            "/api/graph",
            headers={"Authorization": f"Bearer {_token(domain_scope='Finance')}"},
        )
        assert response.status_code == 200
        data = response.json()
        # All nodes should be Finance or Global scope
        for node in data["nodes"]:
            assert node["domain_scope"] in ("Finance", "Global"), (
                f"Unexpected scope in Finance response: {node['domain_scope']}"
            )

    def test_marketing_jwt_gets_marketing_scope_passed(self, monkeypatch):
        captured_scopes: list[str] = []

        def fake_fetch_nodes(self, scope: str):
            captured_scopes.append(scope)
            return []

        monkeypatch.setattr(
            "src.dashboard.graph_service.DashboardGraphService._fetch_nodes",
            fake_fetch_nodes,
        )
        monkeypatch.setattr(
            "src.dashboard.graph_service.DashboardGraphService._fetch_stigmergic_edges",
            lambda self, ids: [],
        )
        monkeypatch.setattr(
            "src.dashboard.graph_service.DashboardGraphService._fetch_structural_edges",
            lambda self, ids: [],
        )

        from src.dashboard.api import create_app
        app = create_app()
        TestClient(app, raise_server_exceptions=False).get(
            "/api/graph",
            headers={"Authorization": f"Bearer {_token(domain_scope='Marketing')}"},
        )
        assert "Marketing" in captured_scopes

    def test_unauthenticated_returns_401(self, client: TestClient):
        response = client.get("/api/graph")
        assert response.status_code == 401

    def test_missing_profile_id_returns_403(self, client: TestClient):
        token = _token(include_profile=False)
        response = client.get("/api/graph", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 403

    def test_missing_domain_scope_returns_403(self, client: TestClient):
        token = _token(include_scope=False)
        response = client.get("/api/graph", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# T019: GET /api/graph response shape + Content-Type + no TOON sentinels
# ---------------------------------------------------------------------------

class TestResponseShape:
    @pytest.fixture()
    def scoped_client(self, monkeypatch) -> TestClient:
        """Client whose graph returns a representative node + edge."""
        nodes = [
            _make_raw_node("n1", meta_type_name="Table", business_name="Revenue Table"),
            _make_raw_node("n2", meta_type_name="Dashboard"),
        ]
        stigmergic = [
            {
                "source_id": "n1",
                "target_id": "n2",
                "edge_type": "RELATES_TO",
                "confidence_score": 0.7,
                "rationale_summary": "test",
                "last_accessed": "2026-01-01T00:00:00+00:00",
            }
        ]
        monkeypatch.setattr(
            "src.dashboard.graph_service.DashboardGraphService._fetch_nodes",
            lambda self, scope: nodes,
        )
        monkeypatch.setattr(
            "src.dashboard.graph_service.DashboardGraphService._fetch_stigmergic_edges",
            lambda self, ids: stigmergic,
        )
        monkeypatch.setattr(
            "src.dashboard.graph_service.DashboardGraphService._fetch_structural_edges",
            lambda self, ids: [],
        )
        from src.dashboard.api import create_app
        app = create_app()
        return TestClient(app, raise_server_exceptions=False)

    def test_content_type_is_json(self, scoped_client: TestClient):
        response = scoped_client.get(
            "/api/graph",
            headers={"Authorization": f"Bearer {_token()}"},
        )
        assert response.status_code == 200
        assert "application/json" in response.headers.get("content-type", "")

    def test_response_has_required_fields(self, scoped_client: TestClient):
        response = scoped_client.get(
            "/api/graph",
            headers={"Authorization": f"Bearer {_token()}"},
        )
        data = response.json()
        assert "nodes" in data
        assert "edges" in data
        assert "meta_types" in data
        assert "node_count" in data
        assert "truncated" in data
        assert "scope" in data

    def test_node_count_equals_len_nodes(self, scoped_client: TestClient):
        response = scoped_client.get(
            "/api/graph",
            headers={"Authorization": f"Bearer {_token()}"},
        )
        data = response.json()
        assert data["node_count"] == len(data["nodes"])

    def test_all_nodes_have_required_fields(self, scoped_client: TestClient):
        response = scoped_client.get(
            "/api/graph",
            headers={"Authorization": f"Bearer {_token()}"},
        )
        for node in response.json()["nodes"]:
            assert "id" in node
            assert "label" in node
            assert "meta_type_name" in node
            assert "domain_scope" in node

    def test_no_toon_sentinel_keys_in_response(self, scoped_client: TestClient):
        """FR-010: response must not contain TOON compact-format sentinel keys."""
        response = scoped_client.get(
            "/api/graph",
            headers={"Authorization": f"Bearer {_token()}"},
        )
        raw = response.text
        # TOON sentinel keys are top-level abbreviated keys
        toon_sentinels = ['"_t"', '"_k"', '"_v"']
        for sentinel in toon_sentinels:
            assert sentinel not in raw, f"TOON sentinel key {sentinel} found in response"

    def test_health_returns_ok(self, scoped_client: TestClient, monkeypatch):
        """GET /health returns 200 when FalkorDB is reachable (mocked)."""
        # Mock the health probe so it doesn't try to connect to FalkorDB
        monkeypatch.setattr(
            "src.graph.client.execute_query",
            lambda cypher, params: type("R", (), {"result_set": [[1]]})(),
        )
        response = scoped_client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_health_returns_degraded_when_falkordb_unreachable(self, monkeypatch):
        """GET /health returns 503 when FalkorDB connection fails (T033)."""
        monkeypatch.setenv("DASHBOARD_JWT_SECRET", _SECRET)
        # Do NOT mock execute_query — let it fail naturally (no FalkorDB running)
        from src.dashboard.api import create_app
        app = create_app()
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/health")
        # Either 200 (if FalkorDB happens to be running) or 503 (degraded)
        assert response.status_code in (200, 503)
        data = response.json()
        assert data["status"] in ("ok", "degraded")


# ---------------------------------------------------------------------------
# T020: business_name in response
# ---------------------------------------------------------------------------

class TestBusinessNameInResponse:
    def test_node_with_business_name_carries_it(self, monkeypatch):
        nodes = [_make_raw_node("n1", business_name="Revenue Table")]
        monkeypatch.setattr(
            "src.dashboard.graph_service.DashboardGraphService._fetch_nodes",
            lambda self, scope: nodes,
        )
        monkeypatch.setattr(
            "src.dashboard.graph_service.DashboardGraphService._fetch_stigmergic_edges",
            lambda self, ids: [],
        )
        monkeypatch.setattr(
            "src.dashboard.graph_service.DashboardGraphService._fetch_structural_edges",
            lambda self, ids: [],
        )
        from src.dashboard.api import create_app
        app = create_app()
        response = TestClient(app, raise_server_exceptions=False).get(
            "/api/graph",
            headers={"Authorization": f"Bearer {_token()}"},
        )
        assert response.status_code == 200
        nodes_resp = response.json()["nodes"]
        assert nodes_resp[0]["business_name"] == "Revenue Table"

    def test_node_without_business_name_is_null(self, monkeypatch):
        nodes = [_make_raw_node("n1", business_name=None)]
        monkeypatch.setattr(
            "src.dashboard.graph_service.DashboardGraphService._fetch_nodes",
            lambda self, scope: nodes,
        )
        monkeypatch.setattr(
            "src.dashboard.graph_service.DashboardGraphService._fetch_stigmergic_edges",
            lambda self, ids: [],
        )
        monkeypatch.setattr(
            "src.dashboard.graph_service.DashboardGraphService._fetch_structural_edges",
            lambda self, ids: [],
        )
        from src.dashboard.api import create_app
        app = create_app()
        response = TestClient(app, raise_server_exceptions=False).get(
            "/api/graph",
            headers={"Authorization": f"Bearer {_token()}"},
        )
        assert response.status_code == 200
        assert response.json()["nodes"][0]["business_name"] is None

    def test_label_always_non_empty(self, monkeypatch):
        nodes = [_make_raw_node("n1", label="tech_table")]
        monkeypatch.setattr(
            "src.dashboard.graph_service.DashboardGraphService._fetch_nodes",
            lambda self, scope: nodes,
        )
        monkeypatch.setattr(
            "src.dashboard.graph_service.DashboardGraphService._fetch_stigmergic_edges",
            lambda self, ids: [],
        )
        monkeypatch.setattr(
            "src.dashboard.graph_service.DashboardGraphService._fetch_structural_edges",
            lambda self, ids: [],
        )
        from src.dashboard.api import create_app
        app = create_app()
        response = TestClient(app, raise_server_exceptions=False).get(
            "/api/graph",
            headers={"Authorization": f"Bearer {_token()}"},
        )
        assert response.json()["nodes"][0]["label"] == "tech_table"


# ---------------------------------------------------------------------------
# T024: is_stigmergic / confidence_score on edges
# ---------------------------------------------------------------------------

class TestEdgeFieldsInResponse:
    def test_stigmergic_edge_has_is_stigmergic_true(self, monkeypatch):
        nodes = [_make_raw_node("n1"), _make_raw_node("n2")]
        stig_edges = [{
            "source_id": "n1",
            "target_id": "n2",
            "edge_type": "RELATES_TO",
            "confidence_score": 0.8,
            "rationale_summary": "test",
            "last_accessed": "2026-01-01T00:00:00+00:00",
        }]
        monkeypatch.setattr(
            "src.dashboard.graph_service.DashboardGraphService._fetch_nodes",
            lambda self, scope: nodes,
        )
        monkeypatch.setattr(
            "src.dashboard.graph_service.DashboardGraphService._fetch_stigmergic_edges",
            lambda self, ids: stig_edges,
        )
        monkeypatch.setattr(
            "src.dashboard.graph_service.DashboardGraphService._fetch_structural_edges",
            lambda self, ids: [],
        )
        from src.dashboard.api import create_app
        app = create_app()
        response = TestClient(app, raise_server_exceptions=False).get(
            "/api/graph",
            headers={"Authorization": f"Bearer {_token()}"},
        )
        edges = response.json()["edges"]
        assert len(edges) == 1
        assert edges[0]["is_stigmergic"] is True
        assert edges[0]["confidence_score"] is not None
        assert 0.0 <= edges[0]["confidence_score"] <= 1.0

    def test_all_confidence_scores_in_range(self, monkeypatch):
        nodes = [_make_raw_node("n1"), _make_raw_node("n2")]
        stig_edges = [
            {"source_id": "n1", "target_id": "n2", "edge_type": "X",
             "confidence_score": 0.5, "rationale_summary": None, "last_accessed": None},
        ]
        monkeypatch.setattr("src.dashboard.graph_service.DashboardGraphService._fetch_nodes",
                            lambda self, scope: nodes)
        monkeypatch.setattr("src.dashboard.graph_service.DashboardGraphService._fetch_stigmergic_edges",
                            lambda self, ids: stig_edges)
        monkeypatch.setattr("src.dashboard.graph_service.DashboardGraphService._fetch_structural_edges",
                            lambda self, ids: [])
        from src.dashboard.api import create_app
        app = create_app()
        response = TestClient(app, raise_server_exceptions=False).get(
            "/api/graph",
            headers={"Authorization": f"Bearer {_token()}"},
        )
        for edge in response.json()["edges"]:
            if edge["confidence_score"] is not None:
                assert 0.0 <= edge["confidence_score"] <= 1.0


# ---------------------------------------------------------------------------
# T028: meta_types in response
# ---------------------------------------------------------------------------

class TestMetaTypesInResponse:
    def test_meta_types_present_and_deduplicated(self, monkeypatch):
        nodes = [
            _make_raw_node("n1", meta_type_name="Table"),
            _make_raw_node("n2", meta_type_name="Table"),  # duplicate
            _make_raw_node("n3", meta_type_name="Dashboard"),
        ]
        monkeypatch.setattr("src.dashboard.graph_service.DashboardGraphService._fetch_nodes",
                            lambda self, scope: nodes)
        monkeypatch.setattr("src.dashboard.graph_service.DashboardGraphService._fetch_stigmergic_edges",
                            lambda self, ids: [])
        monkeypatch.setattr("src.dashboard.graph_service.DashboardGraphService._fetch_structural_edges",
                            lambda self, ids: [])
        from src.dashboard.api import create_app
        app = create_app()
        response = TestClient(app, raise_server_exceptions=False).get(
            "/api/graph",
            headers={"Authorization": f"Bearer {_token()}"},
        )
        data = response.json()
        assert sorted(data["meta_types"]) == ["Dashboard", "Table"]

    def test_meta_types_match_node_meta_type_names(self, monkeypatch):
        nodes = [
            _make_raw_node("n1", meta_type_name="Schema"),
            _make_raw_node("n2", meta_type_name="Column"),
        ]
        monkeypatch.setattr("src.dashboard.graph_service.DashboardGraphService._fetch_nodes",
                            lambda self, scope: nodes)
        monkeypatch.setattr("src.dashboard.graph_service.DashboardGraphService._fetch_stigmergic_edges",
                            lambda self, ids: [])
        monkeypatch.setattr("src.dashboard.graph_service.DashboardGraphService._fetch_structural_edges",
                            lambda self, ids: [])
        from src.dashboard.api import create_app
        app = create_app()
        response = TestClient(app, raise_server_exceptions=False).get(
            "/api/graph",
            headers={"Authorization": f"Bearer {_token()}"},
        )
        data = response.json()
        node_meta_types = {n["meta_type_name"] for n in data["nodes"]}
        assert set(data["meta_types"]) == node_meta_types
