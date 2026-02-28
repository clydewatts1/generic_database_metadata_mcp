# Feature Specification: Schema Health Dashboard Widget

**Feature Branch**: `001-schema-health-widget`  
**Created**: 2026-02-28  
**Status**: Draft  
**Input**: User description: "Build a Schema Health Dashboard Widget feature for the human viewport. This feature should aggregate the health_score of all (:MetaType) nodes (as defined in Rule 2.6) and display them in the existing Visual Web Dashboard. It must be read-only, strictly enforce Profile-Aware Scoping (Rule 5.2), and must bypass Semantic Compression (Rule 3.2) as permitted by the Human Viewport Exception (Rule 3.6)."

## Constitution Check

| Rule | Obligation | This Feature |
|------|-----------|--------------|
| Rule 2.6 | MetaType health_score is decremented on validation failure | Widget reads and surfaces these scores — no writes permitted |
| Rule 3.2 | Semantic compression MUST be used for LLM responses | N/A — dashboard is a human browser, not an LLM |
| Rule 3.6 | Human Viewport Exception — dashboard API is exempt from Rules 3.2 & 3.5 | ✅ Applies — widget serves full JSON to browser |
| Rule 4.4 | AI stigmergic actions carry `rationale_summary` and `created_by_prompt_hash` | Widget performs no AI actions; human audit path (Rule 5.7) applies instead |
| Rule 5.2 | Scoped visibility — only nodes within `domain_scope` returned | ✅ Enforced server-side on every widget query |
| Rule 5.6 | Dashboard Unified Security Layer — all dashboard routes MUST gate on JWT validation, scope injection, and audit write-through | ✅ Enforced at `health_router = APIRouter(dependencies=[Depends(unified_security)])` level — USL applied per R-003 |
| Rule 5.7 | Every human read via the dashboard generates an explicit audit log entry | ✅ Must be implemented; each widget data load writes an audit record |

> **Note on "Rule 4.6"**: Rule 4.6 is **RESERVED** in constitution v1.3.0 (gap-hold placeholder). No compliance obligation applies to this feature. The read-only constraint is structurally enforced under Rule 3.6 — no write routes or Cypher mutation paths exist.

> **Constitution Note — Rule 5.6 / existing `GET /api/graph` route**: Constitution v1.3.0 added Rule 5.6 (Dashboard Unified Security Layer) after the `GET /api/graph` route was already implemented in feature `001-visual-graph-dashboard`. That route is **not** currently protected by the USL. Retroactive USL application to `/api/graph` is deferred to a follow-up feature `002-usl-migration` and does not block this feature's constitution compliance.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — View MetaType Health Scores (Priority: P1)

As a data health analyst, I want to see a dedicated health score panel in the Visual Web Dashboard listing all (:MetaType) nodes within my domain scope, with their current `health_score` displayed as a numeric value, so that I can identify unhealthy schemas without having to query the MCP server directly.

**Why this priority**: This is the core MVP — without readable health scores in the viewport, all other stories have nothing to build on. It delivers the primary read capability that justifies the feature's existence.

**Independent Test**: Authenticate as a user with `domain_scope = Finance`, load the dashboard. The health panel renders a table/list containing every MetaType registered in the Finance domain, each showing its `name`, `type_category`, and `health_score`. Verifiable by seeding two MetaTypes (healthy and degraded) and asserting both appear with correct scores.

**Acceptance Scenarios**:

1. **Given** a user holds a valid JWT with `profile_id = analyst_1` and `domain_scope = Finance`, and two MetaTypes (`CustomerLoan: health_score=1.0` and `LoanProduct: health_score=0.3`) exist in Finance scope, **When** the user loads the health widget, **Then** both MetaTypes are listed with their correct `health_score` values and `type_category`.
2. **Given** a user's JWT has `domain_scope = Finance`, and a MetaType `GlobalSchema` exists in `domain_scope = Global` only, **When** the user loads the health widget, **Then** `GlobalSchema` does NOT appear in the response (Rule 5.2 enforcement).
3. **Given** no MetaTypes are registered in the user's domain scope, **When** the user loads the health widget, **Then** the widget displays an empty-state message (e.g., "No MetaTypes found in your domain") rather than an error or blank panel.
4. **Given** the user loads the health widget, **Then** exactly one audit log entry is written with `action_type = READ`, `profile_id = analyst_1`, `domain_scope = Finance`, and a UTC ISO-8601 timestamp (Rule 5.7).

---

### User Story 2 — Colour-Coded Health Indicators (Priority: P2)

As a data steward, I want each MetaType in the health panel to display a colour-coded visual indicator (green / amber / red) based on its `health_score`, so I can immediately identify MetaTypes that require healing without having to read raw numerical values.

**Why this priority**: Colour encoding transforms raw numbers into actionable at-a-glance insight. It depends entirely on US1 data being present, so P2 is correct.

**Independent Test**: Render the health widget with three seeded MetaTypes with scores 1.0, 0.65, and 0.2. Assert that the frontend assigns class/style `health-green` to the first, `health-amber` to the second, and `health-red` to the third.

**Acceptance Scenarios**:

1. **Given** a MetaType has `health_score >= 0.8`, **When** the health widget renders, **Then** its health indicator renders with the green state (`health-green`).
2. **Given** a MetaType has `health_score >= 0.5` and `health_score < 0.8`, **When** the health widget renders, **Then** its indicator renders amber (`health-amber`).
3. **Given** a MetaType has `health_score < 0.5`, **When** the health widget renders, **Then** its indicator renders red (`health-red`).
4. **Given** a MetaType has `health_score = 0.8` exactly (boundary), **When** the widget renders, **Then** it renders green (inclusive lower bound of green tier).
5. **Given** a MetaType has `health_score = 0.0`, **When** the widget renders, **Then** it renders red and a tooltip or sub-label reads "Schema critically degraded".

---

### User Story 3 — Manual Refresh Without Page Reload (Priority: P3)

As a data architect, I want a Refresh button in the health widget that re-fetches the latest MetaType health scores from the server without reloading the full dashboard page, so I can monitor schema health in near-real-time without losing my graph canvas state.

**Why this priority**: Useful for monitoring workflows but the widget delivers its core value even without refresh. Depends on US1 and US2.

**Independent Test**: Load the widget; update a MetaType's `health_score` in the database; click Refresh. Assert the widget displays the updated score without a full page reload (graph canvas remains mounted).

**Acceptance Scenarios**:

1. **Given** the health widget is loaded, **When** the user clicks "Refresh", **Then** a new `GET /api/health/meta-types` request is issued and the widget re-renders with fresh data.
2. **Given** the user clicks Refresh, **Then** a second audit log entry (distinct timestamp) is written for the re-fetch (each data load = one audit entry per Rule 5.7).
3. **Given** the user clicks Refresh while FalkorDB is degraded, **Then** the widget transitions to the degraded state (see US4) rather than silently showing stale data.

---

### User Story 4 — Degraded State When FalkorDB Is Unreachable (Priority: P4)

As any authenticated dashboard user, when FalkorDB is temporarily unavailable, I want the health widget to display a clear degraded-state placeholder message rather than an empty panel or a generic browser error, so I understand that the absence of data is a service issue and not a data issue.

**Why this priority**: Defensive UX is important but last priority — the core read flow must work first. Depends on US1's endpoint existing.

**Independent Test**: Mock the FalkorDB connection to be unreachable; load the widget. Assert HTTP 503 is returned by the API, and the browser renders a human-readable degraded message (not a stack trace, blank div, or JS error).

**Acceptance Scenarios**:

1. **Given** FalkorDB is unreachable, **When** the health widget data endpoint is called, **Then** the API returns HTTP 503 with a JSON body `{"status": "degraded", "message": "Schema health data temporarily unavailable"}`.
2. **Given** the widget receives a 503, **Then** the frontend renders a degraded-state UI element (e.g., amber banner: "Schema health data temporarily unavailable") instead of an empty list.
3. **Given** FalkorDB is unreachable, **Then** an audit log entry is still attempted; if the audit store is also unavailable, the 503 response body includes `"audit_status": "failed"` for transparency.

---

### Edge Cases

- No MetaTypes registered in the user's domain scope → empty-state message, not an error
- All MetaTypes have `health_score = 1.0` → all green, widget renders normally
- `health_score` at exact threshold boundaries: 0.0, 0.5, 0.8, 1.0 → each must map to the correct colour band (inclusive/exclusive boundaries defined in FR-003)
- JWT expires between page load and the Refresh action → widget must return HTTP 401 and prompt re-authentication, not silently display stale data
- FalkorDB unreachable at widget load → HTTP 503, degraded UI (US4)
- User attempts to submit a POST/PUT/PATCH/DELETE to any widget API endpoint → HTTP 405 Method Not Allowed (read-only enforcement)
- More than the `DASHBOARD_NODE_LIMIT` (500) MetaTypes in scope → widget must paginate or display the capped count and show a "Results truncated" notice
- A MetaType exists in multiple domain scopes (e.g., registered in both Finance and Global) → only the Finance-scoped instance appears to a Finance-scoped user (Rule 5.2)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST expose a dedicated read-only API endpoint (`GET /api/health/meta-types`) that returns all (:MetaType) nodes visible to the authenticated user's `domain_scope`, each record including `name`, `type_category`, and `health_score`.
- **FR-002**: The endpoint MUST be protected by the Unified Security Layer (Rule 5.6) — JWT validation (401), claims check (403), domain scope injection, and audit log write MUST occur on every request.
- **FR-003**: Health scores MUST be mapped to colour bands: `health_score >= 0.8` → **green**; `0.5 <= health_score < 0.8` → **amber**; `health_score < 0.5` → **red**. Boundary values are inclusive on the lower bound of each band.
- **FR-004**: The endpoint MUST be strictly read-only — no Cypher write operations (CREATE, SET, DELETE, MERGE) are permitted in any code path reachable from this endpoint. Violation is a compliance defect.
- **FR-005**: The endpoint MUST enforce Rule 5.2 (Scoped Visibility) — only MetaType nodes whose `domain_scope` matches the JWT's `domain_scope` claim are returned; cross-domain leakage is forbidden.
- **FR-006**: Every request to the endpoint MUST generate one audit log entry per Rule 5.7, containing: `profile_id`, `domain_scope`, `action_type = READ`, the count of MetaTypes returned, a UTC ISO-8601 timestamp, and `human_session_id`.
- **FR-007**: The audit log write MUST be atomic with the query response — if the audit entry cannot be persisted, the API MUST return an appropriate HTTP error and not return data (Rule 5.7 atomicity obligation).
- **FR-008**: The dashboard frontend MUST render the health panel as a sortable list/table showing MetaType name, type category, numeric health score, and colour-coded indicator.
- **FR-009**: The frontend MUST provide a Refresh button that re-fetches the data without a full page reload and without disrupting the graph canvas state.
- **FR-010**: If FalkorDB is unreachable, the endpoint MUST return HTTP 503 with `{"status": "degraded", "message": "Schema health data temporarily unavailable"}`; the frontend MUST display a human-readable degraded-state notice.
- **FR-011**: The endpoint MUST be exempt from TOON serialisation (Rule 3.6) — it MUST return full, uncompressed JSON to the browser.
- **FR-012**: If the number of in-scope MetaTypes exceeds `DASHBOARD_NODE_LIMIT`, the response MUST include a `truncated: true` flag and a `total_available` count, and the frontend MUST display a "Results truncated" notice.

### Key Entities

- **MetaTypeHealthRecord**: A read projection of a (:MetaType) node. Key attributes: `name` (string, unique within domain), `type_category` (string, e.g. `NODE` or `EDGE`), `health_score` (float, 0.0–1.0), `domain_scope` (string). Read from the graph via scoped Cypher query; never written by the dashboard.
- **HealthAuditEntry**: A structured audit record written per Rule 5.7 on every widget data load. Key attributes: `profile_id` (string), `domain_scope` (string), `action_type` (literal `READ`), `entity_summary` (count of MetaTypes returned), `timestamp` (UTC ISO-8601), `human_session_id` (string). MUST NOT carry `created_by_prompt_hash`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The health widget renders all in-scope MetaType health scores within **2 seconds** of page load under normal FalkorDB connectivity.
- **SC-002**: Colour encoding is accurate at all threshold boundaries — a test seeding MetaTypes at scores [`0.0`, `0.49`, `0.5`, `0.79`, `0.8`, `1.0`] must produce exactly `[red, red, amber, amber, green, green]`.
- **SC-003**: The widget API returns HTTP **401** for a missing/expired JWT, HTTP **403** for a valid JWT missing `domain_scope` or `profile_id`, and HTTP **405** for any non-GET HTTP method.
- **SC-004**: Zero MetaType records from outside the JWT's `domain_scope` appear in any response — verified by a contract test that seeds two domains and asserts strict isolation.
- **SC-005**: Each widget data load (initial + refresh) produces **exactly one** audit log entry — confirmed by querying the audit store before and after load and asserting a count delta of 1.
- **SC-006**: The widget API returns HTTP **503** with the prescribed degraded JSON body within 5 seconds when FalkorDB is unreachable, and the frontend renders the degraded-state notice.
- **SC-007**: A contract test asserts that no Cypher statement reachable from `GET /api/health/meta-types` contains the keywords `CREATE`, `SET`, `DELETE`, or `MERGE` (read-only enforcement).
- **SC-008**: The Refresh action completes and the panel re-renders with updated data in under **3 seconds** without a full page reload.
