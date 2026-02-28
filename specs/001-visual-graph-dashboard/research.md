# Research: Visual Web Dashboard — Phase 0 Findings

**Branch**: `001-visual-graph-dashboard`
**Date**: 2026-02-28
**Status**: Complete — all NEEDS CLARIFICATION resolved

---

## 1. Backend API Framework

**Decision**: FastAPI  
**Rationale**: `uvicorn` is already in `requirements.txt` and the project already runs a FastAPI-compatible ASGI stack for the MCP SSE server. FastAPI adds zero net-new runtime dependencies, provides built-in OpenAPI docs, and its `Depends()` injection model is the cleanest way to enforce JWT auth on every route. Middleware and `StaticFiles` mounts allow the dashboard HTML/JS to be served from the same process without a separate HTTP server.  
**Alternatives considered**:
- Flask — would work, but introduces a second web framework when FastAPI/uvicorn is already present.
- Starlette directly — FastAPI is a thin Starlette wrapper; using FastAPI is strictly additive.
- Django — heavyweight, incompatible with the project's ultra-light philosophy.

---

## 2. Graph Rendering Library (Frontend)

**Decision**: Cytoscape.js (CDN-hosted, no build pipeline)  
**Rationale**: Cytoscape.js is purpose-built for node-link diagrams with interaction primitives that map directly to the spec requirements: `cy.on('tap', 'node', ...)` for click-to-select, `ele.addClass('dimmed')` for neighbour highlighting, and edge `width`/`line-color` style mappings for `confidence_score` visual encoding. It handles pan/zoom natively with no extra work. Crucially, because it is loaded via CDN `<script>` tag, the frontend requires no Node.js, no npm, no build step — keeping the dashboard consistent with the project's "no unnecessary complexity" posture.  
**Alternatives considered**:
- D3.js — more expressive but requires significant custom code for node-link layouts, zoom, and interaction. Cytoscape.js provides all required primitives out of the box.
- Sigma.js — lighter but limited styling API; `confidence_score` → line width mapping requires patching.
- vis.js — feature-complete but large bundle size; CDN size is ~800KB vs Cytoscape.js ~200KB minified.

---

## 3. JWT Authentication Library (Python)

**Decision**: PyJWT (`pip install PyJWT`)  
**Rationale**: PyJWT is the de facto standard for stateless JWT decode/verify in Python. It handles RS256 and HS256, raises typed exceptions for expiry and signature failures, and requires no external service. For this feature the JWT carries `profile_id` and `domain_scope` claims; PyJWT's `jwt.decode()` returns them as a plain dict — zero boilerplate to extract scoping values. No session store is required (`profile_id` and `domain_scope` are read directly from the token on every request).  
**Alternatives considered**:
- `python-jose` — supports JOSE standard broadly but is heavier and has had CVEs. PyJWT is narrowly scoped and actively maintained.
- `authlib` — OAuth2/OIDC-focused; overkill for a pre-issued JWT bearer token scheme.

---

## 4. Static File Serving Strategy

**Decision**: FastAPI `StaticFiles` mount for `dashboard/` directory  
**Rationale**: The entire frontend is three files (`index.html`, `app.js`, `style.css`). Mounting `dashboard/` as static files at `/` means the dashboard API process serves both the HTML client and the JSON API endpoints from a single `uvicorn` process on a single dedicated port (default: 8080, separate from MCP's 8000). No Nginx, no CDN configuration, no Docker layer changes.  
**Alternatives considered**:
- Separate HTTP server (e.g., Python `http.server`) — would require a second process and CORS config.
- Embedding HTML as strings in Python — unmanageable for anything beyond a trivial prototype.

---

## 5. Graph Query Integration Pattern

**Decision**: Wrap `src/graph/query.py::query_graph()` in a new `DashboardGraphService` class  
**Rationale**: `query_graph(*, domain_scope, profile_id)` already enforces Rule 5.2 scoping via `WHERE node.domain_scope IN [$domain_scope, "Global"]`. The dashboard backend must not bypass this — it calls `query_graph()` directly and maps the result to `GraphNode` / `GraphEdge` response models. This means Rule 5.2 compliance is inherited structurally rather than requiring the dashboard to re-implement scope guards.  
**Alternatives considered**:
- Direct FalkorDB Cypher from the dashboard API — would duplicate scope-filter logic, creating a second place to maintain correctness.
- Calling the MCP server as an intermediary — MCP tools use TOON serialisation (Rule 3.5); adding a de-TOON step purely to re-serialise to JSON would be wasteful and fragile.

---

## 6. Dashboard Port Strategy

**Decision**: Dashboard API on port `8080`; MCP SSE server stays on port `8000`  
**Rationale**: FR-009 requires process separation. Port 8080 is the conventional secondary HTTP port and avoids conflicts with both the MCP server (8000) and common local services. Both servers can be started independently with no shared socket.

---

## 7. Test Strategy for Dashboard

**Decision**: Three test layers — unit (auth + graph_service), integration (API endpoints with TestClient), contract (zero-mutation assertion)  
**Rationale**:
- **Unit**: `tests/unit/dashboard/` — mock `query_graph()`, test JWT validation, scope enforcement, `business_name` fallback to `label`.
- **Integration**: Extend `tests/integration/` — FastAPI `TestClient` tests that assert scoped response payloads and HTTP 401/403 responses.
- **Contract**: `tests/contract/` — assert no Cypher `CREATE`, `SET`, `DELETE`, or `MERGE` is ever issued by any dashboard route handler (satisfies SC-006 / FR-001).
- All tests use ephemeral in-memory FalkorDB (Rule 6.3). No persistent graph state in tests.

---

## Summary Table

| Unknown | Decision | Key Dependency Added |
|---------|----------|----------------------|
| Backend framework | FastAPI | None (uvicorn already present) |
| Graph rendering | Cytoscape.js via CDN | None (CDN only, no npm) |
| JWT library | PyJWT | `PyJWT` pip package |
| Static serving | FastAPI `StaticFiles` | None |
| Graph query integration | Wrap `query_graph()` | None |
| Dashboard port | 8080 | None |
| Test strategy | Unit + integration + contract | None |
