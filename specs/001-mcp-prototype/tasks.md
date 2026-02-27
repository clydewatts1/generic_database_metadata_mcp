# Tasks: Stigmergic MCP Metadata Server Prototype

**Input**: Design documents from /specs/001-mcp-prototype/
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/mcp-tools.md, quickstart.md

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

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

- [ ] T009 [P] [US1] Write tests for MetaType registration in tests/test_ontology.py

### Implementation for User Story 1

- [ ] T010 [P] [US1] Implement MetaType graph operations (create, get) in src/graph/ontology.py
- [ ] T011 [US1] Implement dynamic Pydantic model generation in src/models/dynamic.py
- [ ] T012 [US1] Implement `register_meta_type` MCP tool in src/mcp_server/tools/ontology.py

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently.

---

## Phase 4: User Story 2 - Context-Frugal Ingestion (Priority: P1)

**Goal**: As an AI Agent, I need to ingest metadata with minimal token overhead so that I don't exhaust my context window.

**Independent Test**: Can insert a node and bulk ingest nodes, receiving only a short confirmation or TOON-formatted ID.

### Tests for User Story 2

- [ ] T013 [P] [US2] Write tests for node insertion and bulk ingest in tests/test_ingestion.py

### Implementation for User Story 2

- [ ] T014 [P] [US2] Implement Node graph operations (create, get) in src/graph/nodes.py
- [ ] T015 [US2] Implement `insert_node` MCP tool in src/mcp_server/tools/ingestion.py
- [ ] T016 [US2] Implement `bulk_ingest_seed` MCP tool in src/mcp_server/tools/ingestion.py

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently.

---

## Phase 5: User Story 3 - Stigmergic Linking (Priority: P2)

**Goal**: As an AI Agent, I need to link related metadata nodes with a strength weight so that I can build a web of associations.

**Independent Test**: Can create an edge between two nodes and verify its initial strength.

### Tests for User Story 3

- [ ] T017 [P] [US3] Write tests for edge creation in tests/test_stigmergy.py

### Implementation for User Story 3

- [ ] T018 [P] [US3] Implement Edge graph operations (create, update) in src/graph/edges.py
- [ ] T019 [US3] Implement `create_stigmergic_edge` MCP tool in src/mcp_server/tools/stigmergy.py

**Checkpoint**: All ingestion and linking user stories should now be independently functional.

---

## Phase 6: User Story 4 - Biological Decay & Retrieval (Priority: P2)

**Goal**: As an AI Agent, I need unused links to decay over time and frequently used links to strengthen, so that my context remains relevant and uncluttered.

**Independent Test**: Can query the graph, observe edge strength decay over time (using freezegun), and see strength increase upon traversal.

### Tests for User Story 4

- [ ] T020 [P] [US4] Write tests for decay logic and graph querying using freezegun in tests/test_decay.py

### Implementation for User Story 4

- [ ] T021 [P] [US4] Implement decay calculation logic in src/graph/decay.py
- [ ] T022 [US4] Implement graph traversal and querying logic in src/graph/query.py
- [ ] T023 [US4] Implement `query_graph` MCP tool in src/mcp_server/tools/query.py

**Checkpoint**: All user stories should now be independently functional.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T024 [P] Documentation updates in README.md
- [ ] T025 Run quickstart.md validation to ensure the prototype works end-to-end
- [ ] T026 Ensure all MCP tools return TOON formatted responses where applicable

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
