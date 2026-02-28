# Implementation Plan: Schema Health Dashboard Widget

**Branch**: `001-schema-health-widget` | **Date**: 2026-02-28 | **Spec**: [specs/001-schema-health-widget/spec.md](spec.md)  
**Input**: Feature specification from `/specs/001-schema-health-widget/spec.md`

## Summary

Add a read-only Schema Health Widget to the existing Visual Web Dashboard (FastAPI, port 8080). The widget surfaces every `(:MetaType)` node's `health_score` within the authenticated user's `domain_scope`, with colour-coded indicators (green/amber/red). A new `GET /api/health/meta-types` endpoint serves full JSON (Rule 3.6 exempt) and is protected by the Unified Security Layer (Rule 5.6), which includes JWT auth, claims enforcement (Rule 5.2), and atomic FalkorDB audit logging (Rule 5.7). Data sourced by reusing `src.graph.ontology.list_meta_types()` — no new Cypher writes from this feature.

---

## Technical Context

**Language/Version**: Python 3.14.2  
**Primary Dependencies**: FastAPI 0.11x, uvicorn, PyJWT 2.11.0, falkordb, Pydantic 2.12.5, structlog, httpx (TestClient), freezegun  
**Storage**: FalkorDB on localhost:6379 — read: `(:MetaType)` nodes; write: `(:HumanAuditLog)` nodes  
**Testing**: pytest 9.0.2, httpx TestClient (FastAPI), monkeypatch for service mocking; freezegun for timestamp assertions  
**Target Platform**: Linux/Windows server process; browser (Cytoscape.js 3.x CDN, vanilla JS in `dashboard/`)  
**Project Type**: Web service (FastAPI REST API) + static SPA frontend  
**Performance Goals**: Widget renders in ≤2s (SC-001); Refresh completes in ≤3s (SC-008); 503 within 5s on degraded FalkorDB (SC-006)  
**Constraints**: Read-only — zero `CREATE/SET/DELETE/MERGE` reachable from new endpoint (SC-007); audit write atomic (Rule 5.7); `DASHBOARD_NODE_LIMIT` cap (default 500, FR-012)  
**Scale/Scope**: Single-service; same FalkorDB instance; dashboard user count expected <100 concurrent

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Rule | Gate | Status | Notes |
|------|------|--------|-------|
| **Rule 2.6** | MetaType `health_score` exposed accurately | ✅ PASS | Widget reads `health_score` via existing `list_meta_types()`; no writes |
| **Rule 3.2** | Semantic compression for LLM responses | ✅ N/A | Dashboard serves a browser, not an LLM |
| **Rule 3.6** | Human Viewport Exception exempts dashboard from TOON | ✅ PASS | Endpoint returns full JSON; TOON not applied |
| **Rule 4.4** | AI stigmergic actions carry `created_by_prompt_hash` | ✅ PASS | No AI actions; `(:HumanAuditLog)` MUST NOT carry `created_by_prompt_hash` |
| **Rule 5.2** | Scoped visibility — no cross-domain leakage | ✅ PASS | `domain_scope` injected as Cypher parameter only, never from query string |
| **Rule 5.6** | Unified Security Layer on all dashboard routes | ✅ PASS | `api_router = APIRouter(dependencies=[Depends(unified_security)])` — see research R-003 |
| **Rule 5.7** | Audit log for every human dashboard read | ✅ PASS | `(:HumanAuditLog)` written before data query (EAFP); 503 on audit failure |
| **Rule 6.1** | Unit tests for stigmergic mechanics | ✅ N/A | Widget does not modify stigmergic mechanics |
| **Rule 6.2** | Payload size assertions | ✅ PASS | SC-007 contract test; SC-004 domain isolation test |
| **Rule 6.3** | Ephemeral sandbox tests | ✅ PASS | All new tests use FastAPI `TestClient` + monkeypatch; no persistent state |

**Post-Phase-1 re-check**: All gates pass. No constitution violations. Complexity Tracking table not required.

---

## Project Structure

### Documentation (this feature)

```text
specs/001-schema-health-widget/
├── plan.md              ✅ this file
├── research.md          ✅ Phase 0 output
├── data-model.md        ✅ Phase 1 output
├── quickstart.md        ✅ Phase 1 output
├── contracts/
│   └── api-health-meta-types.md  ✅ Phase 1 output
└── tasks.md             ⬜ Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
src/
├── dashboard/
│   ├── api.py               # MODIFIED — register api_router with Depends(unified_security)
│   ├── auth.py              # UNCHANGED — get_current_user() remains the JWT dep
│   ├── security.py          # NEW — UnifiedSecurityLayer (Rule 5.6); AuditService; session_id
│   ├── health_service.py    # NEW — HealthService.get_health_payload(user) → HealthPayloadResponse
│   ├── health_router.py     # NEW — GET /api/health/meta-types route
│   ├── models.py            # MODIFIED — add MetaTypeHealthResponse, HealthPayloadResponse
│   ├── router.py            # UNCHANGED
│   ├── graph_service.py     # UNCHANGED
│   ├── config.py            # UNCHANGED
│   └── server.py            # UNCHANGED

dashboard/
│   ├── index.html           # MODIFIED — add health widget panel markup
│   ├── app.js               # MODIFIED — health panel fetch, sort, colour bands, refresh, degraded state
│   └── style.css            # MODIFIED — health-green / health-amber / health-red CSS classes, panel layout

tests/
├── unit/
│   └── dashboard/
│       ├── test_auth.py                  # UNCHANGED
│       ├── test_graph_service.py         # UNCHANGED
│       ├── test_performance.py           # UNCHANGED
│       ├── test_health_service.py        # NEW — HealthService unit tests (colour bands, cap, scoping)
│       └── test_unified_security.py      # NEW — USL dependency chain tests (401, 403, audit write)
├── contract/
│   ├── test_dashboard_mutations.py       # MODIFIED — add read-only assertion for /api/health/meta-types
│   └── test_health_mutations.py          # NEW — assert no Cypher writes from health endpoint (SC-007)
└── integration/
    └── test_dashboard_api.py             # MODIFIED — add health endpoint integration tests (SC-001–008)
```

**Structure Decision**: Single-project layout. New files are lateral additions to `src/dashboard/` using the same patterns as the existing graph service and router. The Unified Security Layer (`security.py`) is extracted as a distinct component rather than extending `auth.py` to satisfy Rule 5.6's "independently testable" requirement.

---

## Complexity Tracking

> **No constitution violations — table not required.**

