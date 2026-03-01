# Contract: Neo4j Adapter Interface Specification

**Feature**: Neo4j Graph Database Migration  
**Date**: 2026-03-01  
**Status**: Specification (to be implemented)

## Purpose

Define the public interface contract for the Neo4j adapter layer, ensuring 100% backward compatibility with existing FalkorDB client usage patterns. All downstream code (dashboard API routes, MCP tools, test fixtures) MUST continue to function without modification after migration.

## Scope

This contract applies to:
- **Module**: `src/graph/neo4j_client.py` (new)
- **Consumers**: `src/dashboard/graph_service.py`, `src/dashboard/health_service.py`, `src/mcp_server/tools/*`, `tests/**`

This contract does NOT apply to:
- Internal Neo4j driver implementation details
- Schema bootstrap logic (internal to adapter)
- Connection retry mechanisms (internal to adapter)

## Interface Contract

### Function: `get_graph(graph_name: str = None) -> GraphInterface`

**Signature**:
```python
def get_graph(graph_name: str = None) -> GraphInterface:
    """Return (and lazily initialize) the named graph handle.
    
    Args:
        graph_name: Database name. If None, uses NEO4J_DATABASE env var or "neo4j" default.
    
    Returns:
        GraphInterface: Object providing query() method for Cypher execution.
    
    Raises:
        RuntimeError: If Neo4j connection fails after retry exhaustion.
        RuntimeError: If schema bootstrap fails (constraints/indexes cannot be created).
    """
```

**Behavioral Contract**:
1. **Idempotency**: Multiple calls with same `graph_name` MUST return the same instance (singleton pattern)
2. **Lazy Initialization**: Connection MUST NOT be established until first `get_graph()` call
3. **Automatic Bootstrap**: Schema constraints and indexes MUST be created automatically on first call
4. **Retry Logic**: Transient connection failures MUST trigger exponential backoff (3 retries, max 5s total)
5. **Explicit Failures**: Permanent failures (auth errors, missing database) MUST raise clear RuntimeError with actionable message

**Test Contract**:
```python
# Test case 1: Singleton behavior
graph1 = get_graph("test_db")
graph2 = get_graph("test_db")
assert graph1 is graph2  # MUST be same instance

# Test case 2: Different databases
graph_a = get_graph("db_a")
graph_b = get_graph("db_b")
assert graph_a is not graph_b  # MUST be different instances

# Test case 3: Connection failure
with pytest.raises(RuntimeError, match="Neo4j unavailable"):
    get_graph("nonexistent")  # MUST fail with clear message
```

---

### Interface: GraphInterface

**Purpose**: Provide Cypher query execution with FalkorDB-compatible result format.

**Method: `query(cypher: str, params: dict = None) -> ResultSetInterface`**

**Signature**:
```python
def query(cypher: str, params: dict = None) -> ResultSetInterface:
    """Execute a Cypher query with parameter binding.
    
    Args:
        cypher: Cypher query string (MUST NOT be empty).
        params: Optional parameter mapping for query (default: None).
    
    Returns:
        ResultSetInterface: Iterable result set with .result_set list attribute.
    
    Raises:
        ValueError: If cypher is empty or params is not dict/None.
        RuntimeError: If query execution fails (connection drop, syntax error).
    """
```

**Behavioral Contract**:
1. **Parameter Binding**: Parameters MUST be passed to Neo4j driver (prevent injection attacks)
2. **Eager Evaluation**: Result MUST be fully materialized before return (FalkorDB behavior)
3. **Error Propagation**: Neo4j syntax errors MUST be wrapped in RuntimeError with original message
4. **Transaction Semantics**: Read queries use auto-commit; write queries use explicit transactions

**FalkorDB Compatibility Requirements**:
```python
# Existing code pattern that MUST continue working:
result = graph.query("MATCH (n:MetaType) RETURN n", params={})

# Pattern 1: Iterate as list of lists (FalkorDB .result_set attribute)
for row in result.result_set:
    node = row[0]  # Access by index
    print(node['name'])

# Pattern 2: Iterate as dictionaries (FalkorDB alternate pattern)
for row in result:
    node = row['n']  # Access by Cypher alias
    print(node['name'])
```

**Test Contract**:
```python
# Test case 1: Simple query
result = graph.query("RETURN 1 AS x")
assert result.result_set == [[1]]

# Test case 2: Parameterized query
result = graph.query("RETURN $val AS x", {"val": 42})
assert result.result_set == [[42]]

# Test case 3: Node query with properties
graph.query("CREATE (n:Test {name: 'Alice'})")
result = graph.query("MATCH (n:Test) RETURN n")
assert result.result_set[0][0]['name'] == 'Alice'

# Test case 4: Empty params (MUST NOT raise error)
result = graph.query("RETURN 1", params=None)
assert result.result_set == [[1]]
```

---

### Interface: ResultSetInterface

**Purpose**: Provide FalkorDB-compatible result iteration.

**Attributes**:
- `result_set`: `list[list[Any]]` — Materialized rows as list of lists (FalkorDB compatibility)

**Methods**:
- `__iter__() -> Iterator[dict]` — Iterate rows as dictionaries with Cypher aliases as keys

**Behavioral Contract**:
1. **Dual Access**: MUST support both `.result_set` list access AND dictionary iteration
2. **Node Conversion**: Neo4j `Node` objects MUST be converted to dicts with properties
3. **Relationship Conversion**: Neo4j `Relationship` objects MUST be converted to dicts with type and properties
4. **Type Coercion**: Neo4j-specific types (DateTime, Point, Duration) MUST be converted to Python primitives

**Test Contract**:
```python
# Test case 1: result_set attribute exists and is list
result = graph.query("RETURN 1 AS x, 2 AS y")
assert isinstance(result.result_set, list)
assert result.result_set == [[1, 2]]

# Test case 2: Dictionary iteration
result = graph.query("RETURN 1 AS x")
for row in result:
    assert isinstance(row, dict)
    assert row['x'] == 1

# Test case 3: Node property access
graph.query("CREATE (n:Test {id: 123, name: 'Bob'})")
result = graph.query("MATCH (n:Test) RETURN n")
node = result.result_set[0][0]
assert node['id'] == 123
assert node['name'] == 'Bob'
```

---

## Environment Configuration Contract

**Required Environment Variables**:

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `NEO4J_URI` | `str` | (none) | Neo4j connection URI (e.g., "bolt://localhost:7687"). MUST be set for Neo4j to be used. |
| `NEO4J_USER` | `str` | (none) | Neo4j authentication username. MUST be set. |
| `NEO4J_PASSWORD` | `str` | (none) | Neo4j authentication password. MUST be set. MUST NOT be logged. |
| `NEO4J_DATABASE` | `str` | "neo4j" | Target database name. OPTIONAL. |

**Validation Contract**:
```python
# Test case 1: Missing NEO4J_URI raises clear error
os.environ.pop("NEO4J_URI", None)
with pytest.raises(RuntimeError, match="NEO4J_URI not set"):
    get_graph()

# Test case 2: Invalid URI raises clear error
os.environ["NEO4J_URI"] = "http://invalid"
with pytest.raises(RuntimeError, match="Invalid URI protocol"):
    get_graph()

# Test case 3: Missing credentials raises clear error
os.environ["NEO4J_URI"] = "bolt://localhost:7687"
os.environ.pop("NEO4J_USER", None)
with pytest.raises(RuntimeError, match="NEO4J_USER not set"):
    get_graph()
```

---

## Schema Bootstrap Contract

**Constraints Created** (idempotent CREATE IF NOT EXISTS):
```cypher
CREATE CONSTRAINT metatype_unique_name IF NOT EXISTS
FOR (m:MetaType) REQUIRE m.name IS UNIQUE;

CREATE CONSTRAINT objectnode_unique_id IF NOT EXISTS
FOR (o:ObjectNode) REQUIRE o.node_id IS UNIQUE;

CREATE CONSTRAINT auditlog_unique_id IF NOT EXISTS
FOR (a:HumanAuditLog) REQUIRE a.audit_id IS UNIQUE;
```

**Indexes Created** (idempotent CREATE IF NOT EXISTS):
```cypher
CREATE INDEX objectnode_domain_scope IF NOT EXISTS
FOR (o:ObjectNode) ON (o.domain_scope);

CREATE INDEX objectnode_meta_type IF NOT EXISTS
FOR (o:ObjectNode) ON (o.meta_type);
```

**Behavioral Contract**:
1. **Automatic Execution**: Bootstrap MUST run automatically on first `get_graph()` call
2. **Idempotency**: Re-running bootstrap MUST NOT fail if constraints/indexes already exist
3. **Atomicity**: If any constraint/index creation fails, entire bootstrap MUST fail (no partial state)
4. **Logging**: Each constraint/index creation MUST log success/skip message
5. **Failure Propagation**: Bootstrap failures MUST raise RuntimeError blocking all queries

**Test Contract**:
```python
# Test case 1: Bootstrap creates constraints
graph = get_graph("test_db")
result = graph.query("SHOW CONSTRAINTS")
constraint_names = [row[0] for row in result.result_set]
assert "metatype_unique_name" in constraint_names
assert "objectnode_unique_id" in constraint_names
assert "auditlog_unique_id" in constraint_names

# Test case 2: Bootstrap creates indexes
result = graph.query("SHOW INDEXES")
index_names = [row[0] for row in result.result_set]
assert "objectnode_domain_scope" in index_names
assert "objectnode_meta_type" in index_names

# Test case 3: Repeat bootstrap is idempotent (no errors)
graph = get_graph("test_db")  # Should not raise error
```

---

## Backward Compatibility Contract

**Zero-Change Guarantee**: The following existing code patterns MUST continue working without modification:

### Dashboard Graph Service
```python
# src/dashboard/graph_service.py
from src.graph.client import get_graph

def get_nodes_by_scope(domain_scope: str):
    graph = get_graph()
    cypher = "MATCH (n:ObjectNode {domain_scope: $scope}) RETURN n LIMIT 100"
    result = graph.query(cypher, {"scope": domain_scope})
    return [row[0] for row in result.result_set]  # MUST work
```

### MCP Tool Query Execution
```python
# src/mcp_server/tools/query_metadata.py
from src.graph.client import get_graph

def execute_tool_query(cypher: str, params: dict):
    graph = get_graph()
    result = graph.query(cypher, params)
    # Iterate as dict (existing pattern)
    nodes = []
    for row in result:
        nodes.append(row['n'])  # MUST work
    return nodes
```

### Test Fixture
```python
# tests/conftest.py
from src.graph.client import get_graph

@pytest.fixture
def test_graph():
    graph = get_graph("test_db_12345")
    yield graph
    # Cleanup (existing pattern)
    graph.query("MATCH (n) DETACH DELETE n")  # MUST work
```

---

## Performance Contract

**Latency Requirements**:
- First `get_graph()` call (cold start with bootstrap): < 500ms
- Subsequent `get_graph()` calls (warm): < 1ms (singleton lookup)
- Simple query (`RETURN 1`): < 10ms
- Complex query (3-hop traversal, 100 nodes): < 200ms
- Connection retry (transient failure): < 5s total

**Resource Limits**:
- Connection pool size: 10 connections (Neo4j driver default)
- Query timeout: 30s (Neo4j driver default)
- Max result set size: 10,000 nodes (enforced by downstream LIMIT clauses)

---

## Compliance Verification

**Contract Adherence Checklist**:

- [ ] `get_graph()` returns singleton instance for same database name
- [ ] `get_graph()` creates schema constraints/indexes automatically
- [ ] `graph.query()` accepts Cypher string and dict params
- [ ] `result.result_set` returns list of lists (FalkorDB compat)
- [ ] `result` is iterable as dicts with Cypher aliases (FalkorDB compat)
- [ ] Neo4j nodes converted to dicts with properties
- [ ] Neo4j DateTime/Point types converted to primitives
- [ ] Missing `NEO4J_URI` raises clear RuntimeError
- [ ] Invalid credentials raise clear RuntimeError
- [ ] Connection retry uses exponential backoff (3 attempts, 5s max)
- [ ] All existing dashboard/MCP tool code works without changes
- [ ] Test fixtures work without modification

**Test Coverage Requirement**: 100% of contract test cases MUST pass before merge to main.

---

## Deprecation & Migration Notes

**No Deprecations**: This is a pure backend substitution. No APIs are deprecated.

**Migration Path**: 
1. Set `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` environment variables
2. Restart application
3. Verify dashboard loads (indicates Neo4j connection successful)
4. Verify MCP tools function (indicates queries executing correctly)
5. Optionally remove FalkorDB dependencies (after transition period)
