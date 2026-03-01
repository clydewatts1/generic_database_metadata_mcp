# Tasks: Neo4j Graph Database Migration

**Input**: Design documents from `/specs/002-neo4j-migration/`  
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/neo4j-adapter-interface.md, quickstart.md

**Feature Goal**: Migrate graph database backend from FalkorDB to Neo4j Community Edition v5.x while maintaining 100% backward compatibility and functional equivalence across all consumer code (dashboard, MCP tools, tests).

**Organization**: Tasks grouped by user story to enable independent implementation and parallel execution where possible. Each user story is independently testable and deliverable.

---

## Phase 1: Setup (Project Initialization)

**Purpose**: Install dependencies and create boilerplate structure

- [x] T001 Install neo4j>=5.0.0 package into requirements.txt
- [x] T002 Create Neo4j adapter boilerplate in src/graph/neo4j_client.py (empty classes: Neo4jClient, Neo4jGraph, Neo4jResultSet)
- [x] T003 Create conftest.py boilerplate in tests/ for Neo4j database fixtures

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core Neo4j adapter layer that MUST be complete before ANY user story implementation begins

**⚠️ CRITICAL**: No user story work can proceed until Phase 2 is complete and all adapter classes implement the contract interface.

### Adapter Implementation

- [x] T004 [P] Implement Neo4jClient singleton class in src/graph/neo4j_client.py with: _driver lazy initialization, get_driver() method, connection pooling configuration, URI/user/password/database attributes per data-model.md
- [x] T005 [P] Implement Neo4jGraph session manager in src/graph/neo4j_client.py with: query(cypher, params) method, result set normalization, error handling per contract
- [x] T006 [P] Implement Neo4jResultSet adapter in src/graph/neo4j_client.py with: .result_set list attribute, __iter__() for dict iteration, node/relationship conversion to match FalkorDB dict structure per contract
- [x] T007 Implement Neo4jClient.verify_connectivity() in src/graph/neo4j_client.py to test connection on first access (execute simple RETURN 1 query)
- [x] T008 Implement Neo4jGraph._ensure_bootstrap() in src/graph/neo4j_client.py with idempotent schema bootstrap: CREATE CONSTRAINT for MetaType {name}, ObjectNode {node_id}, HumanAuditLog {audit_id}; CREATE INDEX for ObjectNode {domain_scope}, {meta_type} per FR-005, FR-006, research.md Decision 5

### Client Module Setup

- [x] T009 Create get_graph() factory function in src/graph/client.py with: auto-detection logic checking NEO4J_URI env var, Neo4j instantiation if present, FalkorDB fallback if absent, singleton pattern per data-model.md, FR-003

### Test Infrastructure

- [x] T010 [P] Create pytest fixtures in tests/conftest.py for per-test Neo4j database creation/teardown with: database naming strategy (UUID suffix to prevent collisions), CREATE DATABASE before test, DROP DATABASE after test, cleanup on failures per FR-007, research.md Decision 3
- [x] T011 [P] Create Neo4j test configuration fixtures in tests/conftest.py with: NEO4J_URI from env or default, credentials from env, database name management per quickstart.md

### Error Handling & Logging

- [x] T012 [P] Implement connection retry logic with exponential backoff in Neo4jClient._with_retries() in src/graph/neo4j_client.py: 3 retries, max 5 seconds total, exponential backoff (0.5s, 1s, 2s), raise RuntimeError with clear message after exhaustion per FR-013, research.md Decision 2
- [x] T013 [P] Add comprehensive logging in src/graph/neo4j_client.py for: connection events (startup, success), retry attempts (with delay), bootstrap operations (constraint/index creation), failures with actionable messages per FR-010, spec §Edge Cases
- [x] T014 Add password masking to logged connection URIs in src/graph/neo4j_client.py (log "bolt://user@host:port/db" without password) per FR-010

**Checkpoint**: All adapter classes complete, tests execute successfully with Neo4j. Ready to begin parallel user story implementation.

---

## Phase 3: User Story 1 - Developer Runs Existing Tests Against Neo4j (Priority: P1) 🎯 MVP

**Goal**: All existing test suite passes against Neo4j backend with zero code changes to test assertions, proving functional equivalence.

**Independent Test**: Execute `pytest tests/unit/ tests/contract/ tests/integration/ -v` with NEO4J_URI configured, verify 100% pass rate.

**Acceptance Criteria**:
1. Unit tests pass with identical assertions (no modifications)
2. Contract tests pass with Neo4j schema constraints applied
3. Integration tests create/cleanup ephemeral test databases correctly
4. Schema bootstrap runs automatically on first test execution
5. Test execution time acceptable (per test <500ms for DB setup + query, baseline from FalkorDB mocks ~50-100ms combined)

### Unit Tests

- [x] T015 [P] [US1] Verify unit tests in tests/unit/dashboard/ work without modification against mocked Neo4j adapter
- [x] T016 [P] [US1] Verify unit tests in tests/unit/graph/ work without modification against mocked queries
- [x] T017 [P] [US1] Execute unit test suite with pytest and confirm 100% pass rate

### Contract Tests

- [x] T018 [P] [US1] Verify contract tests in tests/contract/test_dashboard_mutations.py work without modification (FalkorDB compat layer)
- [x] T019 [P] [US1] Verify contract tests in tests/contract/test_health_mutations.py work without modification
- [x] T020 [US1] Execute contract test suite with pytest and confirm 100% pass rate

### Integration Tests

- [x] T021 [P] [US1] Create integration test in tests/integration/test_neo4j_adapter.py: verify Neo4jDriver connects and executes simple query
- [x] T022 [P] [US1] Create integration test in tests/integration/test_neo4j_adapter.py: verify schema bootstrap is automatic and idempotent on first test
- [x] T023 [P] [US1] Create integration test in tests/integration/test_neo4j_adapter.py: verify test database is ephemeral (cleanup on test end)
- [x] T024 [P] [US1] Create integration test in tests/integration/test_function_objects_e2e.py: verify ObjectNode CRUD operations work identically to FalkorDB
- [x] T025 [P] [US1] Create integration test in tests/integration/test_stigmergic_e2e.py: verify stigmergic edge creation works identically to FalkorDB
- [x] T026 [US1] Execute full integration test suite with pytest against Neo4j and confirm 100% pass rate

**Checkpoint**: User Story 1 complete - all tests pass. Foundation proven. Ready for dashboard and MCP integration (Stories 2-3).

---

## Phase 4: User Story 2 - Dashboard Connects to Neo4j Seamlessly (Priority: P1)

**Goal**: Dashboard server starts with NEO4J_URI configured, connects to Neo4j, queries graph data, renders health widget correctly. End-to-end integration verified.

**Independent Test**: Start dashboard with `NEO4J_*` env vars set, POST JWT token to /authenticate, GET /dashboard/graph and verify response structure and data correctness.

**Acceptance Criteria**:
1. Dashboard graph_service.py queries work without modification (existing execute_query calls work against Neo4j)
2. Domain scope filtering applied correctly (Rule 5.2 enforced)
3. Health endpoint returns HTTP 503 if Neo4j unavailable (FR-008)
4. Graph payload renders with correct node/edge structure
5. MetaType health_score values retrieved correctly

### Backend Compatibility

- [x] T027 [P] [US2] Verify src/dashboard/graph_service.py._fetch_nodes() works against Neo4j without modification (uses generic execute_query interface)
- [x] T028 [P] [US2] Verify src/dashboard/graph_service.py._fetch_stigmergic_edges() works against Neo4j without modification
- [x] T029 [P] [US2] Verify src/dashboard/graph_service.py._fetch_structural_edges() works against Neo4j without modification (MATCH relationships query)
- [x] T030 [P] [US2] Verify domain_scope filtering in where clauses works identically on Neo4j (WHERE n.domain_scope = $ds logic)

### Dashboard API Tests

- [ ] T031 [US2] Create integration test in tests/integration/test_dashboard_api.py: POST /authenticate with JWT, verify 200 response
- [ ] T032 [US2] Create integration test in tests/integration/test_dashboard_api.py: GET /dashboard/graph with valid JWT, verify nodes/edges returned with correct structure
- [ ] T033 [US2] Create integration test in tests/integration/test_dashboard_api.py: GET /dashboard/graph with domain_scope='Finance', verify only Finance + Global nodes returned per Rule 5.2
- [ ] T034 [US2] Create integration test in tests/integration/test_dashboard_api.py: GET /dashboard/health, verify MetaType health_score values match database
- [ ] T035 [US2] Create integration test in tests/integration/test_dashboard_api.py: Simulate Neo4j unavailable (stop server or corrupt URI), GET /health, verify HTTP 503 + degraded status per FR-008

### Dashboard Degraded State

- [x] T036 [P] [US2] Verify src/dashboard/health_router.py returns HTTP 503 with degraded status when Neo4j connection fails (existing error handling logic works)
- [ ] T037 [US2] Create integration test in tests/integration/test_dashboard_api.py: Corrupt NEO4J_PASSWORD, start dashboard, verify /health returns 503 immediately (retry exhausted)

**Checkpoint**: User Story 2 complete - dashboard fully functional against Neo4j. Ready for MCP server integration (Story 3).

---

## Phase 5: User Story 3 - MCP Server Executes Stigmergic Operations on Neo4j (Priority: P2)

**Goal**: MCP tools that create/update stigmergic edges function identically on Neo4j. All Constitution Section 4 mechanics preserved: confidence scoring, 30-day decay threshold, edge pruning.

**Independent Test**: Invoke MCP tool to create stigmergic edge, verify confidence_score, last_accessed, rationale_summary persisted in Neo4j. Invoke decay tool, verify old edges (>30 days) pruned, scores decremented.

**Acceptance Criteria**:
1. Stigmergic edge creation works identically to FalkorDB (same attributes, same initial values)
2. Confidence score increments on traversal (capped at 1.0)
3. Last accessed timestamp updates on traversal
4. 30-day decay threshold applied correctly (edges older than 30 days decremented)
5. Edge pruning when confidence < 0.1
6. All operations atomic (multi-field updates succeed/fail together)

### Stigmergic Operations

- [ ] T038 [P] [US3] Create integration test in tests/integration/test_stigmergic_operations.py: Create stigmergic edge via MCP tool (or direct query), verify persisted with confidence_score=0.5, last_accessed=now(), rationale_summary attribute
- [ ] T039 [P] [US3] Create integration test in tests/integration/test_stigmergic_operations.py: Traverse stigmergic edge, verify confidence_score increments and last_accessed updates (atomic transaction)
- [ ] T040 [P] [US3] Create integration test in tests/integration/test_stigmergic_operations.py: Confidence score capped at 1.0 (increment when already at 1.0 remains at 1.0)
- [ ] T041 [P] [US3] Create integration test in tests/integration/test_stigmergic_operations.py: Mock time advance (freezegun) to 31 days after last_accessed, run decay job, verify confidence decremented and pruned if < 0.1

### Decay & Pruning

- [ ] T042 [P] [US3] Implement or verify stigmergic decay logic in src/graph/query.py or existing decay job: query edges with last_accessed > 30 days ago, decrement confidence_score by fixed amount (e.g., 0.1), delete if score < 0.1, use transaction for atomicity
- [ ] T043 [US3] Create integration test in tests/integration/test_stigmergic_decay.py: Setup 100 stigmergic edges with varying ages and scores, run decay job, verify only old edges (>30 days) affected and correct edges pruned per FR-009, spec User Story 3

### Comparison to FalkorDB

- [ ] T044 [US3] Compare MCP tool behavior: create identical edge on both FalkorDB and Neo4j, verify attributes match
- [ ] T045 [US3] Compare decay behavior: initialize identical edge set on both backends, advance time 31+ days, run decay on both, verify outcome identical (Neo4j matches FalkorDB exactly) per FR-009

**Checkpoint**: User Story 3 complete - stigmergic operations fully functional. Ready for backward compatibility support (Story 4).

---

## Phase 6: User Story 4 - Developers Switch Between FalkorDB and Neo4j (Priority: P3)

**Goal**: Backward compatibility maintained. System auto-detects available backend and uses FalkorDB if NEO4J_URI not set. Gradual migration possible.

**Independent Test**: Unset NEO4J_URI env var, start FalkorDB container, run tests. All pass using FalkorDB client path. Verify Neo4j not required during transition period.

**Acceptance Criteria**:
1. FalkorDB path works if NEO4J_URI not set (backward compatible)
2. Neo4j preferred when both available (explicit precedence)
3. Clear error if neither available (actionable setup instructions)
4. Existing FalkorDB deployments can continue without Neo4j

### Backend Detection

- [ ] T046 [P] [US4] Create integration test in tests/integration/test_backend_detection.py: NEO4J_URI not set, FalkorDB running on localhost:6379, get_graph() returns FalkorDB client, query executes successfully
- [ ] T047 [P] [US4] Create integration test in tests/integration/test_backend_detection.py: Both NEO4J_URI and FalkorDB available, verify Neo4j client instantiated (precedence to Neo4j) per FR-003, spec User Story 4
- [ ] T048 [P] [US4] Create integration test in tests/integration/test_backend_detection.py: Neither Neo4j nor FalkorDB available, get_graph() raises RuntimeError with setup instructions (where to download/configure each backend)
- [ ] T049 [US4] Unset NEO4J_URI, start FalkorDB container, execute pytest tests/unit/ tests/contract/ tests/integration/, verify 100% pass rate using FalkorDB backend unchanged

### Backward Compatibility Verification

- [ ] T050 [P] [US4] Verify existing FalkorDB client import path src/graph/client.py still works without changes (get_graph() returns either Neo4j or FalkorDB transparently)
- [ ] T051 [US4] Verify all existing MCP tools work with both backends (tools call get_graph() which returns compatible interface)
- [ ] T052 [US4] Verify all existing dashboard code works with both backends (dashboard calls execute_query which routes to correct backend)

**Checkpoint**: User Story 4 complete - backward compatibility fully supported. All four user stories implemented independently and tested.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final quality assurance, documentation, and non-functional requirement verification

### Documentation & Migration Guide

- [ ] T053 Create comprehensive Neo4j migration guide in docs/neo4j-migration.md: what changed, why, how to configure, common issues, rollback procedure
- [ ] T054 Update README.md to document Neo4j as primary backend with FalkorDB as fallback option (update constellation v1.4.0 reference)
- [ ] T055 Document Neo4j test database setup in TESTING.md: how to configure test fixtures, how per-test databases work, troubleshooting orphaned test databases
- [ ] T056 Update developer setup guide in CONTRIBUTING.md: Neo4j installation, environment variable configuration, connection verification steps

### Logging & Observability

- [ ] T057 [P] Add structured logging to schema bootstrap in src/graph/neo4j_client.py: log constraint creation attempts, success/failure, timing
- [ ] T058 [P] Add structured logging to connection retry in src/graph/neo4j_client.py: log retry N/max, backoff delay, cumulative elapsed time, final status
- [ ] T059 Verify Neo4j connection URI logged on startup (excluding password) in src/mcp_server/server.py startup sequence per FR-010

### Performance Testing

- [ ] T060 Measure and document cold start latency with Neo4j: connection + schema bootstrap time, target <500ms per contract, research.md Decision 2
- [ ] T061 Measure and document simple query latency: MATCH (n:ObjectNode) RETURN n query timing, target <10ms per contract
- [ ] T062 Measure and document stigmergic edge operation latency: create edge, update score, verify <50ms overhead per plan.md

### Constitution Compliance Verification

- [ ] T063 Verify Rule 2.1-2.8 (Dynamic Pydantic Ontology): confirm Pydantic models unchanged (no backend-specific modifications)
- [ ] T064 Verify Rule 3.1 (Bounded Depth): confirm Cypher queries remain limited to *1..2 hops (no unbounded traversals introduced)
- [ ] T065 Verify Rule 3.2 (Semantic Compression): confirm no raw JSON topology dumps, only context-frugal queries per FR-004
- [ ] T066 Verify Rule 3.3 (Pagination): confirm >5 nodes triggers pagination (verify in dashboard graph payload)
- [ ] T067 Verify Rule 4.1-4.5 (Stigmergic Execution): confirm 30-day decay, confidence scoring, pruning work identically to FalkorDB
- [ ] T068 Verify Rule 5.2 (Domain Scope): confirm domain_scope filtering applied in all queries (never overridden by params)
- [ ] T069 Verify Rule 6.3 (Ephemeral Test Databases): confirm per-test database creation/teardown working correctly with zero cross-contamination

### Code Quality

- [ ] T070 [P] Remove any FalkorDB-specific comments or TODOs from src/dashboard/graph_service.py (e.g., "FalkorDB workaround" comments if applicable)
- [ ] T071 [P] Review error messages in src/graph/neo4j_client.py for clarity and actionability (users should know what to fix)
- [ ] T072 Run type checking (mypy or similar) against src/graph/neo4j_client.py and verify zero errors per Python 3.11+ requirements

### Final Integration Test

- [ ] T073 Execute full integration test suite: pytest tests/unit/ tests/contract/ tests/integration/ -v --tb=short with Neo4j backend, verify 100% pass rate
- [ ] T074 Execute full integration test suite with FalkorDB backend (NEO4J_URI unset), verify 100% pass rate for backward compatibility
- [ ] T075 Manual smoke test: start MCP server with NEO4J_URI configured, start dashboard, execute sample MCP tools, verify graph operations and dashboard rendering

**Checkpoint**: Phase 7 complete - all quality requirements met, documentation current, Constitution compliant, performance acceptable. Feature ready for merge.

---

## Dependencies & Execution Order

### Critical Path (Must Complete in Order)

1. **Phase 1** → All tasks (enables Phase 2)
2. **Phase 2** → Foundational tasks (blocks all user stories)
3. **Phase 3-6** → User stories can execute in parallel AFTER Phase 2 complete
   - Story 1 (US1) and Story 2 (US2) are both P1 and can run in parallel
   - Story 3 (US3) is P2 and independent
   - Story 4 (US4) is P3 and independent
4. **Phase 7** → Polish (can start after US1+US2 pass, completes after US3+US4)

### Parallelization Opportunities

**After Phase 2 Foundational Complete**:
- T015-T026 (US1 tests) run in parallel with T027-T037 (US2 dashboard)
- T038-T045 (US3 stigmergic) run in parallel with T046-T052 (US4 fallback)
- T057-T062 (logging/perf) can begin once US1 tests pass

**Within User Stories**:
- US1: T015-T020 (unit/contract tests) all parallelizable
- US2: T027-T030 (backend compat) all parallelizable
- US3: T038-T043 (stigmergic ops) all parallelizable
- US4: T046-T048 (backend detection) all parallelizable

**Example Parallel Execution Plan**:
```
Phase 1    (T001-T003) → Complete
Phase 2    (T004-T014) → Complete
Phase 3+4  (T015-T037) → Run in parallel
Phase 5    (T038-T045) → Run in parallel
Phase 6    (T046-T052) → Run in parallel
Phase 7    (T053-T075) → Run sequentially after T026 complete
```

---

## Test Coverage Requirements

**All Tests Must Pass Before Merge**:
- ✅ Unit tests: 100% pass rate (Phase 3)
- ✅ Contract tests: 100% pass rate (Phase 3)
- ✅ Integration tests: 100% pass rate (Phase 3-6)
- ✅ Dashboard API tests: All acceptance scenarios (Phase 4)
- ✅ Stigmergic operations tests: All edge cases (Phase 5)
- ✅ Backend detection tests: All fallback paths (Phase 6)
- ✅ Backward compatibility: FalkorDB fallback path works (Phase 6)
- ✅ Constitution compliance: All rules verified (Phase 7)

**Test Isolation Verification**:
- ✅ Per-test database creation working (T010)
- ✅ No cross-contamination between parallel tests (T022)
- ✅ Cleanup on both success and failure (T023)
- ✅ Orphaned test databases manually cleanup guide in docs

---

## Success Metrics

**Completion Criteria**:
- [ ] All 75 tasks marked complete
- [ ] All test suites pass with >95% pass rate (allow 1-2 flaky network tests)
- [ ] Performance benchmarks meet targets:
  - Cold start <500ms
  - Simple query <10ms
  - Stigmergic operations <50ms overhead
- [ ] Zero Constitution violations
- [ ] Backward compatibility verified (FalkorDB path works)
- [ ] Documentation complete (migration guide, setup guide, troubleshooting)
- [ ] Code reviewed and merged to feature branch

**Definition of Done**:
- [ ] All Phase 1-2 tasks complete (foundation ready)
- [ ] At least one complete user story (US1) fully tested and working
- [ ] User stories are independently testable and deliverable
- [ ] No regression against existing FalkorDB deployments
- [ ] Migration path documented and communicated to team

---

## Notes

- Tasks use exact file paths for implementation clarity
- [P] marker indicates parallelizable tasks (can run concurrently)
- [US1][US2][US3][US4] labels map to user stories from spec.md
- Each user story boundary is independent (can deploy separately)
- Phase 2 Foundational is critical path - no user story work until complete
- Tests marked OPTIONAL in template ARE included here - per spec requirement for 100% test pass requirement
- Retry logic, logging, and password masking are part of Foundational (T012-T014) not deferred to Polish
