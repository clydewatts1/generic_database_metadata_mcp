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


# ===========================================================================
# 001-schema-health-widget — Health Endpoint Integration Tests
# T010: Authentication + basic success + domain isolation + audit (SC-003,004,005)
# T016: Refresh / sequential requests (SC-008)
# T019: Degraded state (SC-006, FR-010)
# ===========================================================================

from unittest.mock import MagicMock


def _health_meta_type(
    name: str = "CustomerLoan",
    health_score: float = 1.0,
    domain_scope: str = "Finance",
    type_category_value: str = "NODE",
):
    """Build a minimal MetaType-like mock for health service tests."""
    from src.models.base import MetaType, TypeCategory
    return MetaType(
        name=name,
        type_category=TypeCategory(type_category_value),
        schema_definition={"type": "object", "properties": {}},
        health_score=health_score,
        domain_scope=domain_scope,
    )


def _health_client(monkeypatch, mock_meta_types=None, secret: str = _SECRET) -> "TestClient":
    """Build a TestClient for the health endpoint with patched dependencies.

    Patches:
      - AuditService.write_audit → returns a mock audit ID (no FalkorDB call)
      - list_meta_types → returns mock_meta_types (default: one Finance MetaType)
    """
    monkeypatch.setenv("DASHBOARD_JWT_SECRET", secret)
    if mock_meta_types is None:
        mock_meta_types = [_health_meta_type("CustomerLoan", health_score=1.0)]

    monkeypatch.setattr(
        "src.dashboard.security.AuditService.write_audit",
        MagicMock(return_value="mock-audit-id"),
    )
    monkeypatch.setattr(
        "src.dashboard.health_service.list_meta_types",
        lambda scope: [mt for mt in mock_meta_types if mt.domain_scope == scope or mt.domain_scope == "Global"],
    )
    from src.dashboard.api import create_app
    return TestClient(create_app(), raise_server_exceptions=False)


def _health_token(domain_scope: str = "Finance", profile_id: str = "analyst_1") -> str:
    return _token(domain_scope=domain_scope, profile_id=profile_id)


class TestHealthEndpointAuth:
    """T010 / SC-003: Authentication gate on GET /api/health/meta-types."""

    def test_missing_token_returns_401(self, monkeypatch):
        client = _health_client(monkeypatch)
        response = client.get("/api/health/meta-types")
        assert response.status_code == 401
        assert "WWW-Authenticate" in response.headers

    def test_expired_token_returns_401(self, monkeypatch):
        client = _health_client(monkeypatch)
        now = int(time.time())
        expired = jwt.encode(
            {"profile_id": "u1", "domain_scope": "Finance", "exp": now - 30},
            _SECRET, algorithm=_ALGORITHM,
        )
        response = client.get(
            "/api/health/meta-types",
            headers={"Authorization": f"Bearer {expired}"},
        )
        assert response.status_code == 401

    def test_missing_domain_scope_returns_403(self, monkeypatch):
        client = _health_client(monkeypatch)
        now = int(time.time())
        token = jwt.encode(
            {"profile_id": "u1", "exp": now + 3600},
            _SECRET, algorithm=_ALGORITHM,
        )
        response = client.get(
            "/api/health/meta-types",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403

    def test_missing_profile_id_returns_403(self, monkeypatch):
        client = _health_client(monkeypatch)
        now = int(time.time())
        token = jwt.encode(
            {"domain_scope": "Finance", "exp": now + 3600},
            _SECRET, algorithm=_ALGORITHM,
        )
        response = client.get(
            "/api/health/meta-types",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403

    def test_post_returns_405(self, monkeypatch):
        """GET-only endpoint — POST must return 405 Method Not Allowed."""
        client = _health_client(monkeypatch)
        token = _health_token()
        response = client.post(
            "/api/health/meta-types",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 405


class TestHealthEndpointSuccess:
    """T010 / SC-001, SC-004: Successful response shape and timing."""

    def test_200_with_items(self, monkeypatch):
        items = [
            _health_meta_type("CustomerLoan", health_score=1.0, domain_scope="Finance"),
            _health_meta_type("LoanProduct", health_score=0.3, domain_scope="Finance"),
        ]
        client = _health_client(monkeypatch, mock_meta_types=items)
        response = client.get(
            "/api/health/meta-types",
            headers={"Authorization": f"Bearer {_health_token()}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2

    def test_response_has_required_fields(self, monkeypatch):
        items = [_health_meta_type("CustomerLoan", health_score=0.75)]
        client = _health_client(monkeypatch, mock_meta_types=items)
        response = client.get(
            "/api/health/meta-types",
            headers={"Authorization": f"Bearer {_health_token()}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total_available" in data
        assert "truncated" in data
        assert "audit_status" in data
        assert data["audit_status"] == "ok"
        item = data["items"][0]
        for field in ("id", "name", "type_category", "health_score", "health_band", "domain_scope"):
            assert field in item, f"Missing field in item: {field}"

    def test_sc001_timing_under_2_seconds(self, monkeypatch):
        """SC-001: Response must be served within 2 seconds."""
        items = [_health_meta_type("FastType", health_score=0.9)]
        client = _health_client(monkeypatch, mock_meta_types=items)
        t_start = time.monotonic()
        response = client.get(
            "/api/health/meta-types",
            headers={"Authorization": f"Bearer {_health_token()}"},
        )
        elapsed = time.monotonic() - t_start
        assert response.status_code == 200
        assert elapsed < 2.0, f"SC-001 violated: response took {elapsed:.3f}s (limit 2s)"

    def test_empty_domain_returns_empty_items(self, monkeypatch):
        client = _health_client(monkeypatch, mock_meta_types=[])
        response = client.get(
            "/api/health/meta-types",
            headers={"Authorization": f"Bearer {_health_token('HR')}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total_available"] == 0
        assert data["truncated"] is False


class TestHealthEndpointDomainIsolation:
    """T010 / SC-004: Finance user sees only Finance MetaTypes."""

    def test_finance_user_sees_only_finance_types(self, monkeypatch):
        all_items = [
            _health_meta_type("FinanceType", health_score=0.9, domain_scope="Finance"),
            _health_meta_type("HRType", health_score=0.5, domain_scope="HR"),
        ]
        client = _health_client(monkeypatch, mock_meta_types=all_items)
        response = client.get(
            "/api/health/meta-types",
            headers={"Authorization": f"Bearer {_health_token('Finance')}"},
        )
        assert response.status_code == 200
        names = [item["name"] for item in response.json()["items"]]
        assert "FinanceType" in names
        assert "HRType" not in names

    def test_two_domain_isolation(self, monkeypatch):
        """Finance and HR users each see only their domain."""
        all_items = [
            _health_meta_type("FinanceType", health_score=0.9, domain_scope="Finance"),
            _health_meta_type("HRType", health_score=0.7, domain_scope="HR"),
        ]

        # Finance user
        client_f = _health_client(monkeypatch, mock_meta_types=all_items)
        resp_f = client_f.get(
            "/api/health/meta-types",
            headers={"Authorization": f"Bearer {_health_token('Finance')}"},
        )
        names_f = [item["name"] for item in resp_f.json()["items"]]

        # HR user — rebuild client to pick up the patched scope
        monkeypatch.setattr(
            "src.dashboard.health_service.list_meta_types",
            lambda scope: [mt for mt in all_items if mt.domain_scope == scope],
        )
        from src.dashboard.api import create_app
        client_hr = TestClient(create_app(), raise_server_exceptions=False)
        resp_hr = client_hr.get(
            "/api/health/meta-types",
            headers={"Authorization": f"Bearer {_health_token('HR')}"},
        )
        names_hr = [item["name"] for item in resp_hr.json()["items"]]

        assert "HRType" not in names_f
        assert "FinanceType" not in names_hr


class TestHealthEndpointAudit:
    """T010 / SC-005: Each request writes exactly one audit log entry."""

    def test_single_request_writes_audit_once(self, monkeypatch):
        monkeypatch.setenv("DASHBOARD_JWT_SECRET", _SECRET)
        mock_write = MagicMock(return_value="audit-1")
        monkeypatch.setattr("src.dashboard.security.AuditService.write_audit", mock_write)
        monkeypatch.setattr("src.dashboard.health_service.list_meta_types", lambda s: [])
        from src.dashboard.api import create_app
        client = TestClient(create_app(), raise_server_exceptions=False)
        client.get(
            "/api/health/meta-types",
            headers={"Authorization": f"Bearer {_health_token()}"},
        )
        mock_write.assert_called_once()


class TestHealthEndpointRefresh:
    """T016 / SC-005, SC-008: Sequential requests each write their own audit entry."""

    def test_two_requests_write_two_audit_entries(self, monkeypatch):
        """SC-005: Two sequential requests → 2 audit writes."""
        monkeypatch.setenv("DASHBOARD_JWT_SECRET", _SECRET)
        mock_write = MagicMock(return_value="audit-id")
        monkeypatch.setattr("src.dashboard.security.AuditService.write_audit", mock_write)
        monkeypatch.setattr("src.dashboard.health_service.list_meta_types", lambda s: [])
        from src.dashboard.api import create_app
        client = TestClient(create_app(), raise_server_exceptions=False)
        headers = {"Authorization": f"Bearer {_health_token()}"}
        r1 = client.get("/api/health/meta-types", headers=headers)
        r2 = client.get("/api/health/meta-types", headers=headers)
        assert r1.status_code == 200
        assert r2.status_code == 200
        assert mock_write.call_count == 2

    def test_sc008_two_requests_under_3_seconds(self, monkeypatch):
        """SC-008: Two sequential requests must complete within 3 seconds combined."""
        client = _health_client(monkeypatch, mock_meta_types=[])
        headers = {"Authorization": f"Bearer {_health_token()}"}
        t_start = time.monotonic()
        r1 = client.get("/api/health/meta-types", headers=headers)
        r2 = client.get("/api/health/meta-types", headers=headers)
        elapsed = time.monotonic() - t_start
        assert r1.status_code == 200
        assert r2.status_code == 200
        assert elapsed < 3.0, f"SC-008 violated: two requests took {elapsed:.3f}s (limit 3s)"


class TestHealthEndpointDegradedState:
    """T019 / SC-006, FR-010: FalkorDB failure → 503 degraded response."""

    def test_connection_error_returns_503(self, monkeypatch):
        """FR-010: ConnectionError from list_meta_types → 503."""
        monkeypatch.setenv("DASHBOARD_JWT_SECRET", _SECRET)
        monkeypatch.setattr("src.dashboard.security.AuditService.write_audit", MagicMock(return_value="a"))
        monkeypatch.setattr(
            "src.dashboard.health_service.list_meta_types",
            MagicMock(side_effect=ConnectionError("DB down")),
        )
        from src.dashboard.api import create_app
        client = TestClient(create_app(), raise_server_exceptions=False)
        t_start = time.monotonic()
        response = client.get(
            "/api/health/meta-types",
            headers={"Authorization": f"Bearer {_health_token()}"},
        )
        elapsed = time.monotonic() - t_start
        assert response.status_code == 503
        assert elapsed < 5.0, f"SC-006 violated: degraded response took {elapsed:.3f}s (limit 5s)"

    def test_503_body_shape(self, monkeypatch):
        """FR-010: 503 body must contain status='degraded' and message."""
        monkeypatch.setenv("DASHBOARD_JWT_SECRET", _SECRET)
        monkeypatch.setattr("src.dashboard.security.AuditService.write_audit", MagicMock(return_value="a"))
        monkeypatch.setattr(
            "src.dashboard.health_service.list_meta_types",
            MagicMock(side_effect=RuntimeError("unexpected")),
        )
        from src.dashboard.api import create_app
        client = TestClient(create_app(), raise_server_exceptions=False)
        response = client.get(
            "/api/health/meta-types",
            headers={"Authorization": f"Bearer {_health_token()}"},
        )
        assert response.status_code == 503
        body = response.json()
        assert body.get("status") == "degraded"
        assert "message" in body

    def test_audit_write_failure_returns_503_with_audit_status_failed(self, monkeypatch):
        """Audit write failure → 503 with audit_status:'failed' in body."""
        from fastapi import HTTPException as FE
        monkeypatch.setenv("DASHBOARD_JWT_SECRET", _SECRET)
        monkeypatch.setattr(
            "src.dashboard.security.AuditService.write_audit",
            MagicMock(side_effect=FE(
                status_code=503,
                detail={"status": "degraded", "message": "Audit failed", "audit_status": "failed"},
            )),
        )
        monkeypatch.setattr("src.dashboard.health_service.list_meta_types", lambda s: [])
        from src.dashboard.api import create_app
        client = TestClient(create_app(), raise_server_exceptions=False)
        response = client.get(
            "/api/health/meta-types",
            headers={"Authorization": f"Bearer {_health_token()}"},
        )
        assert response.status_code == 503
        body = response.json()
        # FastAPI wraps HTTPException detail in {"detail": {...}}
        detail = body.get("detail", {})
        if isinstance(detail, dict):
            assert detail.get("audit_status") == "failed"
        else:
            assert body.get("audit_status") == "failed" or detail == "failed"
