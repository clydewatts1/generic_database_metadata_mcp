# Implementation Plan: Visual Web Dashboard

**Branch**: `001-visual-graph-dashboard` | **Date**: 2026-02-28 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/001-visual-graph-dashboard/spec.md`

## Summary

Build a read-only browser dashboard that renders the stigmergic metadata graph as an interactive Cytoscape.js node-link diagram, enforcing profile-aware domain scoping (Rule 5.2) via JWT Bearer token authentication. A new FastAPI process (port 8080) wraps the existing `query_graph()` service and serves both a JSON API and static HTML/JS assets. Stigmergic edges are visually encoded by `confidence_score`; structural edges are visually distinct. Users can filter by Object Type and search by `business_name`. No graph mutations are possible.

## Technical Context

**Language/Version**: Python 3.11 (existing project standard)
**Primary Dependencies**: FastAPI + uvicorn (already in requirements), PyJWT (new — JWT Bearer token auth), Cytoscape.js 3.x (CDN, no npm/build step needed)
**Storage**: FalkorDB (existing — read-only queries via `src/graph/query.py`)
**Testing**: pytest + FastAPI TestClient (existing pytest setup; add `tests/unit/dashboard/`, `tests/integration/test_dashboard_api.py`, `tests/contract/test_dashboard_mutations.py`)
**Target Platform**: Local/server HTTP (port 8080), modern evergreen browsers
**Project Type**: Web service (backend API) + static single-page app (frontend)
**Performance Goals**: Initial canvas render ≤ 3s for ≤ 500 nodes / 2,000 edges; filter/search update ≤ 500ms (SC-002, SC-005)
**Constraints**: Read-only (zero graph mutations); max 500 nodes per payload (`truncated` flag when exceeded); JWT claims are the sole source of `domain_scope` (no query-param override); Cypher depth bounded at 1–2 hops (Rule 3.1)
**Scale/Scope**: Single scoped view ≤ 500 nodes; single dashboard instance per deployment; no multi-tenancy session store

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Rule | Applies? | Status | Notes |
|------|----------|--------|-------|
| **Rule 2.1** Dynamic Type Registration | No | ✅ Pass | Dashboard creates no new MetaTypes |
| **Rule 2.3** Pre-Insertion Validation | No | ✅ Pass | Dashboard performs no insertions |
| **Rule 2.8** Circuit Breaker | No | ✅ Pass | No mutations → circuit breaker never triggered |
| **Rule 3.1** Bounded Cypher (1–2 hops) | **Yes** | ✅ Pass | `DashboardGraphService` calls `query_graph()` which already enforces depth limits |
| **Rule 3.2** Semantic Compression | Exempt | ✅ Exempt | Rule 3.6 grants explicit exemption for browser-facing API |
| **Rule 3.3** Pagination (>5 nodes) | **Yes (adapted)** | ✅ Pass | Hard cap at 500 nodes + `truncated` flag replaces LLM pagination; consistent with spirit of rule |
| **Rule 3.4** Genesis Seed | No | ✅ Pass | No bulk ingest |
| **Rule 3.5** TOON Serialisation | Exempt | ✅ Exempt | Rule 3.6 grants explicit exemption for browser-facing API |
| **Rule 3.6** Human Viewport Exception | **Defines this feature** | ✅ Pass | This feature IS the Rule 3.6 provision |
| **Rule 5.1** User Context Injection | **Yes** | ✅ Pass | JWT claims `profile_id` + `domain_scope` injected via `auth.py` dependency |
| **Rule 5.2** Scoped Visibility | **Yes — MANDATORY** | ✅ Pass | `domain_scope` from JWT passed to `query_graph()` on every request; no bypass possible |
| **Rule 5.5** APPROVAL_REQUIRED | No | ✅ Pass | No delete/drop operations |
| **Rule 6.1** Test-Driven Stigmergy | **Yes** | ✅ Pass | `tests/unit/dashboard/` covers auth and scope enforcement |
| **Rule 6.2** Frugality Assertion | **Yes** | ✅ Pass | Contract tests assert zero mutations; integration tests assert 500-node cap |
| **Rule 6.3** Ephemeral Sandbox | **Yes** | ✅ Pass | All tests use in-memory FalkorDB; no persistent state |

**Post-design re-check**: All gates still pass. No violations requiring justification in Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/001-visual-graph-dashboard/
├── plan.md              # This file
├── research.md          # Phase 0 output ✅
├── data-model.md        # Phase 1 output ✅
├── quickstart.md        # Phase 1 output ✅
├── contracts/
│   └── dashboard-api.md # Phase 1 output ✅
└── tasks.md             # Phase 2 output (created by /speckit.tasks — not yet generated)
```

### Source Code (repository root)

```text
src/
├── dashboard/           # NEW — Python backend API for the dashboard
│   ├── __init__.py
│   ├── api.py           # FastAPI app; mounts StaticFiles + defines /api/graph and /health
│   ├── auth.py          # JWT decode; DashboardUser dependency; raises 401/403
│   ├── graph_service.py # DashboardGraphService — wraps src/graph/query.py; maps to response models
│   └── server.py        # uvicorn entrypoint on port 8080
├── graph/               # EXISTING — unchanged
├── mcp_server/          # EXISTING — unchanged
├── models/              # EXISTING — unchanged
└── utils/               # EXISTING — unchanged

dashboard/               # NEW — static frontend assets served by FastAPI StaticFiles
├── index.html           # Single-page app shell; loads Cytoscape.js from CDN
├── app.js               # Canvas render, node click / dim logic, filter panel, search, tooltips
└── style.css            # Layout; edge width/colour CSS variables for confidence_score encoding

tests/
├── unit/
│   └── dashboard/       # NEW
│       ├── test_auth.py             # JWT decode, missing claims → 401/403, expired → 401
│       └── test_graph_service.py   # Scope enforcement, business_name fallback, 500-node cap
├── integration/
│   ├── test_dashboard_api.py       # NEW — TestClient tests for /api/graph, /health; scope isolation
│   └── test_function_objects_e2e.py  # EXISTING
└── contract/
    └── test_dashboard_mutations.py  # NEW — assert zero WRITE Cypher ops from any dashboard route
```

**Structure Decision**: Option 2 (web application), adapted to the existing `src/` layout. Backend added as `src/dashboard/`; frontend static assets added as `dashboard/` at repo root. Existing modules (`src/graph/`, `src/mcp_server/`, `src/models/`) are untouched. No new top-level `backend/` or `frontend/` directories introduced — the existing single-project structure is extended.

## Complexity Tracking

> No constitution violations requiring justification. Table left empty per governance rules.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |
