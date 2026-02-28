"""Unit tests for src/dashboard/security.py — unified_security dependency.

Covers:
  - SC-003: derive_session_id (tok:, ip:, fallback)
  - SC-005: AuditService.write_audit called exactly once per valid request
  - Rule 5.6: Missing token → 401, missing claims → 403, valid → DashboardUser
  - AuditService failure → 503 with audit_status:"failed"
"""

from __future__ import annotations

import hashlib
import time
from unittest.mock import MagicMock, patch

import jwt
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

_SECRET = "unit-security-test-secret"
_ALGORITHM = "HS256"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_token(profile_id: str = "analyst_1", domain_scope: str = "Finance") -> str:
    now = int(time.time())
    return jwt.encode(
        {"profile_id": profile_id, "domain_scope": domain_scope, "exp": now + 3600, "iat": now},
        _SECRET,
        algorithm=_ALGORITHM,
    )


def _make_app(monkeypatch) -> TestClient:
    """Build a minimal FastAPI app with unified_security as a route dependency."""
    import os
    monkeypatch.setenv("DASHBOARD_JWT_SECRET", _SECRET)
    # (Re-)import after env is set to avoid cached state issues
    from src.dashboard.api import create_app
    app = create_app()
    return TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# TestDeriveSessionId
# ---------------------------------------------------------------------------

class TestDeriveSessionId:
    """SC-003: Session ID derivation (R-002)."""

    def test_with_credentials_starts_with_tok(self):
        from src.dashboard.security import derive_session_id
        from unittest.mock import MagicMock
        mock_req = MagicMock()
        mock_creds = MagicMock()
        mock_creds.credentials = "my-secret-token"
        result = derive_session_id(mock_req, mock_creds)
        assert result.startswith("tok:")

    def test_with_credentials_is_8_hex_chars(self):
        from src.dashboard.security import derive_session_id
        from unittest.mock import MagicMock
        mock_req = MagicMock()
        mock_creds = MagicMock()
        mock_creds.credentials = "some-token-value"
        result = derive_session_id(mock_req, mock_creds)
        hex_part = result[len("tok:"):]
        assert len(hex_part) == 8
        int(hex_part, 16)  # must be valid hex

    def test_with_credentials_matches_sha256(self):
        from src.dashboard.security import derive_session_id
        from unittest.mock import MagicMock
        token = "deterministic-token-abc"
        expected_hash = hashlib.sha256(token.encode()).hexdigest()[:8]
        mock_req = MagicMock()
        mock_creds = MagicMock()
        mock_creds.credentials = token
        result = derive_session_id(mock_req, mock_creds)
        assert result == f"tok:{expected_hash}"

    def test_without_credentials_uses_x_forwarded_for(self):
        from src.dashboard.security import derive_session_id
        from unittest.mock import MagicMock
        mock_req = MagicMock()
        mock_req.headers = {"X-Forwarded-For": "10.0.0.1, 10.0.0.2"}
        mock_req.client = None
        result = derive_session_id(mock_req, None)
        assert result == "ip:10.0.0.1"

    def test_without_credentials_uses_client_host(self):
        from src.dashboard.security import derive_session_id
        from unittest.mock import MagicMock
        mock_req = MagicMock()
        mock_req.headers = {}
        mock_req.client.host = "192.168.1.5"
        result = derive_session_id(mock_req, None)
        assert result == "ip:192.168.1.5"


# ---------------------------------------------------------------------------
# TestAuditServiceWriteAudit
# ---------------------------------------------------------------------------

class TestAuditServiceWriteAudit:
    """AuditService raises 503 + audit_status:failed when FalkorDB fails."""

    def test_falkordb_exception_raises_503(self, monkeypatch):
        from fastapi import HTTPException
        from src.dashboard.security import AuditService

        monkeypatch.setattr(
            "src.graph.client.execute_query",
            MagicMock(side_effect=ConnectionError("FalkorDB unreachable")),
        )

        with pytest.raises(HTTPException) as exc_info:
            AuditService.write_audit(
                profile_id="analyst_1",
                domain_scope="Finance",
                endpoint_path="/api/health/meta-types",
                session_id="tok:abcd1234",
            )
        assert exc_info.value.status_code == 503
        assert exc_info.value.detail["audit_status"] == "failed"
        assert exc_info.value.detail["status"] == "degraded"


# ---------------------------------------------------------------------------
# TestUnifiedSecurityAuth
# ---------------------------------------------------------------------------

class TestUnifiedSecurityAuth:
    """Rule 5.6: Authentication + audit write-through via /api/health/meta-types."""

    def _client(self, monkeypatch) -> TestClient:
        monkeypatch.setenv("DASHBOARD_JWT_SECRET", _SECRET)
        from src.dashboard.api import create_app
        app = create_app()
        return TestClient(app, raise_server_exceptions=False)

    def _patch_write_audit_and_list(self, monkeypatch):
        """Patch both AuditService.write_audit and list_meta_types for routing tests."""
        monkeypatch.setattr(
            "src.dashboard.security.AuditService.write_audit",
            MagicMock(return_value="test-audit-id"),
        )
        monkeypatch.setattr(
            "src.dashboard.health_service.list_meta_types",
            lambda scope: [],
        )

    def test_missing_token_returns_401(self, monkeypatch):
        self._patch_write_audit_and_list(monkeypatch)
        client = self._client(monkeypatch)
        response = client.get("/api/health/meta-types")
        assert response.status_code == 401
        assert "WWW-Authenticate" in response.headers

    def test_expired_token_returns_401(self, monkeypatch):
        self._patch_write_audit_and_list(monkeypatch)
        client = self._client(monkeypatch)
        now = int(time.time())
        expired_token = jwt.encode(
            {"profile_id": "u1", "domain_scope": "Finance", "exp": now - 10},
            _SECRET, algorithm=_ALGORITHM,
        )
        response = client.get(
            "/api/health/meta-types",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert response.status_code == 401

    def test_missing_domain_scope_returns_403(self, monkeypatch):
        self._patch_write_audit_and_list(monkeypatch)
        client = self._client(monkeypatch)
        now = int(time.time())
        token = jwt.encode(
            {"profile_id": "u1", "exp": now + 3600},  # no domain_scope
            _SECRET, algorithm=_ALGORITHM,
        )
        response = client.get(
            "/api/health/meta-types",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403

    def test_missing_profile_id_returns_403(self, monkeypatch):
        self._patch_write_audit_and_list(monkeypatch)
        client = self._client(monkeypatch)
        now = int(time.time())
        token = jwt.encode(
            {"domain_scope": "Finance", "exp": now + 3600},  # no profile_id
            _SECRET, algorithm=_ALGORITHM,
        )
        response = client.get(
            "/api/health/meta-types",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403

    def test_valid_token_calls_write_audit_once(self, monkeypatch):
        mock_write = MagicMock(return_value="audit-id-1")
        monkeypatch.setattr("src.dashboard.security.AuditService.write_audit", mock_write)
        monkeypatch.setattr(
            "src.dashboard.health_service.list_meta_types",
            lambda scope: [],
        )
        client = self._client(monkeypatch)
        token = _make_token()
        response = client.get(
            "/api/health/meta-types",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        mock_write.assert_called_once()

    def test_audit_failure_returns_503_with_audit_status_failed(self, monkeypatch):
        from fastapi import HTTPException as FE
        monkeypatch.setattr(
            "src.dashboard.security.AuditService.write_audit",
            MagicMock(
                side_effect=FE(
                    status_code=503,
                    detail={"status": "degraded", "message": "Audit failed", "audit_status": "failed"},
                )
            ),
        )
        monkeypatch.setattr(
            "src.dashboard.health_service.list_meta_types",
            lambda scope: [],
        )
        client = self._client(monkeypatch)
        token = _make_token()
        response = client.get(
            "/api/health/meta-types",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 503
        body = response.json()
        # FastAPI wraps HTTPException detail in {"detail": {...}}
        detail = body.get("detail", {})
        if isinstance(detail, dict):
            assert detail.get("audit_status") == "failed"
        else:
            # Some FastAPI versions may return flat detail; check both paths
            assert body.get("audit_status") == "failed" or detail == "failed"

    def test_write_audit_called_with_correct_profile_and_scope(self, monkeypatch):
        mock_write = MagicMock(return_value="audit-id-x")
        monkeypatch.setattr("src.dashboard.security.AuditService.write_audit", mock_write)
        monkeypatch.setattr(
            "src.dashboard.health_service.list_meta_types",
            lambda scope: [],
        )
        client = self._client(monkeypatch)
        token = _make_token(profile_id="analyst_99", domain_scope="HR")
        client.get(
            "/api/health/meta-types",
            headers={"Authorization": f"Bearer {token}"},
        )
        call_kwargs = mock_write.call_args
        # Can be positional or keyword
        args = call_kwargs.args if call_kwargs.args else ()
        kwargs = call_kwargs.kwargs if call_kwargs.kwargs else {}
        all_args = list(args) + list(kwargs.values())
        assert "analyst_99" in all_args
        assert "HR" in all_args
