# Tasks: Visual Web Dashboard

**Input**: Design documents from `specs/001-visual-graph-dashboard/`
**Prerequisites**: plan.md ✅ spec.md ✅ research.md ✅ data-model.md ✅ contracts/ ✅

**Tests**: Included — mandated by Constitution Rules 6.1, 6.2, 6.3 and SC-006 (zero-mutation assertion required by integration test).

**Organization**: Tasks grouped by user story for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (operates on different files, no incomplete dependencies)
- **[Story]**: User story label (US1–US4)

---

## Phase 1: Setup

**Purpose**: New directories, dependency, and project skeleton. All tasks parallelisable once T001 is done.

- [X] T001 Add `PyJWT` to `requirements.txt`
- [X] T002 [P] Create `src/dashboard/__init__.py` (empty package marker)
- [X] T003 [P] Create `dashboard/` directory with empty `index.html`, `app.js`, `style.css` placeholders at repo root
- [X] T004 [P] Create `tests/unit/dashboard/__init__.py` and `tests/contract/__init__.py` package markers

**Checkpoint**: Dependency declared; new package skeletons present; tests can begin discovering directories.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Pydantic response models, JWT auth dependency, and uvicorn entrypoint — blocking prerequisites for ALL user story phases.

**⚠️ CRITICAL**: No user story API or frontend work can begin until this phase is complete.

- [X] T005 Implement `GraphNodeResponse`, `GraphEdgeResponse`, `GraphPayloadResponse`, and `DashboardUser` Pydantic models in `src/dashboard/models.py` — per `data-model.md` field/validation spec
- [X] T006 Implement `src/dashboard/auth.py`: JWT decode via PyJWT (`HS256`); `get_current_user()` FastAPI dependency; raises `HTTP 401` for missing/expired token, `HTTP 403` for missing `profile_id`/`domain_scope` claims; reads secret from env var `DASHBOARD_JWT_SECRET`
- [X] T007 [P] Unit test JWT auth in `tests/unit/dashboard/test_auth.py`: valid token → `DashboardUser`; missing token → 401; expired → 401; missing claims → 403; `domain_scope` override in query params has no effect
- [X] T008 Implement `DashboardGraphService` in `src/dashboard/graph_service.py`: calls `src.graph.query.query_graph(domain_scope=user.domain_scope, profile_id=user.profile_id)`; maps `ObjectNode` → `GraphNodeResponse` (with `business_name` None-fallback); maps `StigmergicEdge` → `GraphEdgeResponse` (`is_stigmergic=True`, all fields); maps structural/flow edges → `GraphEdgeResponse` (`is_stigmergic=False`, stigmergic fields null); enforces 500-node cap with `truncated` flag; derives `meta_types` list from nodes
- [X] T009 [P] Unit test `DashboardGraphService` in `tests/unit/dashboard/test_graph_service.py`: scope filter passed through correctly; Finance user never receives Marketing-only nodes; 500-node cap sets `truncated=True`; `business_name=None` when absent; `confidence_score` clamped to [0.0, 1.0]; `meta_types` deduplicated
- [X] T010 Implement `src/dashboard/server.py`: `uvicorn` entrypoint; reads `DASHBOARD_PORT` (default `8080`); starts FastAPI app from `src/dashboard/api.py`
- [X] T011 Create minimal `src/dashboard/api.py`: instantiate FastAPI app; mount `dashboard/` as `StaticFiles` at `/`; include API router; add `GET /health` → `{"status": "ok"}`; no `/api/graph` route yet (added in Phase 3)

**Checkpoint**: Foundation complete — JWT auth works, response models validated, graph service wraps `query_graph()`, server starts. User story phases can now proceed.

---

## Phase 3: User Story 4 — Profile-Aware Scoped View (Priority: P1) 🎯 MVP Gate

**Goal**: Every API call is authenticated and returns only nodes within the user's permitted `domain_scope`. This is the Rule 5.2 security gate — nothing else can ship without it.

**Independent Test**: Start the dashboard server. Send `GET /api/graph` with a Finance-scoped JWT and confirm no Marketing-only nodes appear. Send the same request without a token and confirm HTTP 401. Confirm `domain_scope` query-param override is ignored.

- [X] T012 [US4] Implement `GET /api/graph` route in `src/dashboard/api.py`: inject `get_current_user()` dependency; call `DashboardGraphService.get_graph(user)`; return `GraphPayloadResponse`; no query-param scope override permitted; raises `HTTP 503` if graph engine unreachable
- [X] T013 [P] [US4] Contract test — zero-mutation assertion in `tests/contract/test_dashboard_mutations.py`: instrument FalkorDB connection; call `GET /api/graph` (and all other routes); assert no `CREATE`, `SET`, `MERGE`, or `DELETE` Cypher statement is issued during any request (SC-006, FR-001)
- [X] T014 [P] [US4] Integration test — scope isolation in `tests/integration/test_dashboard_api.py`: Finance JWT → nodes contain only `domain_scope IN ["Finance","Global"]`; Marketing JWT → nodes contain only `domain_scope IN ["Marketing","Global"]`; unauthenticated → 401; profile with no explicit scope → only `"Global"` nodes; missing claims → 403

**Checkpoint**: US4 independently testable and deployable. `GET /api/graph` returns correct scoped payload or 401/403. Zero mutations confirmed by contract test.

---

## Phase 4: User Story 1 — Explore the Metadata Graph Visually (Priority: P1) 🎯 MVP

**Goal**: User opens browser, sees interactive pan/zoom node-link canvas with labelled nodes. Clicking a node opens a side panel and dims non-neighbours.

**Independent Test**: Open `http://localhost:8080` in browser with a valid JWT, confirm graph canvas renders within 3 seconds, nodes have labels (`business_name` if set, else `label`), edges are visible, canvas is pannable and zoomable. Click a node, confirm side panel opens and non-neighbours are dimmed. Press Escape, confirm all nodes restore.

- [X] T015 [P] [US1] Write `dashboard/index.html`: HTML shell; `<script>` tag loading Cytoscape.js 3.x from CDN; `<link>` for `style.css`; JWT input/storage on first load; canvas `<div id="cy">`; side-panel `<div id="detail-panel">` (hidden by default); filter panel placeholder; search box placeholder; refresh button; legend placeholder; loads `app.js`
- [X] T016 [P] [US1] Write `dashboard/style.css`: full-height canvas layout; side-panel slide-in style; dimmed-node opacity; `.stigmergic` edge CSS variable stubs for `confidence_score` width/colour; legend box style; responsive layout for filter panel
- [X] T017 [US1] Implement `dashboard/app.js` — Part 1 (data fetch + canvas render): on page load, read JWT from storage; `fetch('/api/graph', {headers: {Authorization: 'Bearer ...'}})` → handle 401 (show login banner), 403 (show scope-error banner), 503 (show unavailable banner); on 200, call `renderGraph(payload)`; `renderGraph()` builds Cytoscape.js elements array from `nodes` + `edges`; apply `business_name` as primary label with `label` as subtitle when both present; initialise `cy` with `layout: {name: 'cose'}`; enable zoom/pan
- [X] T018 [US1] Implement `dashboard/app.js` — Part 2 (node click: side panel + 1-hop dim): `cy.on('tap', 'node', handler)`: open `#detail-panel` with Object Type, `domain_scope`, and `properties` key-value list; dim all non-1-hop-neighbour nodes via `.addClass('dimmed')`; `cy.on('tap', handler)` on background click → remove all `dimmed` classes, close panel; `keydown` Escape listener → same clear
- [X] T019 [P] [US1] Integration test append to `tests/integration/test_dashboard_api.py`: `GET /api/graph` returns valid `GraphPayloadResponse` with `node_count`, `truncated`, `scope`, `meta_types`; `node_count == len(nodes)`; all nodes have `id`, `label`, `meta_type_name`, `domain_scope`; `GET /health` returns `{"status": "ok"}`; response `Content-Type` header is `application/json`; response body contains no TOON compact-format sentinel keys (assert none of `_t`, `_k`, `_v` appear as top-level keys) (FR-010, C2)
- [X] T020 [P] [US1] Integration test — scatter plot `business_name` rendering: nodes with `business_name` set carry it in response; nodes without carry `null`; `label` always non-empty

**Checkpoint**: US1 independently testable. Browser renders pan/zoom graph. Node click dims neighbours and opens side panel. Escape/background click restores all nodes.

---

## Phase 5: User Story 2 — Distinguish Stigmergic Edges from Standard Edges (Priority: P2)

**Goal**: Stigmergic edges are visually distinct from structural edges, with `confidence_score` encoded as line thickness (and de-emphasised below 0.2). Edge hover tooltips show correct fields.

**Independent Test**: Load dashboard with a dataset containing both stigmergic (varying `confidence_score`) and structural edges. Without reading any tooltip, verify stigmergic edges look different from structural edges, and a `confidence_score=0.9` edge is visually heavier than a `confidence_score=0.1` edge. A `confidence_score < 0.2` edge should appear dashed or light-grey. Hover each edge type to confirm correct tooltip fields.

- [X] T021 [US2] Extend `dashboard/style.css`: define Cytoscape.js edge style for `is_stigmergic=true` nodes using `data(confidence_score)` mapped to `width` (range 1px–6px) and `line-color` (gradient muted→vivid); `confidence_score < 0.2` → `line-style: dashed`, `opacity: 0.4`; structural edges → fixed 1.5px solid grey; legend panel filled with visual swatches and text descriptions
- [X] T022 [US2] Implement `dashboard/app.js` — Part 3 (edge tooltips): `cy.on('mouseover', 'edge', handler)`: for `is_stigmergic=true` → show tooltip with `edge_type`, `confidence_score`, `rationale_summary`, `last_accessed`; for structural → show `edge_type`, source/target node names only; `cy.on('mouseout', 'edge')` → hide tooltip; tooltip `<div>` appended to body, positioned at mouse coords
- [X] T023 [P] [US2] Unit test `DashboardGraphService` — edge mapping in `tests/unit/dashboard/test_graph_service.py`: `StigmergicEdge` with `confidence_score=0.85` → `GraphEdgeResponse(is_stigmergic=True, confidence_score=0.85, ...)`; structural edge → `GraphEdgeResponse(is_stigmergic=False, confidence_score=None, rationale_summary=None, last_accessed=None)`; `confidence_score=1.5` → clamped to `1.0`; `confidence_score=-0.1` → clamped to `0.0`
- [X] T024 [P] [US2] Integration test append to `tests/integration/test_dashboard_api.py`: response includes `is_stigmergic` field on all edges; stigmergic edges have non-null `confidence_score`; structural edges have null `confidence_score`; `confidence_score` values all within [0.0, 1.0]

**Checkpoint**: US2 independently testable. Stigmergic vs structural edges visually distinct. Low-confidence edges de-emphasised. Tooltips show correct fields per edge type. Legend rendered.

---

## Phase 6: User Story 3 — Filter by Object Type or Business Name (Priority: P2)

**Goal**: User can select Object Types from the filter dropdown to restrict visible nodes; text search in `business_name` highlights matching nodes; both clear correctly.

**Independent Test**: Load dashboard with ≥ 3 Object Types. Select a single type in the filter — only nodes of that type and their direct edges remain visible. Clear filter — all nodes return. Type a `business_name` substring in search — matching nodes highlight. Clear search — all nodes restore. Filter matching zero nodes shows empty-state message.

- [X] T025 [US3] Implement `dashboard/app.js` — Part 4 (Object Type filter): populate `#filter-panel` `<select>` with `payload.meta_types` on graph load; `change` event → call `applyFilters()`; `applyFilters()`: if type(s) selected, hide all nodes whose `meta_type_name` not in selection via `.style('display','none')` and also hide edges whose source or target is hidden; clear → restore all via `.removeStyle('display')`; empty match → show `#empty-state` message
- [X] T026 [US3] Implement `dashboard/app.js` — Part 5 (`business_name` search): debounced `input` event on `#search-input`; case-insensitive `includes()` match against node `data.business_name`; non-matching nodes → `addClass('dimmed')`; matching nodes → `removeClass('dimmed')`; determine best match as the matching node with the highest direct edge count; call `cy.animate({center: {eles: bestMatchNode}, duration: 300})`; clear (empty input) → remove all `dimmed` classes and reset pan/zoom; max-50-match cap with `#match-count` notice when exceeded; nodes with `business_name=null` excluded from results
- [X] T027 [P] [US3] Extend `dashboard/index.html`: add `<select multiple id="type-filter">` populated by JS; add `<input id="search-input" type="text" placeholder="Search business name…">`; add `<span id="match-count">` notice area; add `<div id="empty-state">` for zero-match message
- [X] T028 [P] [US3] Integration test append to `tests/integration/test_dashboard_api.py`: `meta_types` in response is a non-empty deduplicated list of strings matching the `meta_type_name` values across all nodes; verify `business_name` null for nodes that have none; verify `business_name` set for nodes that have it

**Checkpoint**: US3 independently testable. Object Type filter restricts canvas. `business_name` search highlights/dims nodes. Both clear correctly. Zero-match empty state shown.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Refresh button, `truncated` banner, error states, empty graph state, 500-node cap display, final `GET /health` 503 pass-through, env-var documentation.

- [X] T029 [P] Implement refresh button handler in `dashboard/app.js`: `click` on `#refresh-btn` → re-fetch `GET /api/graph`, clear FilterState, re-render; show `#loading-spinner` during fetch
- [X] T030 [P] Add `truncated` banner logic in `dashboard/app.js`: if `payload.truncated === true`, show `#truncated-banner` with "Showing first 500 nodes — apply a filter to see more" notice
- [X] T031 [P] Add empty graph state in `dashboard/app.js`: if `payload.node_count === 0`, hide canvas, show `#empty-state-global` message "No nodes in your permitted scope"
- [X] T032 [P] Handle 503 from `GET /api/graph` in `dashboard/app.js`: show `#error-banner` "Graph engine unavailable — last view preserved"; do NOT blank the canvas (preserve last rendered state)
- [X] T033 [P] Update `GET /health` in `src/dashboard/api.py` to probe FalkorDB connection and return `{"status": "degraded", "detail": "Graph engine unavailable"}` with HTTP 503 when unreachable (per `contracts/dashboard-api.md`)
- [X] T034 [P] Add `DASHBOARD_JWT_SECRET`, `DASHBOARD_PORT`, `DASHBOARD_NODE_LIMIT`, `FALKORDB_HOST`, `FALKORDB_PORT` env-var loading in `src/dashboard/api.py` (or a shared `src/dashboard/config.py`); document default values inline; raise `RuntimeError` on startup if `DASHBOARD_JWT_SECRET` is absent (derived from FR-011 + operational security)
- [X] T035 [P] Performance test in `tests/unit/dashboard/test_performance.py`: build an in-memory fixture of 500 `GraphNodeResponse` + 2,000 `GraphEdgeResponse` objects; assert `DashboardGraphService` serialisation of the fixture completes in ≤ 1.5 seconds (SC-002 API-layer budget); assert client-side filter logic (Python simulation of Object Type filter over 500 nodes) completes in ≤ 50ms (SC-005 budget indicator); document that full end-to-end browser render time is validated manually (SC-001, SC-004 manual gates)

**Checkpoint**: Dashboard fully deployable. All error states handled. Refresh, truncation, empty state, and env config complete.

---

## Dependencies

```
Phase 1 (Setup)
  └── Phase 2 (Foundation: models, auth, graph_service, server, api skeleton)
        └── Phase 3 (US4: scoped GET /api/graph — Rule 5.2 gate) ──────────────────┐
              └── Phase 4 (US1: canvas render, node click, side panel)              │
                    └── Phase 5 (US2: edge differentiation, tooltips, legend)        │
                          └── Phase 6 (US3: filter panel, business_name search)      │
                                └── Phase 7 (Polish: refresh, truncation, errors)   │
                                                                                     │
              Contract test T013 (zero-mutations) can run from Phase 3 onward ───────┘
```

**Story isolation**:
- US4 (Phase 3) is independently deployable as MVP — auth + scoped API response only.
- US1 (Phase 4) requires Phase 3 backend. Frontend can be developed in parallel with Phase 3 API work.
- US2 (Phase 5) and US3 (Phase 6) are additive to `app.js`/`style.css` — do not block each other.

## Parallel Execution Examples

**Phase 2** — after T005 (models):
```
T006 (auth.py) ──────────┐
T007 (test_auth.py) ─────┤
T008 (graph_service.py) ─┤── all parallel once T005 complete
T010 (server.py) ────────┘
```

**Phase 4** — after T012 (API route):
```
T015 (index.html) ──┐
T016 (style.css) ───┤── all parallel
T019 (tests) ───────┤
T020 (tests) ────────┘
T017 (app.js Part 1) ── then T018 (app.js Part 2) sequential within app.js
```

**Phase 7** — all T029–T034 fully parallel (different files or independent branches in same file).

## Implementation Strategy

**MVP scope** (minimum shippable increment): **Phase 1 + Phase 2 + Phase 3**

> A scoped JSON API (`GET /api/graph`) with JWT auth and zero-mutation contract test. Proves Rule 5.2 compliance and the read-only guarantee before any frontend work. Can be validated by calling the endpoint directly (e.g., with `curl` or Postman).

**Increment 2**: + Phase 4 (US1) — full browser graph view.

**Increment 3**: + Phase 5 (US2) + Phase 6 (US3) — edge differentiation and filtering. Both can ship together or separately.

**Final**: + Phase 7 (Polish).

## Summary

| Metric | Value |
|--------|-------|
| Total tasks | 35 (T001–T035) |
| Phase 1 — Setup | 4 tasks |
| Phase 2 — Foundation | 7 tasks |
| Phase 3 — US4 Scoped View (P1) | 3 tasks |
| Phase 4 — US1 Graph Exploration (P1) | 6 tasks |
| Phase 5 — US2 Edge Differentiation (P2) | 4 tasks |
| Phase 6 — US3 Filter & Search (P2) | 4 tasks |
| Phase 7 — Polish | 7 tasks |
| Tasks with [P] (parallelisable) | 22 |
| New Python files | 6 (`auth.py`, `models.py`, `graph_service.py`, `api.py`, `server.py`, `config.py`) |
| New frontend files | 3 (`index.html`, `app.js`, `style.css`) |
| New test files | 5 (`test_auth.py`, `test_graph_service.py`, `test_dashboard_api.py`, `test_dashboard_mutations.py`, `test_performance.py`) |
| Suggested MVP scope | Phases 1–3 (US4 only — 14 tasks) |
