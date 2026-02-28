# Tasks: Schema Health Dashboard Widget

**Feature**: `001-schema-health-widget` | **Branch**: `001-schema-health-widget` | **Generated**: 2026-02-28  
**Input**: `specs/001-schema-health-widget/plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/api-health-meta-types.md`

---

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no incomplete-task dependencies)
- **[Story]**: Which user story this task belongs to (US1–US4)
- File paths are absolute from repository root

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: One-time infrastructure preparation. No source changes — creates bootstrap tooling only.

- [X] T001 Create `scripts/bootstrap_indices.py` that connects to FalkorDB and executes `CREATE INDEX FOR (a:HumanAuditLog) ON (a.profile_id)` and `CREATE INDEX FOR (a:HumanAuditLog) ON (a.timestamp)` (data-model.md §HumanAuditEntry; required before USL audit writes under load)

**Checkpoint**: Index script exists and runs without error against a live FalkorDB instance.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core components that ALL user stories depend on — Pydantic response models and the Unified Security Layer. No user story phase can begin until this phase is complete.

**⚠️ CRITICAL**: T002 and T003 are preconditions for every Phase 3–6 task.

- [X] T002 Add `MetaTypeHealthResponse` (id, name, type_category, health_score clamped [0.0–1.0], health_band computed, domain_scope) and `HealthPayloadResponse` (items, total_available, truncated, audit_status) Pydantic models to `src/dashboard/models.py`
- [X] T003 [P] Create `src/dashboard/security.py` implementing: `derive_session_id(request, credentials) → str` (R-002: `"tok:{sha256[:8]}"` / `"ip:{client_ip}"`); `AuditService.write_audit(conn, profile_id, domain_scope, endpoint_path, session_id) → None` (creates `(:HumanAuditLog)` node, raises `HTTPException(503)` on failure); `unified_security(request, credentials, user) → DashboardUser` FastAPI dependency (R-003: sequential JWT→401, claims→403, scope injection, audit write — Rule 5.6)

**Checkpoint**: `src/dashboard/models.py` exports both new Pydantic models. `src/dashboard/security.py` exports `unified_security` and `AuditService`. Existing imports unchanged. `python -c "from src.dashboard.security import unified_security"` succeeds (no runtime errors).

---

## Phase 3: User Story 1 — View MetaType Health Scores (Priority: P1) 🎯 MVP

**Goal**: Deliver a functional read-only API endpoint (`GET /api/health/meta-types`) protected by the USL, plus a basic browser panel listing each in-scope MetaType's name, type category, and numeric health score.

**Independent Test**: Authenticate as `profile_id=analyst_1, domain_scope=Finance`. Seed two MetaTypes (`CustomerLoan: 1.0`, `LoanProduct: 0.3`) in Finance scope and one in HR scope. Load the health widget. Assert both Finance MetaTypes appear with correct scores, HR MetaType absent, and exactly one `(:HumanAuditLog)` node written.

### Tests for User Story 1

- [X] T004 [P] [US1] Create `tests/unit/dashboard/test_unified_security.py`: unit tests for `unified_security` dependency (missing token → 401 + `WWW-Authenticate: Bearer`; valid JWT missing `domain_scope` → 403; valid JWT missing `profile_id` → 403; valid JWT full claims → calls `AuditService.write_audit` exactly once; `write_audit` FalkorDB failure → 503; `derive_session_id` with credentials → `"tok:{8-char-hex}"`; `derive_session_id` without credentials + X-Forwarded-For → `"ip:{ip}"`) — covers SC-003, SC-005
- [X] T005 [P] [US1] Create `tests/contract/test_health_mutations.py`: static analysis contract test asserting that no Cypher string reachable from `src/dashboard/health_service.py` and `src/dashboard/health_router.py` contains the keywords `CREATE`, `SET`, `DELETE`, or `MERGE` (case-insensitive, whole-word) — covers SC-007

### Implementation for User Story 1

- [X] T006 [US1] Create `src/dashboard/health_service.py` implementing `HealthService` class: `get_health_payload(user: DashboardUser) → HealthPayloadResponse` — calls `list_meta_types(user.domain_scope)` (reusing `src.graph.ontology`), builds `MetaTypeHealthResponse` items (health_band computed from health_score per FR-003), applies `DASHBOARD_NODE_LIMIT` cap (env var, default 500), sets `truncated` and `total_available`, wraps FalkorDB `ConnectionError` / `Exception` as `HTTPException(503, detail={"status": "degraded", "message": "Schema health data temporarily unavailable"})` — covers FR-001, FR-004, FR-005, FR-007, FR-010, FR-011, FR-012
- [X] T007 [US1] Create `src/dashboard/health_router.py`: define `health_router = APIRouter(prefix="/api/health", tags=["health"])`; add `GET /meta-types` route that injects `DashboardUser` (from existing `get_current_user`) and `HealthService`, calls `health_service.get_health_payload(user)`, returns `HealthPayloadResponse` — covers FR-001, FR-002, FR-011
- [X] T008 [US1] Modify `src/dashboard/api.py` `_register_routes()`: import `health_router` from `src.dashboard.health_router` and `unified_security` from `src.dashboard.security`; register `app.include_router(health_router, dependencies=[Depends(unified_security)])` — ensures USL applied to all health routes per Rule 5.6 (R-003)
- [X] T009 [P] [US1] Create `tests/unit/dashboard/test_health_service.py`: unit tests for `HealthService.get_health_payload()` using monkeypatched `list_meta_types` — in-scope MetaTypes returned; out-of-scope MetaTypes filtered; empty domain → empty `items`; cap=2 with 3 MetaTypes → `truncated=True`, `total_available=3`; `list_meta_types` raises exception → `HTTPException(503)` raised — covers FR-005, FR-007, FR-010, FR-012, SC-004
- [X] T010 [P] [US1] Extend `tests/integration/test_dashboard_api.py` with health endpoint tests: `GET /api/health/meta-types` with valid JWT → 200 + correct items; missing JWT → 401; valid JWT no `domain_scope` claim → 403; `POST /api/health/meta-types` → 405; empty domain → 200 with `items=[]`; two-domain isolation → Finance user sees only Finance MetaTypes (SC-004); audit node count delta = 1 per request (SC-005) — covers SC-001, SC-003, SC-004, SC-005
- [X] T011 [US1] Modify `dashboard/index.html`: add health widget `<section id="health-panel">` with `<h2>Schema Health</h2>`, `<div id="health-empty-state" hidden>No MetaTypes found in your domain</div>`, `<table id="health-table"><thead>` (Name / Type / Health Score columns) `</thead><tbody id="health-tbody"></tbody></table>`, placeholder `<div id="health-loading">Loading…</div>` — covers FR-008
- [X] T012 [US1] Modify `dashboard/app.js`: add `async function fetchHealthData()` — calls `GET /api/health/meta-types` with Bearer token, shows `#health-loading` during fetch, on success populates `#health-tbody` with one `<tr>` per item (td: name, type_category, health_score.toFixed(2)), toggles `#health-empty-state` when `items.length === 0`, calls `fetchHealthData()` on `DOMContentLoaded` — covers FR-008

**Checkpoint**: `GET /api/health/meta-types` returns 200 with correct scoped payload. JWT missing → 401. Claims missing → 403. POST → 405. Browser panel renders name/type/score table. Audit node written per request. All Phase 3 unit + integration tests pass.

---

## Phase 4: User Story 2 — Colour-Coded Health Indicators (Priority: P2)

**Goal**: Each MetaType row in the health panel displays a colour-coded indicator using the `health_band` field already present in the API response (`"green"` / `"amber"` / `"red"`).

**Independent Test**: Seed MetaTypes with scores `[0.0, 0.49, 0.5, 0.79, 0.8, 1.0]`. Load the health widget. Assert rendered `<tr>` elements carry CSS class `health-red`, `health-red`, `health-amber`, `health-amber`, `health-green`, `health-green` respectively.

### Tests for User Story 2

- [X] T013 [P] [US2] Create `tests/unit/dashboard/test_health_service.py` colour band section (append to file from T009): parametrized tests asserting `health_band` values at boundary scores `0.0→"red"`, `0.49→"red"`, `0.5→"amber"`, `0.79→"amber"`, `0.8→"green"`, `1.0→"green"` (inclusive lower-bound thresholds per FR-003) — covers SC-002

### Implementation for User Story 2

- [X] T014 [P] [US2] Modify `dashboard/style.css`: add `.health-indicator` base class (inline-block, 12px×12px circle); `.health-green { background-color: #28a745; }`, `.health-amber { background-color: #ffc107; }`, `.health-red { background-color: #dc3545; }` — covers FR-008
- [X] T015 [US2] Modify `dashboard/app.js` render function: in each `<tr>`, prepend a `<td><span class="health-indicator ${item.health_band}"></span></td>` using `item.health_band` directly from API response; add tooltip `title="Score: ${item.health_score}"` to the span; for `health_score === 0.0` add `title="Schema critically degraded"` — covers FR-008, US2 Acceptance Scenario 5

**Checkpoint**: All six boundary scores render correct colour classes. `health_score = 0.0` indicator carries "Schema critically degraded" tooltip. SC-002 unit tests pass.

---

## Phase 5: User Story 3 — Manual Refresh Without Page Reload (Priority: P3)

**Goal**: A Refresh button in the health panel re-fetches `GET /api/health/meta-types` and re-renders the widget panel without triggering a full page reload or disturbing the Cytoscape.js graph canvas.

**Independent Test**: Load the widget (initial fetch completes). Update a MetaType's health_score in the DB. Click Refresh. Assert: only the health panel re-renders; Cytoscape canvas element remains mounted (no detach/re-attach); the widget shows the updated score; a second distinct audit log entry is written.

### Tests for User Story 3

- [X] T016 [P] [US3] Extend `tests/integration/test_dashboard_api.py`: two sequential `GET /api/health/meta-types` requests with the same valid JWT; assert both return 200 and audit node count delta = 2 total (each request = one audit entry per Rule 5.7) — covers SC-005, SC-008

### Implementation for User Story 3

- [X] T017 [US3] Modify `dashboard/index.html`: add `<button id="health-refresh-btn" type="button">Refresh</button>` inside `<section id="health-panel">`, adjacent to the panel heading — covers FR-009
- [X] T018 [US3] Modify `dashboard/app.js`: attach `document.getElementById('health-refresh-btn').addEventListener('click', fetchHealthData)`; inside `fetchHealthData` disable the button and set `textContent = 'Refreshing…'` on start, restore on completion (success or error) — covers FR-009; ensure graph canvas `document.getElementById('cy')` is never cleared or re-mounted during fetch

**Checkpoint**: Refresh button visible on widget. Clicking it invokes a new `GET /api/health/meta-types` request. Panel re-renders with fresh data. Cytoscape canvas unmolested. Two sequential requests produce two audit entries.

---

## Phase 6: User Story 4 — Degraded State When FalkorDB Is Unreachable (Priority: P4)

**Goal**: When FalkorDB is unreachable, the API returns HTTP 503 with the prescribed JSON body and the browser renders a human-readable degraded-state notice — never a blank div, stack trace, or JS console error.

**Independent Test**: Monkeypatch `list_meta_types` to raise `ConnectionError`. Call `GET /api/health/meta-types`. Assert HTTP 503 with `{"status": "degraded", "message": "Schema health data temporarily unavailable"}`. Assert `audit_status: "failed"` when the audit write also fails. Assert browser renders amber degraded banner.

### Tests for User Story 4

- [X] T019 [P] [US4] Extend `tests/integration/test_dashboard_api.py`: mock `HealthService.get_health_payload` to raise `HTTPException(503)`; assert response status = 503 and body = `{"status": "degraded", "message": "Schema health data temporarily unavailable"}`; assert response within 5 seconds (SC-006); mock `AuditService.write_audit` to raise exception → assert 503 body includes `audit_status: "failed"` — covers SC-006, FR-010

### Implementation for User Story 4

- [X] T020 [US4] Modify `src/dashboard/health_service.py` `get_health_payload()`: ensure `try/except` block wraps ALL FalkorDB calls (audit write in `AuditService` already raises 503; add explicit `except (ConnectionError, Exception) as e: raise HTTPException(status_code=503, detail={"status": "degraded", "message": "Schema health data temporarily unavailable"})` around `list_meta_types()` call); if audit write fails before data query, `audit_status` in response is not reached — 503 is raised; if data query fails post-audit, audit node is retained — covers FR-007, FR-010, US4
- [X] T021 [P] [US4] Modify `dashboard/app.js` `fetchHealthData()`: in the `catch` block and `response.ok === false` (status 503) branch: clear `#health-tbody`, hide the table, show a `<div id="health-degraded-banner" class="degraded-banner">Schema health data temporarily unavailable</div>` inside `#health-panel`; on successful re-fetch, remove the banner and restore the table — covers FR-010

**Checkpoint**: Mocked FalkorDB failure → HTTP 503 within 5 seconds. Browser renders degraded banner. No JS uncaught exceptions. SC-006 integration test passes.

---

## Final Phase: Polish & Cross-Cutting Concerns

**Purpose**: Completeness checks, truncation notice, and contract test housekeeping.

- [X] T022 [P] Modify `tests/contract/test_dashboard_mutations.py`: add `/api/health/meta-types` to the read-only routes allowlist; assert that the route appears in the app's OpenAPI spec as `GET` only (no other methods registered)
- [X] T023 [P] Modify `dashboard/index.html`: add `<p id="health-truncated-notice" hidden>Results truncated — showing first <span id="health-cap"></span> of <span id="health-total"></span> MetaTypes</p>` inside `#health-panel` below the table — covers FR-012
- [X] T024 [P] Modify `dashboard/app.js` render function: if `data.truncated === true`, set `#health-cap` to `data.items.length`, `#health-total` to `data.total_available`, and `removeAttribute('hidden')` on `#health-truncated-notice`; if `false`, set `hidden` — covers FR-012, SC-001

**Checkpoint**: All 24 tasks complete. `pytest` suite passes (target: ≥58 existing + new tests). Constitution gates all green. Feature branch ready for `/speckit.analyze` validation then PR.

---

## Dependencies (Story Completion Order)

```
Phase 1: Setup
    └── Phase 2: Foundational (T002, T003)
            ├── Phase 3: US1 (T004–T012)  [MVP — can stop here]
            │       ├── Phase 4: US2 (T013–T015)
            │       │       └── Phase 5: US3 (T016–T018)
            │       │               └── Final Phase: Polish (T022–T024)
            │       └── Phase 6: US4 (T019–T021)
            │               └── Final Phase: Polish (T022–T024)
            └── (Final Phase: Polish also requires US1+US4)
```

**Strict block**: Phase 2 (T002, T003) must be complete before any Phase 3 task begins.  
**US1 gates all other stories**: US2, US3, US4 all require the health endpoint and render function from US1.  
**US2 and US4 are independent of each other** (different files; both depend only on US1).  
**US3 depends on US2** (refresh re-renders with colour bands; both `fetchHealthData` and CSS classes must exist).

---

## Parallel Execution Examples

### Parallel within Phase 2
```
Run simultaneously:
  T002 → src/dashboard/models.py (Pydantic models)
  T003 → src/dashboard/security.py (USL + AuditService)
```

### Parallel within Phase 3 (US1)
```
After T006 (health_service.py) and T007 (health_router.py) complete:
  T008 → api.py registration   [blocks on T006, T007]
  T009 → test_health_service.py test file   [can start with T006]
  T010 → test_dashboard_api.py extension    [can start with T007, T008]
  T004 → test_unified_security.py           [can start with T003]
  T005 → test_health_mutations.py           [can start with T006, T007]
  T011 → index.html                         [independent — no backend dependency]
  T012 → app.js fetchHealthData()           [independent from T011]
```

### Parallel within Phase 4 (US2)
```
T013 → test colour bands (append to test_health_service.py — independent)
T014 → style.css CSS classes (independent)
T015 → app.js colour class assignment (depends on T014 — needs CSS to exist)
```

### Parallel within Final Phase
```
T022, T023, T024 are all independent (different files).
```

---

## Implementation Strategy

1. **Deliver MVP with Phase 1–3 only** — after T012, `GET /api/health/meta-types` is live with USL, scoped data, audit logging, and a basic browser panel. All P1 acceptance scenarios satisfied.
2. **Layer US2 next** (≤3 tasks) — colour bands require only CSS + a one-line class assignment.
3. **Add US3 Refresh** — two simple frontend tasks once the fetch function exists.
4. **Add US4 degraded state** — the server-side 503 path is already sketched in T006; US4 adds defensive handling and frontend notification.
5. **Polish last** — truncation notice and contract test housekeeping.

**TDD Note**: Test tasks (T004, T005, T009, T010, T013, T016, T019) are marked with `[P]` where file independence permits. Write and run each test so it **fails** before writing the corresponding implementation task. See `specs/001-schema-health-widget/quickstart.md` for JWT generation and FalkorDB seeding commands.

---

## Summary

| Phase | Story | Tasks | Parallelisable | Independent Test |
|-------|-------|-------|---------------|-----------------|
| Phase 1: Setup | — | T001 | — | Script runs against FalkorDB |
| Phase 2: Foundational | — | T002–T003 | T002 ∥ T003 | Both modules import without error |
| Phase 3: US1 (P1) | US1 | T004–T012 | T004, T005, T009, T010, T011, T012 | 200 response, scoped data, 1 audit entry |
| Phase 4: US2 (P2) | US2 | T013–T015 | T013, T014 | Boundary colours correct (SC-002) |
| Phase 5: US3 (P3) | US3 | T016–T018 | T016 | Refresh → fresh data, 2 audit entries |
| Phase 6: US4 (P4) | US4 | T019–T021 | T019, T021 | 503 + degraded banner (SC-006) |
| Polish | — | T022–T024 | T022, T023, T024 | All tests green, contract allowlist updated |

**Total tasks**: 24 (T001–T024)  
**Total per story**: US1=9, US2=3, US3=3, US4=3, Setup/Foundational/Polish=6  
**Parallel opportunities**: 15 of 24 tasks carry `[P]`  
**Suggested MVP scope**: Phases 1–3 (T001–T012) — delivers US1 fully with USL, audit, and browser panel
