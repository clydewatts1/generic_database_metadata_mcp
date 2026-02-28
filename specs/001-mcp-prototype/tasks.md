---
description: "Task list for Stigmergic MCP Metadata Server Prototype implementation"
---

# Tasks: Stigmergic MCP Metadata Server Prototype

**Input**: Design documents from `/specs/001-mcp-prototype/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/mcp-tools.md

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [x] T001 Create project structure (`src/`, `tests/`) per implementation plan
- [x] T002 Initialize Python environment with `mcp`, `falkordb`, `pydantic`, `pyyaml`, `structlog`, and `freezegun` dependencies
- [x] T003 [P] Setup structured JSON logging (`structlog`) for observability in `src/mcp_server/server.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

- [x] T004 Create core Pydantic base models (`MetaType`, `ObjectNode`, `StigmergicEdge`, `FunctionObject`) in `src/models/base.py`
- [x] T005 [P] Setup `FalkorDB` client connection lifecycle and singleton in `src/graph/client.py`
- [x] T006 Initialize FastMCP server instance and basic routing in `src/mcp_server/server.py`
- [x] T007 Configure ephemeral in-memory graph fixtures for test isolation using `pytest` in `tests/conftest.py`

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Genesis Seed Ingestion (Priority: P1) 🎯 MVP

**Goal**: As an administrator, I want to bulk ingest initial metadata (e.g., YAML schema dumps) without overwhelming the AI context window, so that the system has a foundational graph to work with.

**Independent Test**: Can be fully tested by providing a YAML data file to the `bulk_ingest_seed` tool and verifying the graph is populated without returning the full graph to the AI.

### Tests for User Story 1

- [x] T008 [P] [US1] Integration test for YAML seed ingest missing context bloat in `tests/integration/test_ingest.py`

### Implementation for User Story 1

- [x] T009 [P] [US1] Create core graph bulk insert functions in `src/graph/queries.py`
- [x] T010 [P] [US1] Build YAML parser and logic for `bulk_ingest_seed` tool in `src/mcp_server/tools/ingest.py`
- [x] T011 [US1] Register `bulk_ingest_seed` tool with the main FastMCP server in `src/mcp_server/server.py`

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Dynamic Meta-Ontology Creation and Validation (Priority: P1)

**Goal**: As an AI agent, I want to define new Object Types and Edge Types on the fly, and have the system automatically generate validation schemas.

**Independent Test**: Can be fully tested by defining a new type, attempting to insert a valid instance (succeeds), and attempting to insert an invalid instance (fails).

### Tests for User Story 2

- [x] T012 [P] [US2] Contract and unit test for Pydantic dynamic model generation in `tests/unit/test_schema.py`

### Implementation for User Story 2

- [x] T013 [P] [US2] Implement dynamic Pydantic definitions `create_model` in `src/graph/schema.py`
- [x] T014 [US2] Implement pre-insertion validation and `health_score` tracking in `src/graph/schema.py`
- [x] T015 [US2] Build `register_meta_type`, `patch_meta_type`, and `insert_node` tools in `src/mcp_server/tools/ontology.py`
- [x] T016 [US2] Build Circuit Breaker (locking execution after 3 failed tries) and `confirm_schema_heal` tool in `src/mcp_server/tools/ontology.py`
- [x] T017 [US2] Register ontology tools in `src/mcp_server/server.py`

---

## Phase 5: User Story 3 - Context-Frugal Querying and Serialisation (Priority: P2)

**Goal**: As an AI agent, I want to query the graph and receive results bounded in depth, paginated (max 5), and serialized in a token-efficient format (TOON).

**Independent Test**: Fire a query returning > 5 nodes, proving response restricts payload size, returns pagination metadata, and is compressed.

### Tests for User Story 3

- [x] T018 [P] [US3] Unit test frugality bounds (TOON serialization and Pagination) in `tests/unit/test_serialization.py`

### Implementation for User Story 3

- [x] T019 [P] [US3] Implement TOON output serialization format in `src/mcp_server/formatters/toon.py`
- [x] T020 [US3] Implement depth-bounded (1-2 hop max) Cypher read queries with pagination in `src/graph/queries.py`
- [x] T021 [US3] Build `query_graph` tool applying TOON and pagination in `src/mcp_server/tools/query.py`
- [x] T022 [US3] Register query tool in `src/mcp_server/server.py`

---

## Phase 6: User Story 4 - Stigmergic Edge Creation and Reinforcement (Priority: P2)

**Goal**: As an AI agent, I want to automatically reinforce semantic connections across paths the users traverse and let unused pathways decay based on time.

**Independent Test**: Use freezegun test to mock time passing 7+ days, proving edge confidence drops at 0.02/day.

### Tests for User Story 4

- [x] T023 [P] [US4] Write time-mocked freezegun tests for decay and cascading wither in `tests/unit/test_stigmergy.py`

### Implementation for User Story 4

- [x] T024 [P] [US4] Build `create_stigmergic_edge` tool capturing prompt_hash and rationale in `src/mcp_server/tools/stigmergy.py`
- [x] T025 [US4] Implement pheromone reinforcement logic on successful query execution inside `src/graph/queries.py`
- [x] T026 [US4] Build biological decay/pruning routine and "Cascading Wither" for detached edges in `src/graph/client.py`
- [x] T027 [US4] Register stigmergy tool in `src/mcp_server/server.py`

---

## Phase 7: User Story 5 - Profile-Aware Scoping and Supreme Court (Priority: P3)

**Goal**: As a user, I want queries isolated to my domain, conflicts handled via branch variants, and human approval required for global deletion.

**Independent Test**: Delete global MetaType -> observe `[APPROVAL_REQUIRED]`; Insert conflicting domain record -> observe `[:VARIANTS]`.

### Tests for User Story 5

- [x] T028 [P] [US5] Unit test domain scoping, Parallel Truths, and approval interception in `tests/unit/test_scoping.py`

### Implementation for User Story 5

- [x] T029 [P] [US5] Inject Profile Context into all `graph/queries.py` execution
- [x] T030 [US5] Add `[:VARIANTS]` logic in `src/graph/schema.py` for parallel truths branching
- [x] T031 [US5] Build `delete_node` and `delete_meta_type` tools enforcing `[APPROVAL_REQUIRED]` response format on structural teardowns in `src/mcp_server/tools/ontology.py`

---

## Phase 8: User Story 6 - Function Objects (Priority: P3)

**Goal**: Represent executable ETL logic securely inside the graph that governs Object Nodes without burying logic in properties.

**Independent Test**: End-to-end execution of `create_function`, query retrieval, and `attach_function_to_nodes` mapping to a pre-defined domain node.

### Tests for User Story 6

- [x] T032 [P] [US6] Integration test for comprehensive Function Objects workflow in `tests/integration/test_function_objects_e2e.py`

### Implementation for User Story 6

- [x] T033 [US6] Implement CRUD mechanics for Functions in `src/graph/queries.py`
- [x] T034 [US6] Build tool endpoints `create_function`, `query_functions`, and `attach_function_to_nodes` in `src/mcp_server/tools/functions.py`
- [x] T035 [US6] Register tools inside the FastMCP wrapper in `src/mcp_server/server.py`

---

## Final Phase: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [x] T036 Code cleanup and strict type-hint alignment
- [x] T037 Perform FastMCP end-to-end validation of the SSE server mapping via the `.quickstart.md` invocations
- [x] T038 Review all payload assertions to absolutely confirm no uncompressed `JSON` leaks

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies
- **Foundational (Phase 2)**: Depends on Setup 
- **User Stories (Phase 3-8)**: All depend on Foundational (Phase 2). Should be completed in order.
- **Polish (Final)**: Depends on all User Story tasks.

### Supported Parallel Execution Strategies

```bash
# Foundational Example
T004 (Core Models) & T005 (FalkorDB Client Setup) & T007 (Docker test fixtures) # Executed at same time

# Story Implementation Example
T012 (Schema testing) & T013 (Schema Pydantic creation internals) # Model generation is separate from testing implementations
```
