# Phase 1: Data Model — Neo4j Migration Entities

**Feature**: Neo4j Graph Database Migration  
**Date**: 2026-03-01  
**Prerequisites**: [research.md](research.md) complete

## Overview

This document defines the adapter layer entities and their relationships for the Neo4j migration. The goal is to maintain full API compatibility with the existing FalkorDB client while swapping the underlying persistence layer.

## Adapter Layer Entities

### Entity: Neo4jClient

**Purpose**: Singleton wrapper around `neo4j.GraphDatabase.driver` providing connection pooling, retry logic, and lifecycle management.

**Attributes**:
- `_driver`: `neo4j.Driver` — Shared connection pool (lazy-initialized)
- `uri`: `str` — Neo4j connection URI (e.g., "bolt://localhost:7687")
- `user`: `str` — Neo4j authentication username
- `password`: `str` — Neo4j authentication password (never logged)
- `database`: `str` — Target database name (default: "neo4j")
- `max_retry_time`: `int` — Max seconds for retry logic (default: 5)

**Operations**:
- `get_driver() -> neo4j.Driver` — Return (and lazily initialize) the shared driver instance
- `close() -> None` — Explicitly close the driver connection pool
- `verify_connectivity() -> bool` — Execute simple query to test connection (called on first access)

**Lifecycle**:
- Created once per application runtime (singleton pattern)
- Automatically initialized on first `get_graph()` call
- Connection pool closed on application shutdown

**Validation Rules**:
- URI MUST start with "bolt://" or "neo4j://" protocol
- User and password MUST be non-empty strings
- Database name MUST NOT be "system" (reserved)

**Relationships**:
- **Creates** → `Neo4jGraph` instances (one per database)
- **Wraps** → `neo4j.Driver` (official Neo4j Python driver)

---

### Entity: Neo4jGraph

**Purpose**: Session manager providing a FalkorDB-compatible query interface for executing Cypher queries with parameter binding.

**Attributes**:
- `_client`: `Neo4jClient` — Reference to parent client
- `database`: `str` — Target database name
- `_bootstrapped`: `bool` — Flag tracking whether schema constraints/indexes created

**Operations**:
- `query(cypher: str, params: dict = None) -> Neo4jResultSet` — Execute Cypher query with parameter binding, return result set
- `_ensure_bootstrap() -> None` — Idempotently create schema constraints and indexes on first query
- `_create_constraints() -> None` — Execute CREATE CONSTRAINT IF NOT EXISTS for MetaType, ObjectNode, HumanAuditLog
- `_create_indexes() -> None` — Execute CREATE INDEX IF NOT EXISTS for domain_scope, meta_type fields

**FalkorDB Compatibility Interface**:
```python
# Existing FalkorDB interface that MUST be preserved:
result = graph.query("MATCH (n:MetaType) RETURN n", params={})
# Returns iterable result set with .result_set attribute containing rows
```

**Validation Rules**:
- Cypher string MUST NOT be empty
- Parameters MUST be dict or None
- Bootstrap MUST succeed before any queries execute (fail-fast on schema creation errors)

**Relationships**:
- **Executes queries on** → `neo4j.Session` (via driver)
- **Returns** → `Neo4jResultSet` instances
- **Creates on bootstrap** → Schema constraints (`:MetaType`, `:ObjectNode`, `:HumanAuditLog`)
- **Creates on bootstrap** → Indexes (`domain_scope`, `meta_type` on `:ObjectNode`)

---

### Entity: Neo4jResultSet

**Purpose**: Adapter converting Neo4j `Result` objects to FalkorDB-compatible dict-based result sets for transparent downstream consumption.

**Attributes**:
- `_result`: `neo4j.Result` — Underlying Neo4j result cursor
- `result_set`: `list[list[Any]]` — Materialized rows (FalkorDB compatibility)

**Operations**:
- `__iter__() -> Iterator[dict]` — Iterate over result rows as dictionaries
- `_convert_node(node: neo4j.Node) -> dict` — Convert Neo4j node to dict with properties
- `_convert_relationship(rel: neo4j.Relationship) -> dict` — Convert Neo4j relationship to dict

**FalkorDB Compatibility Interface**:
```python
# Existing code expects:
for row in result.result_set:
    node_data = row[0]  # Access by index
    # OR
for row in result:
    node_data = row['n']  # Access by key
```

**Validation Rules**:
- MUST materialize all rows eagerly (FalkorDB behavior) to prevent cursor lifecycle issues
- Node/relationship conversion MUST preserve all properties
- MUST handle Neo4j types (Path, DateTime, Point) gracefully (convert to strings/primitives)

**Relationships**:
- **Wraps** → `neo4j.Result` objects
- **Returned by** → `Neo4jGraph.query()`

---

## Graph Data Entities (Unchanged)

These entities exist in the graph database and are NOT affected by the backend migration. Documented here for completeness.

### Node: MetaType

**Purpose**: Pydantic schema definition for dynamic object types (e.g., "Table", "Column", "Dashboard").

**Properties**:
- `name`: `str` — Unique type identifier
- `health_score`: `float` — Validation success metric (default: 1.0, range: [0.0, 1.0])
- `required_fields`: `list[str]` — Field names required for this type
- `field_types`: `dict[str, str]` — Field name → Pydantic type mapping

**Constraints (Neo4j)**:
```cypher
CREATE CONSTRAINT metatype_unique_name IF NOT EXISTS
FOR (m:MetaType) REQUIRE m.name IS UNIQUE
```

**Unchanged by Migration**: Yes — same Cypher `CREATE CONSTRAINT` syntax in both FalkorDB and Neo4j

---

### Node: ObjectNode

**Purpose**: Instance of a metadata object (e.g., specific Table "customer_dim").

**Properties**:
- `node_id`: `str` — Unique identifier (UUID)
- `meta_type`: `str` — Type name (references MetaType.name)
- `domain_scope`: `str` — Visibility scope ("Finance", "Marketing", "Global")
- `[dynamic fields]`: varies — Type-specific properties

**Constraints (Neo4j)**:
```cypher
CREATE CONSTRAINT objectnode_unique_id IF NOT EXISTS
FOR (o:ObjectNode) REQUIRE o.node_id IS UNIQUE
```

**Indexes (Neo4j)**:
```cypher
CREATE INDEX objectnode_domain_scope IF NOT EXISTS
FOR (o:ObjectNode) ON (o.domain_scope)

CREATE INDEX objectnode_meta_type IF NOT EXISTS
FOR (o:ObjectNode) ON (o.meta_type)
```

**Unchanged by Migration**: Yes — semantic meaning identical; only storage backend differs

---

### Node: HumanAuditLog

**Purpose**: Audit trail for human actions through dashboard (Rule 5.7).

**Properties**:
- `audit_id`: `str` — Unique identifier
- `profile_id`: `str` — Acting user
- `domain_scope`: `str` — User's active scope
- `action_type`: `str` — "READ" or "MUTATION"
- `timestamp`: `str` — ISO-8601 UTC timestamp
- `human_session_id`: `str` — Session token or client IP

**Constraints (Neo4j)**:
```cypher
CREATE CONSTRAINT auditlog_unique_id IF NOT EXISTS
FOR (a:HumanAuditLog) REQUIRE a.audit_id IS UNIQUE
```

**Unchanged by Migration**: Yes — audit logging behavior identical

---

### Relationship: Stigmergic Edge

**Purpose**: AI-created semantic connections with confidence scoring and decay mechanics (Rule 4.1-4.5).

**Properties**:
- `confidence_score`: `float` — Confidence metric (range: [0.0, 1.0], initial: 0.5)
- `last_accessed`: `str` — ISO-8601 UTC timestamp
- `rationale_summary`: `str` — Human-readable explanation of why edge created
- `created_by_prompt_hash`: `str` — Provenance hash (Rule 4.4)
- `decay_hold_until`: `str | null` — Optional moratorium timestamp (Rule 4.7)

**Decay Rules**:
- If `last_accessed` > 30 days ago AND no `decay_hold_until` in future → decrement `confidence_score`
- If `confidence_score` < 0.1 → delete edge (prune hallucinations)

**Unchanged by Migration**: Yes — decay logic uses standard Cypher datetime functions supported by both backends

---

## State Transitions

### Schema Bootstrap Lifecycle

1. **Initial State**: Neo4j database exists but has no constraints/indexes
2. **First `get_graph_client()` Call**: 
   - `Neo4jClient` initializes driver
   - `Neo4jGraph` created
   - `_ensure_bootstrap()` called automatically
3. **Bootstrap Execution**:
   - Execute `CREATE CONSTRAINT IF NOT EXISTS` for all MetaType, ObjectNode, HumanAuditLog constraints
   - Execute `CREATE INDEX IF NOT EXISTS` for domain_scope, meta_type indexes
   - Set `_bootstrapped = True`
4. **Subsequent Calls**: Skip bootstrap (idempotent checks fast)

### Connection Retry Lifecycle

1. **Query Attempt**: `query(cypher, params)` called
2. **Connection Failure**: `neo4j.exceptions.ServiceUnavailable` raised
3. **Retry Logic**: Exponential backoff (0.5s, 1s, 2s) for max 3 attempts
4. **Success**: Return result set
5. **Exhausted**: Raise RuntimeError with clear message ("Neo4j unavailable after 3 retries")

---

## Validation Summary

| Entity | Validation Rules | Enforcement Point |
|--------|------------------|-------------------|
| Neo4jClient | URI protocol check, non-empty credentials | `__init__()` constructor |
| Neo4jGraph | Non-empty Cypher, bootstrap success | `query()` entry point |
| Neo4jResultSet | Materialized rows, type conversion | `__iter__()` method |
| MetaType | Unique name constraint | Neo4j database (CREATE CONSTRAINT) |
| ObjectNode | Unique node_id, indexed domain/type | Neo4j database (CREATE CONSTRAINT + INDEX) |
| HumanAuditLog | Unique audit_id | Neo4j database (CREATE CONSTRAINT) |

---

## Migration Impact

**Changed Entities**: Neo4jClient, Neo4jGraph, Neo4jResultSet (new adapter layer)

**Unchanged Entities**: MetaType, ObjectNode, HumanAuditLog, Stigmergic edges (semantic meaning preserved)

**Backward Compatibility**: 100% — Downstream code (dashboard, MCP tools) uses same query interface
