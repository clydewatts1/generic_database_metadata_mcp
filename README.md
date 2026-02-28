# generic_database_metadata_mcp

A **stigmergic, context-frugal metadata MCP server** backed by FalkorDB.

**Transport**: HTTP server with Server-Sent Events (SSE) on `localhost:8000`

The server exposes a graph of typed metadata objects whose edges carry a living
`confidence_score`.  Edges are reinforced every time they are traversed and
decay when left unused — embodying the "use it or lose it" principle from ant
colony stigmergy.  All responses use the compact **TOON** serialisation format
to keep LLM context windows small.

---

## Architecture

```
src/
├── graph/
│   ├── client.py        # FalkorDB connection singleton
│   ├── ontology.py      # MetaType CRUD + health-score management
│   ├── nodes.py         # ObjectNode CRUD + bulk ingest
│   ├── edges.py         # StigmergicEdge CRUD, reinforce, decay, cascading wither
│   ├── decay.py         # Decay runner (single edge + full-graph sweep)
│   └── query.py         # Bounded traversal (1-2 hops) + flat scan + pagination
├── models/
│   ├── base.py          # Pydantic models for all graph entities
│   ├── dynamic.py       # Runtime model factory (pydantic.create_model)
│   └── serialization.py # TOON compact serialiser / paginator
├── mcp_server/
│   ├── app.py           # FastMCP singleton
│   ├── server.py        # Entry point – registers all tools, calls mcp.run()
│   └── tools/
│       ├── ingestion.py # insert_node, bulk_ingest_seed (circuit breaker)
│       ├── ontology.py  # register_meta_type, list_meta_types_tool
│       ├── stigmergy.py # create_stigmergic_edge, reinforce_stigmergic_edge
│       └── query.py     # query_graph
└── utils/
    ├── logging.py       # Logger + error class hierarchy
    └── context.py       # RequestContext (profile, domain, prompt hash, session)
tests/
├── conftest.py          # ephemeral_graph fixture (random-named FalkorDB graphs)
└── unit/
    ├── test_ontology.py
    ├── test_ingestion.py
    ├── test_stigmergy.py
    └── test_decay.py
```

---

## Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | 3.11+ | |
| Docker | Latest | Runs FalkorDB (lightweight graph database) |
| pip | any | |

---

## Setup

1. **Start FalkorDB** (lightweight graph database):
   ```bash
   docker run -p 6379:6379 -it --rm falkordb/falkordb
   ```
   This is the MCP server's graph backend (FalkorDBLite = lightweight, not a heavy SQL DB).

2. **Install dependencies** (in another terminal):
   ```bash
   git clone <repository-url>
   cd generic_database_metadata_mcp

   python -m venv .venv
   # Windows
   .venv\Scripts\activate
   # macOS / Linux
   source .venv/bin/activate

   pip install -r requirements.txt
   ```

---

## Running the MCP Server (SSE over HTTP)

The server runs as an HTTP server with **Server-Sent Events (SSE)** transport on `http://127.0.0.1:8000`.

Make sure FalkorDB is running in another terminal (see Setup above):

```bash
# Activate venv first
.venv\Scripts\activate  # Windows
# or
source .venv/bin/activate  # macOS / Linux

# Start the server (connects to FalkorDB at localhost:6379)
python -m src.mcp_server.server
```

The server will log:
```
INFO:  src.graph.client: Connecting to FalkorDB at localhost:6379
INFO:  src.mcp_server.server:  [FastMCP] MCP tools registered: 17
INFO:  uvicorn.server: Uvicorn running on http://127.0.0.1:8000 (press CTRL+C to quit)
```

Alternatively, use uvicorn directly:
```bash
uvicorn src.mcp_server.app:app --host 127.0.0.1 --port 8000
```

---

## Architecture Overview

**FalkorDB** (FalkorDBLite = lightweight graph database):
- **Not** a heavyweight SQL database like Teradata
- **Lightweight, fast** graph for metadata connections and lineage
- Runs in Docker during development  
- Context-frugal by design (bounded queries, pagination, TOON serialization)

**MCP Server** (FastMCP on SSE/HTTP):
- Exposes 17 MCP tools for metadata management, stigmergic edges, dynamic schemas, lineage tracking
- All responses use TOON compact serialization to minimize token consumption
- Domain-scoped visibility (Rule 5.1-5.3)

---

## Testing with MCP Inspector

Once the server is running, connect via the MCP Inspector:

```bash
npx @modelcontextprotocol/inspector
```

In the Inspector UI, configure an SSE connection to `http://127.0.0.1:8000` and start testing the 17 MCP tools.

---

## MCP Tools

| Tool | Rule | Description |
|------|------|-------------|
| `register_meta_type` | US1 | Define a new typed schema (PascalCase name, JSON Schema definition) |
| `list_meta_types_tool` | US1 | List all registered MetaTypes (TOON paginated) |
| `insert_node` | US2 | Insert a single ObjectNode; validated against its MetaType schema |
| `bulk_ingest_seed` | US2 | Bulk-load nodes; returns compact summary (never full data) |
| `create_stigmergic_edge` | US3 | Create a directed edge between two ObjectNodes (`confidence_score=0.5`) |
| `reinforce_stigmergic_edge` | US3 | Reinforce an edge (+0.1, capped at 1.0) |
| `query_graph` | US4 | Query nodes with optional traversal, domain filter, pagination |
| `suggest_schema_heals` | Rule 2.7 | Identify MetaTypes with low health scores and suggest healing |
| `confirm_schema_heal` | Rule 2.7 | Reset a MetaType's health score to 1.0 after schema healing |
| `deprecate_node` | Rule 4.5 | Deprecate a node and trigger cascading wither (prune attached edges) |
| `branch_node_for_domain` | Rule 5.4 | Create a domain-specific copy of a node (Parallel Truths) |
| `request_node_deletion` | Rule 5.5 | Request deletion with approval flow (Supreme Court) |
| `confirm_node_deletion` | Rule 5.5 | Confirm node deletion after approval |
| `create_function` | Function Objects | Register an ETL operation or transformation with input/output schemas |
| `query_functions` | Function Objects | Query registered Function Objects by name or description |
| `attach_function_to_nodes` | Function Objects | Link a Function Object to ObjectNodes for transformation lineage |

### Example: register a MetaType

```json
{
  "tool": "register_meta_type",
  "arguments": {
    "name": "Dashboard",
    "type_category": "NODE",
    "schema_definition": {
      "url": {"type": "string", "required": true},
      "owner": {"type": "string"}
    }
  }
}
```

### Example: query the graph

```json
{
  "tool": "query_graph",
  "arguments": {
    "meta_type_name": "Dashboard",
    "domain_scope": "Finance",
    "page": 0,
    "page_size": 5
  }
}
```

### Example: suggest schema heals (Rule 2.7)

```json
{
  "tool": "suggest_schema_heals",
  "arguments": {
    "profile_id": "user_alice",
    "domain_scope": "Finance"
  }
}
```

### Example: deprecate a node (Rule 4.5)

```json
{
  "tool": "deprecate_node",
  "arguments": {
    "node_id": "node_uuid",
    "profile_id": "user_alice",
    "reason": "Node is no longer used in this domain"
  }
}
```

### Example: branch node for domain (Rule 5.4 - Parallel Truths)

```json
{
  "tool": "branch_node_for_domain",
  "arguments": {
    "source_node_id": "node_uuid",
    "target_domain_scope": "Finance",
    "profile_id": "user_alice",
    "domain_scope": "Global"
  }
}
```

---

## Specification Rules Coverage

| Component | Rules | Status |
|-----------|-------|--------|
| **Dynamic Meta-Ontology** | 2.1-2.8 | ✅ Complete |
| **Stigmergic Execution** | 4.1-4.5 | ✅ Complete |
| **Profile-Aware Scoping** | 5.1-5.5 | ✅ Complete |
| **Testing & Validation** | 6.1-6.3 | ✅ Complete |
| **Context Frugality** | 3.1-3.5 | ✅ Complete |

All 26 specification rules have been implemented and tested.

````

## TOON Serialisation

All tools that return lists use the **TOON** compact format:

- Keys are abbreviated (`confidence_score` → `cs`, `name` → `n`, etc.)
- Default / empty values are stripped (`"Global"`, `"SYSTEM_GENERATED"`, `null`, `""`, `{}`, `[]`)
- Hard cap: 10 KB per response payload
- Paginated envelope: `{"items": [...], "total": N, "page": P, "has_more": bool}`

---

## Stigmergic Decay

Edges decay passively over time (0.05 / day) once the 24-hour access threshold
passes.  Edges whose `confidence_score` drops below **0.1** are automatically
pruned.  Run a full decay sweep at any time:

```python
from src.graph.decay import run_all_decay
result = run_all_decay()
# {"processed": 42, "pruned": 3}
```

---

## Testing

```bash
# Uses embedded FalkorDBLite (no external dependencies)
pytest tests/ -v
```

Tests use `freezegun` to simulate time passage for decay assertions without
real waits.  Each test runs in an isolated ephemeral graph (random UUID name)
and the graph is deleted on teardown.

---

## Linting & Type Checking

```bash
ruff check src/ tests/
mypy src/
```
