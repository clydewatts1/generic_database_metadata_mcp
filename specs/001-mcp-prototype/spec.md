# Feature Specification: Stigmergic MCP Metadata Server Prototype

**Feature Branch**: `001-mcp-prototype`  
**Created**: 2026-02-27  
**Status**: Complete  
**Input**: User description: "Implement the feature specification based on the updated constitution. I want to build a working prototype based on the constitution"

## Technology Stack

**Database**: FalkorDBLite (lightweight graph database)  
- Lightweight alternative to heavy SQL/OLAP systems (Teradata, PostgreSQL)
- Fast graph traversals using Cypher query language
- Context-frugal by design (bounded queries, pagination support)
- Deployed via Docker for reproducible dev/test/prod environments

**API Transport**: HTTP/SSE (Server-Sent Events) on port 8000  
**Python Version**: 3.11+  
**Key Dependencies**: mcp (MCP SDK), falkordb (client), pydantic (v2), freezegun (testing)

## Clarifications

### Session 2026-02-27
- Q: How should nodes (Object Nodes and MetaTypes) be uniquely identified in the graph? → A: UUID v4
- Q: In SC-001, what is the specific maximum size allowed for the "minimal response payload size"? → A: < 10KB
- Q: To keep the prototype focused, what should be explicitly marked as out-of-scope? → A: Real-time streaming & binary data
- Q: What is the expected maximum size of the graph (number of nodes/edges) for this prototype? → A: Small (< 100k nodes/edges)
- Q: For the prototype, what should be the default biological decay rate for Stigmergic Edges? → A: Aggressive (hours/days)

### Session 2026-02-27 (Consistency Review)
- Q: For Stigmergic Edge biological decay, what should be the exact threshold and decay rate? → A: 7-day threshold, 0.02 decay per 24h (edge unused for 7+ days loses 2% confidence daily, reaches pruning threshold ~50 days)
- Q: What specific operations trigger [APPROVAL_REQUIRED] for Global-scoped resources? → A: Node deletion only; property updates and edge modifications do not require approval
- Q: Function Objects are specified but lack MCP tools or tests. Should they be: → A: Implement tools (create_function, query_functions, attach_function_to_nodes)
- Q: How should a locked circuit breaker (Rule 2.8) be unlocked after 3 validation failures? → A: Via confirm_schema_heal MCP tool (requires schema fix; lockout persists until schema evolved)
- Q: For query result pagination (FR-007), what is the max nodes per page before pagination triggers? → A: Return maximum 5 nodes per page; paginate if result > 5

### Session 2026-02-28 (Clarification Review)
- Q: How should a MetaType node be structured in the graph? → A: Suggested structure (type_name, description, required_fields, field_schemas, health_score, created_at, created_by_prompt_hash)
- Q: What file format should the `bulk_ingest_seed` tool accept? → A: YAML bulk specification (modern, supports complex nested structures, avoids relational constraints of CSV)
- Q: How should observability (logging/metrics) be handled? → A: Structured JSON logging to stdout (easy parsing of metrics like payload_size without bloating payload)
- Q: How should Parallel Truths branching be executed? → A: Create new node, link to original via `[:VARIANTS]` (preserves original as umbrella term)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Genesis Seed Ingestion (Priority: P1)

As an administrator, I want to bulk ingest initial metadata (e.g., Teradata schema dumps) without overwhelming the AI context window, so that the system has a foundational graph to work with.

**Why this priority**: A cold start is required before any meaningful AI interaction or querying can occur.

**Independent Test**: Can be fully tested by providing a data file to the `bulk_ingest_seed` tool and verifying the graph is populated without returning the full graph to the AI.

**Acceptance Scenarios**:

1. **Given** an empty graph, **When** the `bulk_ingest_seed` tool is called with a valid data file path, **Then** the graph is populated with the initial nodes and edges silently, returning only a success summary.

---

### User Story 2 - Dynamic Meta-Ontology Creation and Validation (Priority: P1)

As an AI agent, I want to define new Object Types and Edge Types on the fly, and have the system automatically generate validation schemas to validate any new instances of these types before insertion.

**Why this priority**: Dynamic schema generation and strict validation are the core mechanisms ensuring data integrity in the graph.

**Independent Test**: Can be fully tested by defining a new type, attempting to insert a valid instance (succeeds), and attempting to insert an invalid instance (fails with validation error).

**Acceptance Scenarios**:

1. **Given** a running server, **When** the AI defines a new Object Type "Dashboard" with required field "url", **Then** a Pydantic model is generated and a schema node is saved.
2. **Given** the "Dashboard" type exists, **When** the AI tries to insert a Dashboard without a "url", **Then** the insertion is rejected and a validation error is returned.

---

### User Story 3 - Context-Frugal Querying and a compact format Serialization (Priority: P2)

As an AI agent, I want to query the graph and receive results that are strictly bounded in depth, paginated if too large, and serialized in a token-efficient format (a compact format), so that my context window is never overwhelmed.

**Why this priority**: Context frugality is a non-negotiable mandate to ensure the AI can operate efficiently without token exhaustion.

**Independent Test**: Can be fully tested by executing a query that matches many nodes and verifying the output is paginated and formatted in a compact format.

**Acceptance Scenarios**:

1. **Given** a populated graph, **When** a query returns more than 5 nodes, **Then** the results are paginated.
2. **Given** a query result, **When** it is returned to the AI, **Then** it is serialized using the Compact Output Serialization (a compact format) format.

---

### User Story 4 - Stigmergic Edge Creation and Reinforcement (Priority: P2)

As an AI agent, I want to create connections between Business Terms and Technical Nodes, and have the system automatically reinforce these connections when they are successfully traversed to answer user queries.

**Why this priority**: Stigmergy is the primary mechanism for organic knowledge discovery and confidence weighting.

**Independent Test**: Can be fully tested by creating an edge, querying it multiple times, and observing its confidence_score increase.

**Acceptance Scenarios**:

1. **Given** a Business Term and a Technical Node, **When** the AI maps them, **Then** a Stigmergic Edge is created with an initial confidence score (e.g., 0.5).
2. **Given** an existing Stigmergic Edge, **When** it is traversed to answer a query, **Then** its confidence score increases (up to 1.0) and its last_accessed timestamp is updated.

---

### User Story 5 - Profile-Aware Scoping and Supreme Court Escalation (Priority: P3)

As a user, I want my queries and stigmergic traces to be scoped to my domain (e.g., Finance), and I want to be explicitly prompted for approval if the AI attempts to delete or destructively modify global nodes.

**Why this priority**: Ensures security, domain isolation, and prevents catastrophic accidental deletions by the AI.

**Independent Test**: Can be fully tested by querying with a specific profile ID and verifying only scoped nodes are returned, and by attempting a destructive global action and verifying an approval payload is sent.

**Acceptance Scenarios**:

1. **Given** a user in the "Finance" domain, **When** they query the graph, **Then** only nodes within the "Finance" scope or global scope are returned.
2. **Given** an AI agent, **When** it attempts to delete a schema node, **Then** the action is blocked and an [APPROVAL_REQUIRED] payload is returned to the client.

### Edge Cases

- What happens when an AI agent repeatedly fails schema validation? (Circuit Breaker triggers after 3 failures, locking the action and requiring human intervention).
- What happens when a Stigmergic Edge is not accessed for a long time? (Biological Decay reduces its confidence score, eventually pruning it if it falls below the threshold).
- What happens when a technical node is deprecated? (Cascading Wither applies a massive decay penalty to all attached stigmergic edges).
- What happens when conflicting stigmergic connections arise from different domains? (Parallel Truths branch the node into domain-specific versions linked via `[:VARIANTS]`).

## Requirements *(mandatory)*

### Out of Scope

- Real-time streaming ingestion.
- Binary data storage.

### Dependencies and Assumptions

- **Assumption**: The underlying graph database can handle dynamic schema updates without significant downtime.
- **Assumption**: The AI agent has the capability to parse and understand the compact serialization format.
- **Assumption**: The expected maximum size of the graph for this prototype is small (< 100k nodes/edges).
- **Dependency**: Requires an authentication/authorization mechanism to provide the profile_id and domain_scope for scoping.


### Functional Requirements

- **FR-001**: System MUST provide a `bulk_ingest_seed` tool for initial data loading without returning the full graph. Ingestion payloads MUST be formatted as a YAML bulk specification to support modern, complex nested structures without relational constraints.
- **FR-002**: System MUST allow dynamic registration of Object Types and Edge Types.
- **FR-003**: System MUST generate validation schemas for registered types and validate all insertions against them.
- **FR-004**: System MUST track the health_score of schema nodes and decrement it upon validation failures.
- **FR-005**: System MUST implement a Circuit Breaker that locks actions after 3 consecutive validation failures in a session.
- **FR-006**: System MUST restrict queries to a bounded depth of 1-2 hops (inclusive range).
- **FR-007**: System MUST paginate query results returning more than 5 nodes, returning maximum 5 nodes per page.
- **FR-008**: System MUST serialize all multi-node responses using the a compact format.
- **FR-009**: System MUST create Stigmergic Edges with an initial confidence score and last_accessed timestamp.
- **FR-010**: System MUST reinforce (increase confidence) Stigmergic Edges upon successful traversal.
- **FR-011**: System MUST decay confidence scores over time using 7-day inactivity threshold and 0.02-per-24h decay rate (edges unused for 7+ days lose 2% confidence daily; minimum pruning threshold 0.1). System MUST automatically prune edges when confidence_score < 0.1.
- **FR-012**: System MUST include `rationale_summary` and `created_by_prompt_hash` on all AI-generated modifications.
- **FR-013**: System MUST apply Cascading Wither to edges attached to deprecated/deleted nodes.
- **FR-014**: System MUST inject profile_id and domain_scope into all tool invocations.
- **FR-015**: System MUST filter query results based on the user's domain scope.
- **FR-016**: System MUST branch nodes into domain-specific versions linked via `[:VARIANTS]` when high-confidence conflicts occur (Parallel Truths).
- **FR-017**: System MUST require explicit human approval for destructive modifications (deletion only; property updates do not require approval) to global nodes or MetaTypes (Supreme Court escalation via [APPROVAL_REQUIRED] payload).

### Key Entities

- **MetaType**: Defines the schema for Object Types and Edge Types, including a health_score. Uniquely identified by a UUID v4.
- **Object Node**: An instance of a MetaType, representing a Business Term or Technical Node. Uniquely identified by a UUID v4.
- **Stigmergic Edge**: A relationship between nodes, containing `confidence_score`, `last_accessed`, `rationale_summary`, and `created_by_prompt_hash`. Decays at 0.02 per 24h after 7-day inactivity threshold; pruned if confidence_score < 0.1.
- **Function Object**: Represents an ETL operation or logic transformation. Supports attach-to-node relationships and traversal queries (newly clarified as in-scope).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The `bulk_ingest_seed` tool can ingest 10,000 nodes in under 1 minute without exceeding a 10KB response payload size to the AI.
- **SC-002**: Schema validation catches 100% of schema violations before database insertion.
- **SC-003**: Query responses containing more than 5 nodes are consistently paginated (max 5 per page) and serialized in a compact format, reducing token usage by at least 40% compared to raw standard verbose formats.
- **SC-004**: Stigmergic edges unused for 7+ days automatically decay at 0.02 per 24h; edges with confidence_score < 0.1 are automatically pruned.
- **SC-005**: The Circuit Breaker successfully engages and blocks further attempts after exactly 3 validation failures; unlock only via confirm_schema_heal after evolving the MetaType schema.
- **SC-006**: Function Object tools (create_function, query_functions, attach_function_to_nodes) enable ETL operation registration and linkage to ObjectNodes.
