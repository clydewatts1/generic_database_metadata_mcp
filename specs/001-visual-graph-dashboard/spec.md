# Feature Specification: Visual Web Dashboard for Stigmergic Metadata Graph

**Feature Branch**: `001-visual-graph-dashboard`
**Created**: 2026-02-28
**Status**: Draft
**Input**: User description: "Build a lightweight Visual Web Dashboard for the Stigmergic Metadata Server"

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Explore the Metadata Graph Visually (Priority: P1)

As a human user, I want to open a browser and see the metadata graph rendered as an interactive node-link diagram, so that I can understand the shape of my organisation's metadata landscape without writing Cypher queries.

**Why this priority**: This is the core deliverable — no other story has value without a visible, navigable graph. It is the minimum viable product on its own.

**Independent Test**: Open the dashboard URL in a browser without configuring any filters. The graph must render within 3 seconds, display nodes as labelled circles, display edges as connecting lines, and allow the user to pan and zoom the canvas. No MCP tools or query language knowledge is required.

**Acceptance Scenarios**:

1. **Given** a populated metadata graph and a logged-in user, **When** the dashboard loads, **Then** the graph canvas renders all nodes in the user's permitted scope within 3 seconds.
2. **Given** a rendered graph, **When** the user clicks a node, **Then** a side-panel opens showing the node's Object Type, domain scope, and key properties, AND all nodes that are not direct 1-hop neighbours of the selected node are dimmed on the canvas so the immediate connections are visually prominent.
3. **Given** a node is selected (side panel open, neighbours highlighted), **When** the user clicks the canvas background or presses Escape, **Then** the dimming is cleared and all nodes return to full opacity.
4. **Given** a rendered graph, **When** the user scrolls or drag-pans, **Then** the canvas responds smoothly and node labels remain readable.
5. **Given** the dashboard is running, **When** the user opens a second browser tab for the same graph, **Then** both tabs show the same scoped view independently.

---

### User Story 2 — Distinguish Stigmergic Edges from Standard Edges (Priority: P2)

As a human analyst, I want the graph to visually differentiate between standard structural edges and stigmergic confidence-weighted edges, including the ability to read the relative confidence score at a glance, so that I can identify well-established versus speculative semantic connections in the graph.

**Why this priority**: The stigmergic nature of the graph is its primary differentiator. Without this visual distinction, the dashboard is no different from a generic graph viewer. It must be delivered early to be useful for validation sessions.

**Independent Test**: Load the dashboard with a dataset that contains both structural edges (e.g., `[:CONTAINS]`) and stigmergic edges (e.g., `[:RELATES_TO]` with varying `confidence_score`). Verify without reading any tooltip that stigmergic edges are visually distinct from structural edges, and that a high-confidence edge is visually "heavier" or "brighter" than a low-confidence edge.

**Acceptance Scenarios**:

1. **Given** a graph with structural and stigmergic edges, **When** the canvas renders, **Then** stigmergic edges are rendered with variable visual weight (e.g., line thickness or colour gradient) proportional to their `confidence_score`.
2. **Given** a rendered graph, **When** the user hovers over a stigmergic edge, **Then** a tooltip shows the `edge_type`, `confidence_score` (0.0–1.0), `rationale_summary`, and `last_accessed` timestamp.
3. **Given** a rendered graph, **When** the user hovers over a structural edge, **Then** a tooltip shows the `edge_type` and the source/target node names, with no `confidence_score` displayed.
4. **Given** a graph with a stigmergic edge whose `confidence_score` is below 0.2, **When** the canvas renders, **Then** that edge is visually de-emphasised (e.g., dashed or light grey) to signal low confidence.

---

### User Story 3 — Filter the Graph by Object Type or Business Name (Priority: P2)

As a human analyst, I want to narrow the graph view to a specific Object Type (e.g., "Dashboard", "Table") or to nodes matching a `business_name` string, so that I can focus on a relevant slice of the metadata without visual clutter.

**Why this priority**: Real graphs can contain hundreds of nodes. Without filtering, the dashboard is illegible at scale. This story directly unlocks practical, day-to-day usefulness.

**Independent Test**: Load the dashboard with a dataset containing at least three Object Types. Select a single Object Type from the filter panel and verify that only nodes of that type and their direct edges are retained on the canvas. Clear the filter and verify all permitted nodes return.

**Acceptance Scenarios**:

1. **Given** a rendered graph, **When** the user selects one or more Object Types from the filter panel, **Then** the canvas updates to show only nodes matching those types and their direct connections.
2. **Given** a rendered graph, **When** the user types a string into the search box, **Then** nodes whose `business_name` property contains that string (case-insensitive) are highlighted (all non-matching nodes dimmed) and the canvas re-centres on the best match, defined as the matching node with the highest number of direct edges.
3. **Given** an active filter, **When** the user clears the filter, **Then** all scoped nodes are restored to the canvas in under 1 second.
4. **Given** a filter that matches zero nodes in the user's scope, **When** the user applies it, **Then** the canvas displays an empty state message rather than an error.

---

### User Story 4 — Profile-Aware Scoped View (Priority: P1)

As an administrator, I want to ensure that each user only sees nodes and edges within their permitted domain scope when they open the dashboard, so that cross-domain data is never inadvertently exposed through the visual interface.

**Why this priority**: Scoped visibility (Rule 5.2) is a non-negotiable security requirement shared with the rest of the system. It must be in place from the first deployment and cannot be deferred.

**Independent Test**: Configure two user profiles — one scoped to "Finance" and one to "Marketing". Log in as each user separately and confirm the sets of visible nodes are disjoint (Finance user sees no Marketing-only nodes, and vice versa). Both users see nodes with `domain_scope = "Global"`.

**Acceptance Scenarios**:

1. **Given** a user whose domain scope is "Finance", **When** the dashboard loads, **Then** only nodes with `domain_scope = "Finance"` or `domain_scope = "Global"` are rendered.
2. **Given** a user whose domain scope is "Finance" and the graph contains Marketing-scope nodes, **When** the dashboard renders, **Then** those Marketing-scope nodes are never returned by the API and never appear on the canvas.
3. **Given** an unauthenticated request to the dashboard API, **When** the request is received, **Then** the API returns HTTP 401 and no graph data is included in the response body.
4. **Given** a user whose profile has no explicit domain scope, **When** the dashboard loads, **Then** only nodes with `domain_scope = "Global"` are visible.

---

### Edge Cases

- What happens when the graph contains no nodes in the user's scope? → Empty state message on the canvas; no error is thrown.
- What happens when a clicked node has no edges (it is an isolated node in the scoped view)? → The side panel opens with the node's properties; no nodes are dimmed because there are no neighbours to highlight; the canvas state is otherwise unchanged.
- What happens when a node has been deleted from the graph but the client has it cached? → Dashboard re-fetches on each page load; no persistent client-side cache of node data between sessions.
- What happens when a stigmergic edge's `confidence_score` is exactly 0.0 or 1.0? → Edge renders at minimum or maximum visual weight respectively; no divide-by-zero or rendering artefact occurs.
- What happens when a `business_name` search matches more than 50 nodes? → The canvas renders up to 50 results with a "showing first 50 matches" notice; further filtering is encouraged.
- What happens if the graph engine becomes unavailable while the dashboard is open? → An inline error banner appears; the canvas is not blanked; the last rendered state (loaded at page open) is preserved until the user manually triggers a refresh.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The dashboard MUST expose a read-only HTTP endpoint for the browser client and MUST NOT expose any endpoint that mutates the graph (no CREATE, UPDATE, or DELETE operations).
- **FR-002**: The dashboard API MUST enforce domain-scope filtering on every graph query before returning data to the browser, using the authenticated user's `profile_id` and `domain_scope` (Rule 5.2). Requests that cannot be scoped MUST receive HTTP 403.
- **FR-003**: The browser client MUST render nodes and edges as an interactive, zoomable, pannable graph diagram.
- **FR-004**: The client MUST visually distinguish stigmergic edges from structural edges. Stigmergic edges MUST encode their `confidence_score` (0.0–1.0) as line width scaled linearly between 1px (score=0.0) and 6px (score=1.0). Structural and flow edges MUST render as a fixed 1.5px solid grey line.
- **FR-005**: The client MUST provide a filter panel allowing the user to select one or more Object Types to restrict the visible node set.
- **FR-006**: The client MUST provide a text search input that performs a case-insensitive substring match against each node's `business_name` property. Matching nodes MUST be emphasised by dimming all non-matching nodes. The canvas MUST re-centre on the most-connected matching node (highest direct edge count). Nodes with no `business_name` value are excluded from search results.
- **FR-007**: Clicking a node MUST open a detail side-panel showing: Object Type, domain scope, and the node's stored properties as key-value pairs. Simultaneously, all nodes that are NOT direct 1-hop neighbours of the selected node MUST be dimmed on the canvas. Clicking the canvas background or pressing Escape MUST clear the selection and restore all nodes to full opacity.
- **FR-008**: Hovering over an edge MUST display a tooltip showing: edge type, source/target node names, and — for stigmergic edges only — `confidence_score`, `rationale_summary`, and `last_accessed`.
- **FR-009**: The dashboard API MUST run as a separate process from the MCP SSE server so that MCP tool traffic and dashboard traffic do not share a port or process boundary.
- **FR-010**: The dashboard API and client MUST serve full, uncompressed JSON to the browser. It is explicitly exempt from TOON compact serialisation (Rule 3.5) and raw-JSON suppression (Rule 3.2) per Rule 3.6.
- **FR-011**: The dashboard client MUST authenticate using a pre-issued JWT Bearer token sent as an `Authorization: Bearer <token>` header on every API request; the API MUST reject requests without a valid token with HTTP 401. The JWT MUST carry the user's `profile_id` and `domain_scope` claims so that scoped visibility (FR-002) can be enforced server-side without a session store.
- **FR-012**: The dashboard MUST display a persistent visual legend explaining the difference between standard and stigmergic edges, and the meaning of visual weight for `confidence_score`.
- **FR-013**: The dashboard MUST fetch the full scoped graph payload once on page load. The client MUST provide a visible "Refresh" control that re-fetches the payload on demand. The client MUST NOT poll the backend automatically or maintain a persistent WebSocket connection.
- **FR-014**: Each node on the canvas MUST display its `business_name` as the primary label. When a `business_name` is present, the node's technical `label` MUST also be rendered beneath it in visually smaller text. When `business_name` is absent, only the technical `label` is shown.

### Key Entities

- **GraphNode**: A renderable node in the UI, representing an ObjectNode. Carries: `id`, `label` (the node's technical name, always present; shown as secondary smaller text on the canvas when `business_name` is also present), `business_name` (optional human-readable alias; shown as the primary canvas label when present; the target of the business name search), `meta_type_name`, `domain_scope`, `properties` (key-value dict for the detail panel).
- **GraphEdge**: A renderable edge in the UI. Carries: `id`, `source_id`, `target_id`, `edge_type`, `is_stigmergic` (boolean), `confidence_score` (null for non-stigmergic), `rationale_summary` (null for non-stigmergic), `last_accessed` (null for non-stigmergic).
- **UserSession**: Encapsulates the authenticated user's `profile_id` and `domain_scope`, injected into every dashboard API request to enforce scoped visibility.
- **FilterState**: Client-side state representing the active Object Type filter(s) and `business_name` search string. Applied locally after the scoped payload is received from the API.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can open the dashboard, search for a node by its `business_name`, and read its connections — without any prior knowledge of the graph structure — in under 1 minute. *(Manual validation gate — verified by usability review, not automated test.)*
- **SC-002**: The graph canvas renders the initial scoped view within 3 seconds for graphs containing up to 500 nodes and 2,000 edges. *(Automated: `GET /api/graph` response time ≤ 1.5s for a 500-node fixture; browser render time validated by T035.)*
- **SC-003**: 100% of API responses contain only nodes and edges within the requesting user's permitted domain scope; zero cross-domain data leaks are possible by design.
- **SC-004**: A human observer can correctly identify a stigmergic edge and estimate whether it is high-, medium-, or low-confidence from the visual encoding alone — without reading any tooltip — with an accuracy rate of ≥ 90% in a brief usability review. *(Manual validation gate — verified by usability review, not automated test.)*
- **SC-005**: Applying an Object Type filter or a `business_name` search updates the visible canvas in under 500 milliseconds for graphs up to the render limit. *(Automated: T035 performance test asserts filter operation time on a 500-node in-memory fixture.)*
- **SC-006**: The dashboard API introduces zero graph mutations; confirmed by integration tests that assert no write operations are issued to the graph engine during any dashboard request.

---

## Clarifications

### Session 2026-02-28

- Q: What authentication mechanism should the browser-facing dashboard use to establish user identity and transmit credentials to the API? → A: Browser-held JWT as Bearer token — client sends `Authorization: Bearer <token>` on all requests; JWT carries `profile_id` and `domain_scope` claims; no session store or external identity provider required.
- Q: How should the dashboard keep graph data current — real-time push, polling, or load-once? → A: Load-once per page load with a manual refresh button; no background polling or WebSocket connection.
- Q: What does "Business Term" refer to in the data model — a separate node type, a node property, or any string property? → A: A `business_name` string property stored directly on ObjectNode; search performs case-insensitive substring match against this field. Formerly referred to as "Business Term" throughout the spec (now normalised to `business_name`).
- Q: When a user clicks a node, should the canvas change or only a side panel appear? → A: Both — side panel opens with node properties AND all non-adjacent (non-1-hop-neighbour) nodes are dimmed on the canvas; clicking the background or pressing Escape clears the selection.
- Q: Which label text is rendered on the canvas node — the technical name, the business name, or both? → A: `business_name` as the primary label with the technical `label` in smaller text beneath when both are present; fall back to `label` alone when `business_name` is absent.

---

## Assumptions

- Authentication uses a pre-issued JWT Bearer token (`Authorization: Bearer <token>`) carrying `profile_id` and `domain_scope` claims. The dashboard does not introduce a session store, cookies, or an external identity provider. This mirrors the credential injection model used for MCP tool invocations while remaining stateless.
- The graph engine is accessible to the dashboard API process on the same network; direct client-to-graph-engine connections from the browser are not required or permitted.
- Initial release is bounded at ≤ 500 nodes per scoped view; graphs exceeding this limit are out of scope and will require a future pagination or level-of-detail iteration.
- The dashboard is read-only by definition; no optimistic concurrency, write-back, or form submission flows are in scope.
- Browser support targets modern evergreen browsers (Chrome, Firefox, Edge, Safari); legacy browser support is not required.
