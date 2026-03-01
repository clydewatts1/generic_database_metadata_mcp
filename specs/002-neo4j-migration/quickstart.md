# Quickstart: Neo4j Migration Setup

**Feature**: Neo4j Graph Database Migration  
**Audience**: Developers setting up local Neo4j environment  
**Time to Complete**: ~10 minutes

## Prerequisites

- Windows 11, macOS, or Linux
- Python 3.11+ with virtualenv activated
- Neo4j Community Edition v5.x installed locally

## 1. Install Neo4j Community Edition

### Option A: Windows (Installer)

1. Download Neo4j Desktop from https://neo4j.com/download/
2. Run installer, launch Neo4j Desktop
3. Create new project → Add local DBMS → Neo4j 5.x
4. Set password (remember this for step 3)
5. Start DBMS (green play button)

**Bolt URI**: `bolt://localhost:7687`  
**Database**: `neo4j` (default)

### Option B: macOS (Homebrew)

```bash
brew install neo4j
neo4j start
# Follow prompts to set password
```

**Bolt URI**: `bolt://localhost:7687`

### Option C: Linux (Debian/Ubuntu)

```bash
wget -O - https://debian.neo4j.com/neotechnology.gpg.key | apt-key add -
echo 'deb https://debian.neo4j.com stable latest' > /etc/apt/sources.list.d/neo4j.list
apt-get update
apt-get install neo4j
systemctl start neo4j
# Set password: cypher-shell -u neo4j -p neo4j (initial), then SET PASSWORD
```

**Bolt URI**: `bolt://localhost:7687`

### Verification

Open browser to http://localhost:7474 (Neo4j Browser). You should see the query interface. Run:
```cypher
RETURN "Hello Neo4j!" AS message
```

If successful, Neo4j is ready.

---

## 2. Install Python Dependencies

From project root (`generic_database_metadata_mcp/`):

```powershell
# Activate virtual environment
.venv\Scripts\Activate.ps1  # Windows PowerShell
# OR
source .venv/bin/activate    # macOS/Linux

# Install Neo4j driver
pip install neo4j>=5.0.0

# Verify installation
python -c "import neo4j; print(neo4j.__version__)"
# Expected: 5.x.x
```

---

## 3. Configure Environment Variables

### Windows PowerShell

```powershell
$env:NEO4J_URI = "bolt://localhost:7687"
$env:NEO4J_USER = "neo4j"
$env:NEO4J_PASSWORD = "your-password-here"  # Password you set during Neo4j installation
$env:NEO4J_DATABASE = "neo4j"  # Optional, defaults to "neo4j"
```

### macOS/Linux Bash

```bash
export NEO4J_URI="bolt://localhost:7687"
export NEO4J_USER="neo4j"
export NEO4J_PASSWORD="your-password-here"
export NEO4J_DATABASE="neo4j"  # Optional
```

**Security Note**: Do NOT commit passwords to version control. Use `.env` files (gitignored) or secret management tools in production.

---

## 4. Verify Migration Setup

### Test Connection

```powershell
# From project root
python -c "
import os
from neo4j import GraphDatabase

uri = os.getenv('NEO4J_URI')
user = os.getenv('NEO4J_USER')
password = os.getenv('NEO4J_PASSWORD')

driver = GraphDatabase.driver(uri, auth=(user, password))
driver.verify_connectivity()
print('✅ Neo4j connection successful!')
driver.close()
"
```

**Expected Output**: `✅ Neo4j connection successful!`

**Troubleshooting**:
- `ServiceUnavailable`: Neo4j not running → Start Neo4j service
- `AuthError`: Wrong password → Check `NEO4J_PASSWORD` env var matches Neo4j password
- `ConnectionRefused`: Wrong port → Verify `bolt://localhost:7687` (not 7474, which is HTTP)

---

## 5. Run Dashboard with Neo4j

```powershell
# Start dashboard server (will auto-create schema on first connection)
python -m src.dashboard.server
```

**Expected Output**:
```
INFO: Connecting to Neo4j at bolt://localhost:7687
INFO: Neo4j connection verified
INFO: Creating schema constraints...
INFO: Created constraint: metatype_unique_name
INFO: Created constraint: objectnode_unique_id
INFO: Created constraint: auditlog_unique_id
INFO: Creating indexes...
INFO: Created index: objectnode_domain_scope
INFO: Created index: objectnode_meta_type
INFO: Schema bootstrap complete
INFO: Uvicorn running on http://0.0.0.0:8080
```

**Access Dashboard**: http://localhost:8080

**Authenticate** with JWT token (from earlier session):
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJkb21haW5fc2NvcGUiOiJkZWZhdWx0IiwicHJvZmlsZV9pZCI6ImFkbWluIiwiZXhwIjoxNzc0OTczOTUwfQ.mCKkNL6yES4GwVX2lTHzS5svWA6l_gD-DzwXFE90ljI
```

---

## 6. Run Tests Against Neo4j

```powershell
# Run all tests
pytest tests/ -v

# Run integration tests only (uses Neo4j)
pytest tests/integration/ -v

# Run with test database isolation
pytest tests/integration/test_dashboard_api.py -v
# Each test creates ephemeral test database
```

**Expected**: All tests pass (green). Test databases auto-created and auto-cleaned.

**Troubleshooting**:
- `Test databases not created`: Check Neo4j user has CREATE DATABASE privilege
- `Tests hang`: Check `NEO4J_URI` reachable, firewall allows port 7687

---

## 7. Verify Schema in Neo4j Browser

Open http://localhost:7474, run:

```cypher
SHOW CONSTRAINTS
```

**Expected Output**:
```
metatype_unique_name
objectnode_unique_id
auditlog_unique_id
```

Run:
```cypher
SHOW INDEXES
```

**Expected Output**:
```
objectnode_domain_scope
objectnode_meta_type
```

✅ **Schema bootstrap successful!**

---

## 8. Optional: Seed Test Data

```powershell
# Create sample MetaType and ObjectNode
python -c "
from src.graph.client import get_graph

graph = get_graph()

# Create MetaType (Pydantic schema definition)
graph.query('''
CREATE (m:MetaType {
    name: 'Table', 
    health_score: 1.0,
    required_fields: ['name', 'database']
})
''')

# Create ObjectNode instance
graph.query('''
CREATE (o:ObjectNode {
    node_id: 'table_001',
    meta_type: 'Table',
    domain_scope: 'Finance',
    name: 'customer_dim',
    database: 'prod_analytics'
})
''')

print('✅ Test data seeded')
"
```

Verify in Neo4j Browser:
```cypher
MATCH (n) RETURN n LIMIT 10
```

You should see the `MetaType` and `ObjectNode` nodes.

---

## 9. Switch Back to FalkorDB (Optional)

To test backward compatibility, unset `NEO4J_URI` and start FalkorDB:

```powershell
# Unset Neo4j env vars
Remove-Item Env:\NEO4J_URI
Remove-Item Env:\NEO4J_USER
Remove-Item Env:\NEO4J_PASSWORD

# Start FalkorDB (Docker)
docker run -p 6379:6379 -d falkordb/falkordb

# Restart dashboard
python -m src.dashboard.server
# Should connect to FalkorDB at localhost:6379
```

Dashboard and MCP tools should work identically.

---

## Common Issues

### "Neo4j connection unavailable after 3 retries"

**Cause**: Neo4j not running or wrong URI  
**Fix**: 
1. Verify Neo4j service running: `systemctl status neo4j` (Linux) or check Neo4j Desktop
2. Check `NEO4J_URI` matches actual URI: `echo $env:NEO4J_URI`
3. Test direct connection: `cypher-shell -u neo4j -p <password>`

### "AuthenticationError: The client is unauthorized"

**Cause**: Wrong password or user  
**Fix**: 
1. Reset password in Neo4j Browser or via `cypher-shell ALTER CURRENT USER SET PASSWORD FROM 'old' TO 'new'`
2. Update `NEO4J_PASSWORD` env var
3. Restart application

### "CREATE CONSTRAINT failed: Permission denied"

**Cause**: Neo4j user lacks CREATE DATABASE or admin privileges  
**Fix**:
1. Grant privileges in Neo4j Browser: `GRANT CREATE ON DATABASE * TO neo4j`
2. OR use admin user credentials

### "Tests fail with 'database not found'"

**Cause**: Test trying to create database but lacking privileges  
**Fix**: 
1. Use Neo4j default database: `NEO4J_DATABASE=neo4j`
2. OR grant CREATE DATABASE privilege to test user

---

## Next Steps

- **Read**: [data-model.md](data-model.md) — Understand adapter layer entities
- **Read**: [contracts/neo4j-adapter-interface.md](contracts/neo4j-adapter-interface.md) — Review API contract
- **Explore**: Neo4j Browser (http://localhost:7474) — Query graph data directly
- **Monitor**: Application logs for `INFO: Connecting to Neo4j` messages

---

## Summary Checklist

- [x] Neo4j Community Edition v5.x installed and running
- [x] Python `neo4j>=5.0.0` package installed
- [x] Environment variables set (`NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`)
- [x] Connection verified (test script passed)
- [x] Dashboard starts successfully (schema bootstrap logged)
- [x] Dashboard accessible at http://localhost:8080
- [x] Tests pass against Neo4j backend
- [x] Schema constraints/indexes visible in Neo4j Browser

**Estimated Setup Time**: 10 minutes ✅  
**You are ready to develop!**
