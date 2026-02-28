# Research: Schema Health Dashboard Widget

**Feature**: `001-schema-health-widget`  
**Branch**: `001-schema-health-widget`  
**Phase**: 0 — Unknowns resolved

---

## R-001 — Audit Log Storage Pattern

**Decision**: Store audit entries as `(:HumanAuditLog)` graph nodes in FalkorDB.

**Rationale**:  
Rule 5.7 sets three hard requirements — queryable, retained for the operational lifetime of the Stigmergic Graph Engine, and atomic with the action (503 if audit fails). FalkorDB is the only persistent store in the project; no external log services exist. Storing audit entries as graph nodes:
- Satisfies queryability via Cypher (`MATCH (a:HumanAuditLog)`)
- Shares the same lifecycle and backup destiny as all other graph data
- Enables atomic enforcement: write the `(:HumanAuditLog)` CREATE **before** the data query; if the CREATE fails, raise HTTP 503 immediately (EAFP pattern)

**Alternatives considered**:
- **structlog to file** — Rejected. Log files are not queryable via Cypher, not lifecycle-bound to FalkorDB, and cannot be made transactionally atomic (no fail-fast mechanism).
- **Redis RPUSH** (native to FalkorDB's underlying store) — Rejected. Loses graph traversal, breaks the data model abstraction, no Cypher query capability.
- **SQLite in-process** — Rejected. Introduces a second persistent store, violates single-store constraint, adds schema migration complexity.

**Implementation notes**:
- Write order: `CREATE (:HumanAuditLog {...})` → then execute data query
- EAFP: `try: execute_query(audit_create) except Exception: raise HTTPException(503)`
- Three outcomes are all Rule 5.7 compliant: audit-fail → 503; audit-ok + query-fail → 503 (audit of attempt retained); both ok → 200
- structlog remains for real-time observability alongside the FalkorDB audit of record
- Recommended FalkorDB indices: `CREATE INDEX FOR (a:HumanAuditLog) ON (a.profile_id)` and `ON (a.timestamp)`
- Node properties MUST NOT include `created_by_prompt_hash` (that field is Rule 4.4 / AI-only)

---

## R-002 — `human_session_id` Derivation

**Decision**: Use a SHA-256 prefix of the JWT token: `"tok:{sha256(token)[:8]}"`. Fall back to `"ip:{client_ip}"` on unauthenticated paths.

**Rationale**:  
Rule 5.7 defines `human_session_id` as "session token or client IP where a session identifier is not available." In this stateless JWT system the token *is* the session identifier per issuance. A SHA-256 prefix is:
- Deterministic (same token → same prefix; correlatable within session)
- Privacy-preserving (8 hex chars = 32 bits of SHA-256; irreversible)
- Unique per token issuance, not per user (correctly identifies sessions vs users)

**Alternatives considered**:
- **IP address only** — Rejected. Poor granularity behind NAT; proxy IP instead of real client.
- **Combined `ip:hash`** — Rejected. Redundant; adds potential GDPR exposure of IP PII with no audit benefit.
- **`X-Session-ID` header** — Rejected. Client-controlled values in an audit log are a security anti-pattern; spoofable.
- **`jti` JWT claim** — Not available; project tokens only carry `profile_id` + `domain_scope`.

**Implementation**:
```python
import hashlib
from fastapi import Request
from fastapi.security import HTTPAuthorizationCredentials

def derive_session_id(request: Request, credentials: HTTPAuthorizationCredentials | None) -> str:
    if credentials and credentials.credentials:
        prefix = hashlib.sha256(credentials.credentials.encode()).hexdigest()[:8]
        return f"tok:{prefix}"
    forwarded = request.headers.get("X-Forwarded-For")
    ip = forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else "unknown")
    return f"ip:{ip}"
```

---

## R-003 — Unified Security Layer (Rule 5.6) Implementation Pattern

**Decision**: `APIRouter(dependencies=[Depends(unified_security)])` — Option C. A single async FastAPI dependency `unified_security` is registered on `api_router` at construction time in `api.py`.

**Rationale**:  
Router-level `dependencies=` registration ensures every current and future route inherits the USL automatically — a new route cannot accidentally skip it. FastAPI's per-request dependency cache means `get_current_user` decodes the JWT exactly once per request even though it appears in both the USL and the route signature. The component is independently unit-testable via `dependency_overrides` without needing a full ASGI stack.

**Alternatives considered**:
- **Per-route `Depends()` chain** — Rejected. Every route must explicitly opt in; a new route can silently skip the USL, which is a constitution violation (Rule 5.6: "No dashboard route MAY be registered that bypasses any step").
- **ASGI Starlette middleware** — Rejected. Sits outside FastAPI's DI graph, cannot inject typed objects, body-streaming complicates pre-response audit writes, requires full `TestClient` for unit tests (no `dependency_overrides`).

**Component location**: `src/dashboard/security.py`

**Interface sketch**:
```python
# src/dashboard/security.py
async def unified_security(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    user: DashboardUser = Depends(get_current_user),   # raises 401/403
) -> None:
    """USL: steps 1-4 of Rule 5.6. Raises 503 if audit write fails."""
    session_id = derive_session_id(request, credentials)
    _write_audit_log(
        profile_id=user.profile_id,
        domain_scope=user.domain_scope,
        action_type="READ",
        path=str(request.url.path),
        human_session_id=session_id,
    )  # EAFP: raises HTTPException(503) on failure

# src/dashboard/api.py  — one additional import + one argument change
from .security import unified_security
api_router = APIRouter(prefix="/api", dependencies=[Depends(unified_security)])
```

**Domain scope injection (step 3 of Rule 5.6)**:  
The USL does not inject scope into Cypher directly. Routes receive `DashboardUser` via `Depends(get_current_user)` (FastAPI caches per-request; no re-execution) and pass `user.domain_scope` as a named Cypher parameter — never as string interpolation.

---

## R-004 — Existing `list_meta_types` Cypher Query

**Decision**: Reuse `src.graph.ontology.list_meta_types(domain_scope)` as the data source for the health widget.

**Rationale**: The function already exists and is correct:
```python
def list_meta_types(domain_scope: str = "Global") -> list[MetaType]:
    result = execute_query(
        "MATCH (m:MetaType) WHERE m.domain_scope IN [$domain_scope, 'Global'] RETURN m",
        {"domain_scope": domain_scope},
    )
    return [_row_to_meta_type(row) for row in result.result_set]
```
The query is read-only (MATCH only), uses a parameterised scope filter (Rule 5.2), and returns `MetaType` objects that include `name`, `type_category`, `health_score`, `domain_scope`, and `id`. No new Cypher is required.

**Node cap**: If `len(results) > DASHBOARD_NODE_LIMIT`, slice and set `truncated=True` in the response — consistent with the graph endpoint's existing pattern.

---

## Summary of All Decisions

| ID | Question | Decision |
|----|----------|----------|
| R-001 | Audit log storage | FalkorDB `(:HumanAuditLog)` nodes, written before data query (EAFP) |
| R-002 | `human_session_id` | `"tok:{sha256(jwt)[:8]}"`, fallback `"ip:{client_ip}"` |
| R-003 | Unified Security Layer | `APIRouter(dependencies=[Depends(unified_security)])` in `api.py` |
| R-004 | MetaType data source | Reuse `src.graph.ontology.list_meta_types(domain_scope)` |
