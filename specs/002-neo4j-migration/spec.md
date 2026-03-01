# Feature Specification: Neo4j Graph Database Migration

**Feature Branch**: `002-neo4j-migration`  
**Created**: 2026-03-01  
**Status**: Draft  
**Input**: User request: "Implement refactoring to neo4j"

**Constitution Check**: This feature implements Constitution v1.4.0 (ratified 2026-03-01), which mandates Neo4j Community Edition as the graph database backend (Section 1, Tech Stack), replacing all FalkorDB/FalkorDBLite references.

## User Scenarios & Testing

### User Story 1 - Developer Runs Existing Tests Against Neo4j (Priority: P1)

A developer with Neo4j installed locally runs the existing test suite without modification. All tests pass against the Neo4j backend, proving functional equivalence with the prior FalkorDB implementation.

**Why this priority**: Ensures no regression and validates the adapter layer works correctly. This is the foundation for all other functionality.

**Independent Test**: Run `pytest tests/` with Neo4j configured and verify 100% pass rate matches pre-migration baseline.

**Acceptance Scenarios**:

1. **Given** Neo4j is running locally with connection credentials configured, **When** developer runs `pytest tests/unit/`, **Then** all unit tests pass with identical assertions
2. **Given** Neo4j test database is empty, **When** developer runs integration tests, **Then** ephemeral test data is created, tested, and cleaned up correctly
3. **Given** a fresh Neo4j installation, **When** bootstrap script runs, **Then** all constraints and indexes are created successfully

---

### User Story 2 - Dashboard Connects to Neo4j Seamlessly (Priority: P1)

An operator starts the dashboard server with `NEO4J_URI` configured. The dashboard connects to Neo4j, queries graph data, and renders the health widget without errors or data loss.

**Why this priority**: Validates end-to-end integration with the visual dashboard (Rule 3.6 compliance).

**Independent Test**: Start dashboard with `NEO4J_*` env vars, authenticate with JWT, verify graph canvas loads and health widget displays MetaType data.

**Acceptance Scenarios**:

1. **Given** Neo4j contains metadata nodes, **When** user authenticates to dashboard, **Then** graph payload returns nodes scoped to user's `domain_scope` per Rule 5.2
2. **Given** Neo4j is unavailable, **When** dashboard `/health` endpoint is called, **Then** HTTP 503 is returned with degraded status per FR-010 (001-schema-health-widget)
3. **Given** valid JWT token, **When** user requests MetaType health data, **Then** data is retrieved from Neo4j (:MetaType) nodes with correct `health_score` values

---

### User Story 3 - MCP Server Executes Stigmergic Operations on Neo4j (Priority: P2)

An AI agent using the MCP server creates stigmergic edges, reinforces pheromone trails, and triggers biologicaldecay operations. All Constitution Section 4 mechanics function identically on Neo4j.

**Why this priority**: Validates core stigmergic paradigm (Constitution Rule 4.1-4.5) against new backend.

**Independent Test**: Run MCP tools that create/update stigmergic edges, verify `confidence_score` increments, `last_accessed` updates, and decay pruning works correctly.

**Acceptance Scenarios**:

1. **Given** a Business Term node exists, **When** AI creates a stigmergic edge to a Technical Node, **Then** edge is persisted in Neo4j with `confidence_score=0.5`, `last_accessed=now()`, and `rationale_summary` attribute
2. **Given** an existing stigmergic edge, **When** edge is traversed during query, **Then** `confidence_score` increments (capped at 1.0) and `last_accessed` timestamp updates
3. **Given** a stigmergic edge with `last_accessed` older than decay threshold, **When** decay job runs, **Then** `confidence_score` decrements and edge is deleted if score < 0.1

---

### User Story 4 - Developers Switch Between FalkorDB and Neo4j (Priority: P3)

A developer working on a machine with FalkorDB installed can still run the codebase. The adapter layer auto-detects available backend and uses FalkorDB if `NEO4J_URI` is not set, ensuring backward compatibility during transition period.

**Why this priority**: Enables gradual migration and CI/CD flexibility (some environments may still use FalkorDB temporarily).

**Independent Test**: Unset `NEO4J_URI`, start FalkorDB container, run tests. All pass using FalkorDB client path.

**Acceptance Scenarios**:

1. **Given** `NEO4J_URI` environment variable is not set and FalkorDB is running on localhost:6379, **When** `get_graph_client()` is called, **Then** FalkorDB client is instantiated
2. **Given** both `NEO4J_URI` and FalkorDB are available, **When** client initializes, **Then** Neo4j is preferred (explicit precedence)
3. **Given** neither Neo4j nor FalkorDB is available, **When** any graph query is attempted, **Then** clear RuntimeError is raised with setup instructions

---

### Edge Cases

- **What happens when Neo4j connection drops mid-query?** — Client must catch connection errors, log them, and raise appropriate HTTP 503 for dashboard endpoints or tool errors for MCP calls.
- **How does system handle Neo4j authentication failure?** — `get_graph_client()` must validate credentials on first connection and raise RuntimeError with actionable message ("NEO4J_PASSWORD incorrect").
- **What if Neo4j schema constraints conflict with existing data?** — Bootstrap script must check for constraint violations and provide migration guide (e.g., deduplicate nodes before applying UNIQUE constraints).
- **How is transaction rollback handled?** — Neo4j adapter must use session transactions and ensure atomic writes (all-or-nothing for multi-node operations).

## Requirements

### Functional Requirements

- **FR-001**: System MUST support Neo4j Community Edition v5.x as the primary graph database backend.
- **FR-002**: System MUST provide a `Neo4jClient` adapter class that implements the same query interface as the existing FalkorDB client (`query(cypher: str, params: dict) -> ResultSet`).
- **FR-003**: System MUST auto-detect graph backend based on environment variables (`NEO4J_URI` presence) and fallback to FalkorDB if Neo4j is not configured.
- **FR-004**: All Cypher queries MUST execute identically on both Neo4j and FalkorDB without syntax modifications (Cypher compatibility layer).
- **FR-005**: System MUST create Neo4j schema constraints for `(:MetaType {name})`, `(:ObjectNode {node_id})`, and `(:HumanAuditLog {audit_id})` on bootstrap.
- **FR-006**: System MUST create Neo4j indexes for `(:ObjectNode {domain_scope})`, `(:ObjectNode {meta_type})` for query performance.
- **FR-007**: Test suite MUST support ephemeral Neo4j test databases (either in-memory or per-test database creation/teardown) per Rule 6.3.
- **FR-008**: Dashboard health endpoint (`/health`) MUST return HTTP 503 with `{"status": "degraded"}` if Neo4j connection fails.
- **FR-009**: All stigmergic edge operations (creation, reinforcement, decay, pruning) MUST function identically on Neo4j as they did on FalkorDB.
- **FR-010**: System MUST log Neo4j connection URI (excluding password) on startup for debugging.
- **FR-011**: Migration MUST NOT require changes to existing MCP tool implementations or dashboard API routes (transparent backend swap).

### Key Entities

- **Neo4jClient**: Singleton adapter wrapping `neo4j.GraphDatabase.driver` with FalkorDB-compatible interface.
- **Neo4jGraph**: Session manager providing `query(cypher, params)` method and result set normalization.
- **Neo4jResultSet**: Result adapter converting Neo4j `Record` objects to dict-based result sets matching FalkorDB's interface.

### Success Criteria

- All existing tests (unit, contract, integration) pass against Neo4j backend with zero code changes to test assertions.
- Dashboard loads graph data from Neo4j and renders health widget correctly.
- MCP server creates stigmergic edges in Neo4j with correct attributes (`confidence_score`, `last_accessed`, `rationale_summary`).
- Bootstrap script creates Neo4j constraints and indexes without errors on fresh database.
- System startup logs indicate successful Neo4j connection with connection URI.
- Existing FalkorDB-based deployments can continue to function if `NEO4J_URI` is not set (backward compatibility verified).

### Out of Scope

- Data migration tooling for existing FalkorDB databases (users must export/import manually if needed).
- Neo4j Enterprise Edition features (clustering, hot backups) — Community Edition only.
- GraphQL endpoint support — focus on Cypher query layer only.
- Web-based Neo4j query console integration — users can use Neo4j Browser separately.

### Assumptions

- Neo4j Community Edition is installed locally and accessible via `bolt://` protocol.
- User has created a Neo4j database (default name: `metadata_mcp`) and set credentials.
- Python `neo4j` driver v5.x is compatible with project's Python 3.11+ requirement.
- Cypher syntax used in existing queries is standard and supported by both FalkorDB and Neo4j.
- Tests currently using FalkorDB mocks can be adapted to use Neo4j test databases or fixtures.

### Dependencies

- **External**: Neo4j Community Edition v5.x installed and running locally.
- **Python Package**: `neo4j>=5.0.0` driver.
- **Internal**: No changes to `src/graph/ontology.py`, `src/dashboard/graph_service.py`, or `src/dashboard/health_service.py` required (they use abstract client interface).

### Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Neo4j Cypher dialect differs from FalkorDB's | High | Medium | Test all existing queries against Neo4j; add compatibility shims if needed |
| Test isolation more complex with Neo4j | Medium | High | Use separate test database or transaction rollback per test |
| Performance regression vs. FalkorDB | Medium | Low | Benchmark key queries; add indexes if needed |
| Backward compatibility breaks existing deployments | High | Low | Keep FalkorDB fallback; document migration path clearly |

### Constitution Check

This feature directly implements Constitution v1.4.0 amendments:

- **Section 1 (Tech Stack)**: ✅ Implements Neo4j Community Edition as mandated.
- **Rule 2.1-2.8 (Dynamic Pydantic Ontology)**: ✅ No changes required — Pydantic validation layer is backend-agnostic.
- **Rule 3.1-3.6 (Context Frugal Mandate)**: ✅ Cypher depth limits and pagination unchanged.
- **Rule 4.1-4.5 (Stigmergic Execution)**: ✅ Confidence scoring, decay, pruning logic unchanged — only storage backend differs.
- **Rule 5.1-5.7 (Profile-Aware Scoping)**: ✅ `domain_scope` filtering in Cypher queries works identically on Neo4j.
- **Rule 6.3 (Ephemeral Sandbox)**: ✅ FR-007 ensures test isolation with Neo4j test databases.

**No constitutional violations**: This is a pure backend substitution maintaining all semantic contracts.
