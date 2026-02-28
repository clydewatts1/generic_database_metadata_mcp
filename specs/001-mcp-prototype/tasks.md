# Tasks: Stigmergic MCP Metadata Server Prototype

**Input**: Design documents from /specs/001-mcp-prototype/
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/mcp-tools.md, quickstart.md

**Status**: ✅ **ALL TASKS COMPLETE** - Implementation finished 2026-02-27

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [x] T001 Create project structure per implementation plan (src/mcp_server, src/graph, src/models, src/utils, tests)
- [x] T002 Initialize Python project with dependencies (mcp, falkordb, pydantic, freezegun)
- [x] T003 [P] Configure linting and formatting tools (ruff, mypy)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T004 Setup FalkorDB client wrapper in src/graph/client.py
- [x] T005 [P] Create base Pydantic models (MetaType, ObjectNode, StigmergicEdge) in src/models/base.py
- [x] T006 [P] Implement TOON compact serialization logic in src/models/serialization.py
- [x] T007 Setup ephemeral FalkorDB test fixtures in tests/conftest.py
- [x] T008 [P] Create logging utilities in src/utils/logging.py
- [x] T009 Initialize FastMCP server setup in src/mcp_server/server.py and app.py

**Checkpoint**: ✅ Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Genesis Seed Ingestion (Priority: P1) 🎯 MVP

**Goal**: Enable bulk ingestion of initial metadata without overwhelming the AI context window

**Independent Test**: Provide a CSV file to `bulk_ingest_seed` tool and verify the graph is populated silently with only a summary returned (< 10KB payload)

### Tests for User Story 1

- [x] T010 [P] [US1] Unit test for MetaType creation in tests/unit/test_ontology.py
- [x] T011 [P] [US1] Unit test for bulk ingestion (frugality assertion: payload < 10KB) in tests/unit/test_ingestion.py

### Implementation for User Story 1

- [x] T012 [P] [US1] Create MetaType CRUD operations in src/graph/ontology.py
- [x] T013 [P] [US1] Create ObjectNode CRUD operations in src/graph/nodes.py
- [x] T014 [US1] Implement bulk_ingest function in src/graph/nodes.py
- [x] T015 [US1] Create bulk_ingest_seed MCP tool in src/mcp_server/tools/ingestion.py
- [x] T016 [US1] Add validation for CSV parsing and error handling
- [x] T017 [US1] Add logging and frugality checks (ensure response < 10KB)

**Checkpoint**: ✅ Bulk ingestion works and returns only compact summaries

---

## Phase 4: User Story 2 - Dynamic Meta-Ontology Creation and Validation (Priority: P1)

**Goal**: Enable AI to define new Object Types and Edge Types on the fly with automatic validation schema generation

**Independent Test**: Define a new type "Dashboard" with required field "url", attempt valid insertion (succeeds), attempt invalid insertion (fails with validation error)

### Tests for User Story 2

- [x] T018 [P] [US2] Unit test for dynamic Pydantic model generation in tests/unit/test_ontology.py
- [x] T019 [P] [US2] Integration test for insert_node with validation (valid + invalid cases) in tests/unit/test_ingestion.py
- [x] T020 [P] [US2] Unit test for circuit breaker mechanism in tests/unit/test_ingestion.py

### Implementation for User Story 2

- [x] T021 [P] [US2] Implement dynamic Pydantic model factory (create_model) in src/models/dynamic.py
- [x] T022 [US2] Create register_meta_type MCP tool in src/mcp_server/tools/ontology.py
- [x] T023 [US2] Create insert_node MCP tool in src/mcp_server/tools/ingestion.py
- [x] T024 [US2] Implement pre-insertion validation logic using dynamic models
- [x] T025 [US2] Implement circuit breaker mechanism (3 failures → lock)
- [x] T026 [US2] Implement health_score tracking (decrement on validation failure)

**Checkpoint**: ✅ Dynamic type registration and validation work independently

---

## Phase 5: User Story 4 - Stigmergic Edge Creation and Reinforcement (Priority: P2)

**Goal**: Enable AI to create confidence-weighted connections that automatically reinforce when traversed

**Independent Test**: Create an edge, query it multiple times, observe confidence_score increase from 0.5 toward 1.0

### Tests for User Story 4

- [x] T027 [P] [US4] Unit test for edge creation with initial confidence=0.5 in tests/unit/test_stigmergy.py
- [x] T028 [P] [US4] Unit test for edge reinforcement (+0.1 per traversal) in tests/unit/test_stigmergy.py
- [x] T029 [P] [US4] Unit test for biological decay (using freezegun) in tests/unit/test_decay.py
- [x] T030 [P] [US4] Unit test for edge pruning (confidence < 0.1) in tests/unit/test_decay.py

### Implementation for User Story 4

- [x] T031 [P] [US4] Create StigmergicEdge CRUD operations in src/graph/edges.py
- [x] T032 [P] [US4] Implement edge reinforcement logic in src/graph/edges.py
- [x] T033 [P] [US4] Implement biological decay mechanism in src/graph/edges.py
- [x] T034 [US4] Create create_stigmergic_edge MCP tool in src/mcp_server/tools/stigmergy.py
- [x] T035 [US4] Create reinforce_stigmergic_edge MCP tool in src/mcp_server/tools/stigmergy.py
- [x] T036 [US4] Implement decay runner (run_decay_pass, run_all_decay) in src/graph/decay.py
- [x] T037 [US4] Add rationale_summary and created_by_profile_id tracking

**Checkpoint**: ✅ Stigmergic edge creation, reinforcement, and decay all work

---

## Phase 6: User Story 3 - Context-Frugal Querying and Compact Serialization (Priority: P2)

**Goal**: Enable bounded, paginated graph queries with TOON compact serialization

**Independent Test**: Execute a query that matches > 5 nodes and verify results are paginated and TOON-serialized

### Tests for User Story 3

- [x] T038 [P] [US3] Unit test for TOON serialization (strip defaults, abbreviate keys) in tests/unit/test_serialization.py
- [x] T039 [P] [US3] Unit test for paginated query results (page_size=5) in tests/unit/test_decay.py
- [x] T040 [P] [US3] Integration test for frugality assertion (payload < 10KB) in tests/integration/test_tools.py

### Implementation for User Story 3

- [x] T041 [P] [US3] Implement bounded graph query (max 1-2 hops) in src/graph/query.py
- [x] T042 [P] [US3] Implement pagination logic (default page_size=5) in src/graph/query.py
- [x] T043 [US3] Create query_graph MCP tool in src/mcp_server/tools/query.py
- [x] T044 [US3] Implement domain_scope filtering in queries
- [x] T045 [US3] Add TOON serialization to all tool responses
- [x] T046 [US3] Implement edge reinforcement on successful traversal

**Checkpoint**: ✅ Context-frugal queries return paginated, TOON-serialized results

---

## Phase 7: User Story 5 - Profile-Aware Scoping and Supreme Court (Priority: P3)

**Goal**: Enable domain-scoped queries and require approval for destructive global modifications

**Independent Test**: Query with "Finance" profile_id → verify only Finance + Global nodes returned; attempt global deletion → verify [APPROVAL_REQUIRED] returned

### Tests for User Story 5

- [x] T047 [P] [US5] Unit test for domain_scope filtering in tests/unit/test_domain_scoping.py
- [x] T048 [P] [US5] Unit test for [APPROVAL_REQUIRED] on global deletions in tests/unit/test_remaining_rules.py
- [x] T049 [P] [US5] Unit test for Parallel Truths (domain-specific branching) in tests/unit/test_remaining_rules.py
- [x] T050 [P] [US5] Unit test for cascading wither in tests/unit/test_remaining_rules.py

### Implementation for User Story 5 (Rules 5.1-5.3)

- [x] T051 [P] [US5] Add profile_id and domain_scope fields to all models in src/models/base.py
- [x] T052 [P] [US5] Update all 7 MCP tool signatures to accept profile_id and domain_scope
- [x] T053 [US5] Update MetaType creation to store profile_id and domain_scope in src/graph/ontology.py
- [x] T054 [US5] Update list_meta_types to filter by domain_scope in src/graph/ontology.py
- [x] T055 [US5] Update ObjectNode creation to persist profile_id in src/graph/nodes.py
- [x] T056 [US5] Update StigmergicEdge creation to persist created_by_profile_id in src/graph/edges.py
- [x] T057 [US5] Update query_graph to require profile_id/domain_scope parameters
- [x] T058 [US5] Implement WHERE clause domain filtering in src/graph/query.py

### Implementation for Additional Rules (2.7, 4.5, 5.4-5.5, Function Objects)

- [x] T059 [P] [US5] Create suggest_schema_heals MCP tool in src/mcp_server/tools/healing.py (Rule 2.7)
- [x] T060 [P] [US5] Create confirm_schema_heal MCP tool in src/mcp_server/tools/healing.py (Rule 2.7)
- [x] T061 [P] [US5] Create deprecate_node MCP tool in src/mcp_server/tools/lifecycle.py (Rule 4.5)
- [x] T062 [P] [US5] Create branch_node_for_domain MCP tool in src/mcp_server/tools/lifecycle.py (Rule 5.4)
- [x] T063 [P] [US5] Create request_node_deletion MCP tool in src/mcp_server/tools/lifecycle.py (Rule 5.5)
- [x] T064 [P] [US5] Create confirm_node_deletion MCP tool in src/mcp_server/tools/lifecycle.py (Rule 5.5)
- [x] T065 [P] [US5] Create create_function MCP tool in src/mcp_server/tools/functions.py (Function Objects)
- [x] T066 [P] [US5] Create query_functions MCP tool in src/mcp_server/tools/functions.py (Function Objects)
- [x] T067 [P] [US5] Create attach_function_to_nodes MCP tool in src/mcp_server/tools/functions.py (Function Objects)
- [x] T068 [US5] Update server.py to register new healing, lifecycle, and function tools

**Checkpoint**: ✅ All user stories independently functional with full domain scoping

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [x] T069 [P] Documentation updates in README.md (list all 17 MCP tools with examples)
- [x] T070 [P] Add specification rules coverage table to README.md
- [x] T071 Run quickstart.md validation to ensure the prototype works end-to-end
- [x] T072 Ensure all MCP tools return TOON formatted responses where applicable
- [x] T073 [P] Migrate all imports to relative paths (remove `from __future__`)
- [x] T074 [P] Add comprehensive docstrings to all graph layer functions
- [x] T075 Code cleanup and refactoring

**Checkpoint**: ✅ All polish tasks complete

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately ✅
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories ✅
- **User Stories (Phase 3-7)**: All depend on Foundational phase completion ✅
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P1 → P2 → P2 → P3) ✅
- **Polish (Phase 8)**: Depends on all user stories being complete ✅

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational - No dependencies ✅
- **User Story 2 (P1)**: Can start after Foundational - Uses MetaType ✅
- **User Story 4 (P2)**: Can start after Foundational - Uses ObjectNode ✅
- **User Story 3 (P2)**: Can start after Foundational - Queries nodes/edges ✅
- **User Story 5 (P3)**: Can start after Foundational - Adds domain scoping ✅

### Implementation Timeline

All tasks completed sequentially between 2026-02-26 and 2026-02-27:

1. **Foundation & MVP** (Phase 1-4): Core functionality with dynamic ontology
2. **Stigmergy** (Phase 5): Edge creation, reinforcement, and decay
3. **Context Frugality** (Phase 6): Bounded queries with TOON serialization
4. **Domain Scoping** (Phase 7): Profile-aware visibility and approval workflows
5. **Polish** (Phase 8): Documentation and final refinements

---

## Final Implementation Summary

### ✅ Completed Features

| Component | Tasks | Files | Status |
|-----------|-------|-------|--------|
| **Infrastructure** | T001-T009 | 9 files | ✅ Complete |
| **User Story 1** | T010-T017 | 8 tasks | ✅ Complete |
| **User Story 2** | T018-T026 | 9 tasks | ✅ Complete |
| **User Story 4** | T027-T037 | 11 tasks | ✅ Complete |
| **User Story 3** | T038-T046 | 9 tasks | ✅ Complete |
| **User Story 5** | T047-T068 | 22 tasks | ✅ Complete |
| **Polish** | T069-T075 | 7 tasks | ✅ Complete |

**Total Tasks**: 75 tasks across 8 phases
**Total MCP Tools**: 17 tools (7 core + 10 advanced)
**Total Specification Rules**: 26/26 implemented (100%)

### Test Coverage

- ✅ Unit tests: `tests/unit/test_ontology.py`, `test_ingestion.py`, `test_stigmergy.py`, `test_decay.py`
- ✅ Domain scoping tests: `tests/unit/test_domain_scoping.py`
- ✅ Advanced rules tests: `tests/unit/test_remaining_rules.py`
- ✅ All tests use ephemeral FalkorDB fixtures (no persistent state)
- ✅ Time-based tests use `freezegun` for deterministic testing

### Git Commits

All work committed across 5 commits:
- `c13ead0`: Rules 5.1-5.3 Part 1 (Models + Tool Signatures)
- `22ddb43`: Rules 5.1-5.3 Part 2 (Graph Layer + Domain Filtering)
- `72d28c1`: Tests: Domain scoping validation
- `854748d`: Rules 2.7, 4.5, 5.4-5.5 implementation
- `f44bf7e`: Documentation update + completion table

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [x] T001 Create project structure per implementation plan (src/mcp_server, src/graph, src/models, src/utils, tests)
- [x] T002 Initialize Python project with dependencies (mcp, falkordb, pydantic, freezegun)
- [x] T003 [P] Configure linting and formatting tools (ruff, mypy)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

- [x] T004 Setup FalkorDBLite connection manager in src/graph/client.py
- [x] T005 [P] Implement TOON serialization utility in src/models/serialization.py
- [x] T006 [P] Setup FastMCP server instance in src/mcp_server/server.py
- [x] T007 Create base Pydantic models (MetaType, ObjectNode, StigmergicEdge) in src/models/base.py
- [x] T008 Configure error handling and logging infrastructure in src/utils/logging.py

**Checkpoint**: Foundation ready - user story implementation can now begin.

---

## Phase 3: User Story 1 - Dynamic Ontology Definition (Priority: P1) 🎯 MVP

**Goal**: As an AI Agent, I need to define new metadata types dynamically so that I can adapt to new domains without schema migrations.

**Independent Test**: Can register a new MetaType and verify its schema is stored correctly.

### Tests for User Story 1

- [x] T009 [P] [US1] Write tests for MetaType registration in tests/unit/test_ontology.py

### Implementation for User Story 1

- [x] T010 [P] [US1] Implement MetaType graph operations (create, get) in src/graph/ontology.py
- [x] T011 [US1] Implement dynamic Pydantic model generation in src/models/dynamic.py
- [x] T012 [US1] Implement `register_meta_type` MCP tool in src/mcp_server/tools/ontology.py

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently.

---

## Phase 4: User Story 2 - Context-Frugal Ingestion (Priority: P1)

**Goal**: As an AI Agent, I need to ingest metadata with minimal token overhead so that I don't exhaust my context window.

**Independent Test**: Can insert a node and bulk ingest nodes, receiving only a short confirmation or TOON-formatted ID.

### Tests for User Story 2

- [x] T013 [P] [US2] Write tests for node insertion and bulk ingest in tests/unit/test_ingestion.py

### Implementation for User Story 2

- [x] T014 [P] [US2] Implement Node graph operations (create, get) in src/graph/nodes.py
- [x] T015 [US2] Implement `insert_node` MCP tool in src/mcp_server/tools/ingestion.py
- [x] T016 [US2] Implement `bulk_ingest_seed` MCP tool in src/mcp_server/tools/ingestion.py

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently.

---

## Phase 5: User Story 3 - Stigmergic Linking (Priority: P2)

**Goal**: As an AI Agent, I need to link related metadata nodes with a strength weight so that I can build a web of associations.

**Independent Test**: Can create an edge between two nodes and verify its initial strength.

### Tests for User Story 3

- [x] T017 [P] [US3] Write tests for edge creation in tests/unit/test_stigmergy.py

### Implementation for User Story 3

- [x] T018 [P] [US3] Implement Edge graph operations (create, update) in src/graph/edges.py
- [x] T019 [US3] Implement `create_stigmergic_edge` MCP tool in src/mcp_server/tools/stigmergy.py

**Checkpoint**: All ingestion and linking user stories should now be independently functional.

---

## Phase 6: User Story 4 - Biological Decay & Retrieval (Priority: P2)

**Goal**: As an AI Agent, I need unused links to decay over time and frequently used links to strengthen, so that my context remains relevant and uncluttered.

**Independent Test**: Can query the graph, observe edge strength decay over time (using freezegun), and see strength increase upon traversal.

### Tests for User Story 4

- [x] T020 [P] [US4] Write tests for decay logic and graph querying using freezegun in tests/test_decay.py

### Implementation for User Story 4

- [x] T021 [P] [US4] Implement decay calculation logic in src/graph/decay.py
- [x] T022 [US4] Implement graph traversal and querying logic in src/graph/query.py
- [x] T023 [US4] Implement `query_graph` MCP tool in src/mcp_server/tools/query.py

**Checkpoint**: All user stories should now be independently functional.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [x] T024 [P] Documentation updates in README.md
- [x] T025 Run quickstart.md validation to ensure the prototype works end-to-end
- [x] T026 Ensure all MCP tools return TOON formatted responses where applicable

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-6)**: All depend on Foundational phase completion
  - US1 (Ontology) must precede US2 (Ingestion) as nodes require MetaTypes.
  - US2 (Ingestion) must precede US3 (Linking) as edges require Nodes.
  - US3 (Linking) must precede US4 (Decay) as decay requires Edges.
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel (within Phase 2)
- Tests for a user story marked [P] can run in parallel with other tests or initial implementation steps.
