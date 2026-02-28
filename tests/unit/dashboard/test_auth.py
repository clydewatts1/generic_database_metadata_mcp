"""Unit tests for src/dashboard/auth.py.

Tests:
- Valid JWT → DashboardUser
- Missing token → HTTP 401
- Expired token → HTTP 401
- Invalid signature → HTTP 401
- Missing profile_id claim → HTTP 403
- Missing domain_scope claim → HTTP 403
- domain_scope in query param has no effect (Rule 5.2)
"""

from __future__ import annotations

import time

import jwt
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.dashboard.auth import get_current_user
from src.dashboard.models import DashboardUser

_SECRET = "test-secret-key-for-unit-tests"
_ALGORITHM = "HS256"


# ---------------------------------------------------------------------------
# Minimal FastAPI app for testing the dependency
# ---------------------------------------------------------------------------

def _make_app(secret: str = _SECRET) -> FastAPI:
    import os
    os.environ["DASHBOARD_JWT_SECRET"] = secret

    app = FastAPI()

    @app.get("/whoami")
    def whoami(user: DashboardUser = __import__("fastapi").Depends(get_current_user)):
        return {"profile_id": user.profile_id, "domain_scope": user.domain_scope}

    return app


def _valid_token(extra_claims: dict | None = None, expired: bool = False, secret: str = _SECRET) -> str:
    """Generate a test JWT with standard claims."""
    now = int(time.time())
    payload = {
        "profile_id": "user-001",
        "domain_scope": "Finance",
        "exp": (now - 10) if expired else (now + 3600),
        "iat": now,
    }
    if extra_claims is not None:
        payload.update(extra_claims)
    return jwt.encode(payload, secret, algorithm=_ALGORITHM)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def client(monkeypatch) -> TestClient:
    import os
    monkeypatch.setenv("DASHBOARD_JWT_SECRET", _SECRET)
    app = _make_app()
    return TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestValidToken:
    def test_valid_token_returns_dashboard_user(self, client: TestClient):
        token = _valid_token()
        response = client.get("/whoami", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        data = response.json()
        assert data["profile_id"] == "user-001"
        assert data["domain_scope"] == "Finance"

    def test_different_scope_returned_correctly(self, client: TestClient):
        token = _valid_token(extra_claims={"domain_scope": "Marketing", "profile_id": "mkt-user"})
        response = client.get("/whoami", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        assert response.json()["domain_scope"] == "Marketing"


class TestMissingToken:
    def test_no_auth_header_returns_401(self, client: TestClient):
        response = client.get("/whoami")
        assert response.status_code == 401

    def test_empty_bearer_returns_401(self, client: TestClient):
        response = client.get("/whoami", headers={"Authorization": "Bearer "})
        assert response.status_code == 401


class TestExpiredToken:
    def test_expired_token_returns_401(self, client: TestClient):
        token = _valid_token(expired=True)
        response = client.get("/whoami", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 401

    def test_expired_token_detail_mentions_expired(self, client: TestClient):
        token = _valid_token(expired=True)
        response = client.get("/whoami", headers={"Authorization": f"Bearer {token}"})
        assert "expired" in response.json()["detail"].lower()


class TestInvalidToken:
    def test_wrong_secret_returns_401(self, client: TestClient):
        token = _valid_token(secret="wrong-secret")
        response = client.get("/whoami", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 401

    def test_garbage_token_returns_401(self, client: TestClient):
        response = client.get("/whoami", headers={"Authorization": "Bearer not.a.valid.token"})
        assert response.status_code == 401


class TestMissingClaims:
    def test_missing_profile_id_returns_403(self, client: TestClient):
        # Build token WITHOUT profile_id
        now = int(time.time())
        payload = {
            "domain_scope": "Finance",
            "exp": now + 3600,
            "iat": now,
        }
        token = jwt.encode(payload, _SECRET, algorithm=_ALGORITHM)
        response = client.get("/whoami", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 403
        assert "profile_id" in response.json()["detail"]

    def test_missing_domain_scope_returns_403(self, client: TestClient):
        # Build token WITHOUT domain_scope
        now = int(time.time())
        payload = {
            "profile_id": "user-001",
            "exp": now + 3600,
            "iat": now,
        }
        token = jwt.encode(payload, _SECRET, algorithm=_ALGORITHM)
        response = client.get("/whoami", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 403
        assert "domain_scope" in response.json()["detail"]

    def test_missing_both_claims_returns_403(self, client: TestClient):
        now = int(time.time())
        payload = {"exp": now + 3600, "iat": now}
        token = jwt.encode(payload, _SECRET, algorithm=_ALGORITHM)
        response = client.get("/whoami", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 403


class TestRule52DomainScopeQueryParamIgnored:
    """Rule 5.2: domain_scope MUST come from JWT claim, never from query params."""

    def test_query_param_does_not_override_jwt_scope(self, client: TestClient):
        """Even if ?domain_scope=Marketing is passed, the Finance JWT wins."""
        token = _valid_token(extra_claims={"domain_scope": "Finance", "profile_id": "user-001"})
        response = client.get(
            "/whoami?domain_scope=Marketing",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        # domain_scope should still be Finance (from JWT), not Marketing (from query)
        assert response.json()["domain_scope"] == "Finance"
