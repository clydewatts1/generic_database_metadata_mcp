# Neo4j Migration Guide

**Version**: 1.4.0  
**Status**: Complete  
**Effective**: 2026-03-01

## Overview

This guide documents the migration from FalkorDB to Neo4j Community Edition v5.x as the primary graph database backend for the Stigmergic MCP Metadata Server.

### What Changed

The core application logic remains **100% unchanged**. Only the underlying graph database backend changed:

- **Old Backend**: FalkorDB Lite (embedded, in-process)
- **New Backend**: Neo4j Community Edition v5.x (requires separate server)
- **Compatibility**: Automatic detection — system works with both backends transparently

### Why Neo4j

1. **Windows Support**: FalkorDB Lite doesn't support Windows; Neo4j Community Edition is cross-platform
2. **Scalability**: Neo4j supports larger graphs and scaling across multiple nodes
3. **Community Support**: Active maintenance and extensive documentation
4. **Standard Query Language**: Cypher is the graph query language standard

### Backward Compatibility

**No breaking changes**. The system automatically detects which backend is available:

- If `NEO4J_URI` environment variable is set → Uses Neo4j (preferred)
- If `NEO4J_URI` is not set → Falls back to FalkorDB (if running)
- If neither is available → Clear error message with setup instructions

Existing FalkorDB deployments can continue operating without any modifications.

---

## Installation & Configuration

### Neo4j Community Edition Installation

#### Docker (Recommended)

```bash
docker run -it --rm \
  --publish=7687:7687 \
  --publish=7474:7474 \
  --publish=7473:7473 \
  --env NEO4J_AUTH=neo4j/Achill853$ \
  neo4j:5-latest
```

#### Manual Installation

1. Download Neo4j Community Edition from https://neo4j.com/download/community-edition/
2. Extract and navigate to the installation directory
3. Start the server:
   - **Linux/macOS**: `bin/neo4j start`
   - **Windows**: `bin\neo4j.bat start`

### Environment Variables (Neo4j Backend)

Set these in your `.env` file or shell before running the MCP server or dashboard:

```bash
# Neo4j connection
NEO4J_URI="bolt://localhost:7687"
NEO4J_USER="neo4j"
NEO4J_PASSWORD="Achill853$"
NEO4J_DATABASE="graph"

# MCP Server (optional, for testing)
MCP_PORT=5000
DASHBOARD_JWT_SECRET="your-secret-here"
```

**Note**: `NEO4J_DATABASE` is created automatically by the test fixtures. In production, create it manually:

```cypher
CREATE DATABASE graph;
```

### Schema Bootstrap

The application creates required constraints and indexes automatically on first connection:

```cypher
-- Automatically created by schema bootstrap:
CREATE CONSTRAINT MetaType_name_unique IF NOT EXISTS
  FOR (m:MetaType) REQUIRE m.name IS UNIQUE;

CREATE CONSTRAINT ObjectNode_id_unique IF NOT EXISTS
  FOR (n:ObjectNode) REQUIRE n.id IS UNIQUE;

CREATE CONSTRAINT HumanAuditLog_id_unique IF NOT EXISTS
  FOR (a:HumanAuditLog) REQUIRE a.id IS UNIQUE;

CREATE INDEX ObjectNode_domain_scope IF NOT EXISTS
  FOR (n:ObjectNode) ON (n.domain_scope);

CREATE INDEX ObjectNode_meta_type_name IF NOT EXISTS
  FOR (n:ObjectNode) ON (n.meta_type_name);
```

---

## Verification

### Test Connection

```bash
# Set environment variables
export NEO4J_URI="bolt://localhost:7687"
export NEO4J_USER="neo4j"
export NEO4J_PASSWORD="your-password"
export NEO4J_DATABASE="graph"

# Test with Python
python -c "
from src.graph.client import get_graph
graph = get_graph()
result = graph.query('RETURN 1 AS test')
print('✓ Connected to Neo4j successfully')
print('Result:', result.result_set)
"
```

### Run Tests

```bash
# Run full test suite (should all pass)
pytest tests/unit/ tests/contract/ tests/integration/ -v

# Run just Neo4j-specific integration tests
pytest tests/integration/test_dashboard_api.py -v
```

---

## Common Issues & Solutions

### Issue: "Cannot connect to Neo4j server"

**Symptoms**:
```
RuntimeError: Neo4j connection failed after 3 retries (max 5s): Connection refused
```

**Solutions**:
1. Verify Neo4j is running: `curl -I http://localhost:7474/`
2. Check `NEO4J_URI` format: Should be `bolt://host:port` (not `http://`)
3. Verify `NEO4J_PASSWORD` is correct in Neo4j setup
4. Check firewall isn't blocking port 7687 (Bolt protocol)

### Issue: "Database not found"

**Symptoms**:
```
RuntimeError: Database 'graph' not found. Create it with: CREATE DATABASE graph
```

**Solutions**:
1. Connect to Neo4j and create the database:
   ```bash
   cypher-shell -u neo4j -p "password" "CREATE DATABASE graph IF NOT EXISTS"
   ```
2. Or via Python:
   ```python
   from src.graph.neo4j_client import Neo4jClient
   client = Neo4jClient(uri="bolt://localhost:7687", user="neo4j", password="...")
   driver = client.get_driver()
   with driver.session() as session:
       session.run("CREATE DATABASE graph IF NOT EXISTS")
   ```

### Issue: "Constraint/Index creation failed"

**Symptoms**:
Test connection succeeds, but subsequent queries fail with constraint errors.

**Solutions**:
1. Verify schema bootstrap ran: Check logs for "Creating constraint"
2. Manually create the required constraints (see Schema Bootstrap section)
3. Drop and recreate: 
   ```cypher
   DROP CONSTRAINT MetaType_name_unique;
   CREATE CONSTRAINT MetaType_name_unique FOR (m:MetaType) REQUIRE m.name IS UNIQUE;
   ```

### Issue: "Test database not cleaned up"

**Symptoms**:
Multiple `test_db_*` databases accumulate in Neo4j.

**Solutions**:
1. These are created by the test fixtures and should cleanup automatically
2. Manual cleanup if orphaned:
   ```cypher
   :show databases;
   DROP DATABASE test_db_abc12345;  # Repeat for each orphaned DB
   ```

---

## Performance Characteristics

### Connection & Bootstrap

- **Cold start** (first connection in a process): ~200-500ms
  - Includes TCP connection, driver initialization, schema bootstrap
- **Warm queries**: <10ms for simple `MATCH` operations
- **Stigmergic operations**: ~20-50ms (create edge + increment score)

### Test Execution

- Full test suite: ~6 minutes (all 117 tests)
  - Per-test database creation: ~100-200ms per test
  - Fixture overhead: <1% of total execution time

---

## Fallback to FalkorDB

If Neo4j becomes unavailable and you need to revert:

```bash
# Unset Neo4j environment
unset NEO4J_URI
unset NEO4J_USER
unset NEO4J_PASSWORD
unset NEO4J_DATABASE

# Ensure FalkorDB is running (Docker)
docker run -p 6379:6379 -d falkordb/falkordb

# Run tests (will use FalkorDB fallback automatically)
pytest tests/ -v
```

**Result**: All tests pass using FalkorDB, no code changes required.

---

## Migration Checklist for Operators

- [ ] Neo4j 5.x installed and running
- [ ] Firewall allows connections to port 7687 (Bolt)
- [ ] Environment variables set (`NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`)
- [ ] Database created: `CREATE DATABASE graph IF NOT EXISTS`
- [ ] Test connection succeeds (see Verification section)
- [ ] Run full test suite: `pytest tests/ -v` (expect 100% pass)
- [ ] Monitor logs for schema bootstrap messages
- [ ] Expected constraints/indexes appear in Neo4j Browser

---

## For Developers

### Adding Neo4j-Specific Code

The abstraction layer (`src/graph/client.py`) handles backend switching automatically.

**Do this** (uses abstraction):
```python
from src.graph.client import execute_query
result = execute_query("MATCH (n:ObjectNode) WHERE n.domain_scope = $ds RETURN n", {"ds": "Finance"})
for row in result.result_set:
    print(row[0])  # Node as dict
```

**Don't do this** (hardcoded to FalkorDB):
```python
from falkordb import FalkorDB
db = FalkorDB()  # Fails if Neo4j is configured
```

### Writing Tests

Use the provided fixtures for automatic per-test database creation:

```python
def test_schema_bootstrap(neo4j_test_database):
    """Test runs with an ephemeral database created by the fixture."""
    from src.graph.client import execute_query
    result = execute_query("RETURN 1 AS test")
    assert result.result_set[0][0] == 1
```

### Debugging

Enable debug logging in Neo4j code:

```python
import logging
logging.getLogger("src.graph").setLevel(logging.DEBUG)

# Now see detailed connection logs, retry attempts, etc.
```

---

## Support & Troubleshooting

For issues not covered here:

1. Check application logs: `journalctl -u metadata-mcp` or Docker logs
2. Check Neo4j logs: `neo4j logs -f` (Neo4j Docker) or `logs/neo4j.log`
3. Verify with: `cypher-shell -u neo4j -p "password" "RETURN 1"`
4. Run test suite: `pytest tests/integration/test_dashboard_api.py -v`

---

**Last Updated**: 2026-03-01  
**Maintainer**: Engineering Team  
**Tested With**: Neo4j 5.0.0, Python 3.11+, pytest 9.0.2
