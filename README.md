# generic_database_metadata_mcp

A **stigmergic, context-frugal metadata MCP server** backed by FalkorDB, with a **read-only visual web dashboard**.

| Service | Transport | Default Port |
|---------|-----------|-------------|
| MCP Server | HTTP + SSE (FastMCP) | `8000` |
| Visual Dashboard | HTTP (FastAPI + static) | `8080` |

The server exposes a graph of typed metadata objects whose edges carry a living `confidence_score`. Edges are reinforced every time they are traversed and decay when left unused ÔÇö embodying the "use it or lose it" principle from ant colony stigmergy. MCP tool responses use the compact **TOON** serialisation format to keep LLM context windows small. The dashboard bypasses TOON and serves full JSON to the browser (Rule 3.6 exemption).

---

## Architecture

```
src/
Ôö£ÔöÇÔöÇ graph/
Ôöé   Ôö£ÔöÇÔöÇ client.py        # FalkorDB connection singleton
Ôöé   Ôö£ÔöÇÔöÇ ontology.py      # MetaType CRUD + health-score management
Ôöé   Ôö£ÔöÇÔöÇ nodes.py         # ObjectNode CRUD + bulk ingest
Ôöé   Ôö£ÔöÇÔöÇ edges.py         # StigmergicEdge CRUD, reinforce, decay, cascading wither
Ôöé   Ôö£ÔöÇÔöÇ decay.py         # Decay runner (single edge + full-graph sweep)
Ôöé   Ôö£ÔöÇÔöÇ query.py         # Bounded traversal (1-2 hops) + flat scan + pagination
Ôöé   ÔööÔöÇÔöÇ schema.py        # Graph schema helpers
Ôö£ÔöÇÔöÇ dashboard/           # Visual web dashboard API (FastAPI, port 8080)
Ôöé   Ôö£ÔöÇÔöÇ api.py           # App factory; mounts static files; /health + /api/graph
Ôöé   Ôö£ÔöÇÔöÇ auth.py          # JWT Bearer decode; DashboardUser dependency; 401/403
Ôöé   Ôö£ÔöÇÔöÇ router.py        # GET /api/graph route (scoped, read-only)
Ôöé   Ôö£ÔöÇÔöÇ graph_service.py # DashboardGraphService ÔÇö wraps query.py; 500-node cap
Ôöé   Ôö£ÔöÇÔöÇ models.py        # Pydantic response models (GraphNodeResponse, GraphEdgeResponse ÔÇª)
Ôöé   Ôö£ÔöÇÔöÇ config.py        # Env-var loading (DASHBOARD_JWT_SECRET, DASHBOARD_PORT ÔÇª)
Ôöé   ÔööÔöÇÔöÇ server.py        # uvicorn entrypoint (port 8080)
Ôö£ÔöÇÔöÇ models/
Ôöé   Ôö£ÔöÇÔöÇ base.py          # Pydantic models for all graph entities
Ôöé   Ôö£ÔöÇÔöÇ dynamic.py       # Runtime model factory (pydantic.create_model)
Ôöé   ÔööÔöÇÔöÇ serialization.py # TOON compact serialiser / paginator
Ôö£ÔöÇÔöÇ mcp_server/
Ôöé   Ôö£ÔöÇÔöÇ app.py           # FastMCP singleton
Ôöé   Ôö£ÔöÇÔöÇ server.py        # Entry point ÔÇô registers all tools, calls mcp.run()
Ôöé   Ôö£ÔöÇÔöÇ formatters/
Ôöé   Ôöé   ÔööÔöÇÔöÇ toon.py      # TOON compact format helpers
Ôöé   ÔööÔöÇÔöÇ tools/
Ôöé       Ôö£ÔöÇÔöÇ ingestion.py # insert_node, bulk_ingest_seed (circuit breaker)
Ôöé       Ôö£ÔöÇÔöÇ ontology.py  # register_meta_type, list_meta_types_tool
Ôöé       Ôö£ÔöÇÔöÇ stigmergy.py # create_stigmergic_edge, reinforce_stigmergic_edge
Ôöé       Ôö£ÔöÇÔöÇ query.py     # query_graph
Ôöé       Ôö£ÔöÇÔöÇ lifecycle.py # deprecate_node, branch_node_for_domain, request/confirm deletion
Ôöé       Ôö£ÔöÇÔöÇ healing.py   # suggest_schema_heals, confirm_schema_heal
Ôöé       ÔööÔöÇÔöÇ functions.py # create_function, query_functions, attach_function_to_nodes
ÔööÔöÇÔöÇ utils/
    Ôö£ÔöÇÔöÇ logging.py       # Logger + error class hierarchy
    ÔööÔöÇÔöÇ context.py       # RequestContext (profile, domain, prompt hash, session)

dashboard/               # Frontend static assets (served by the dashboard API)
Ôö£ÔöÇÔöÇ index.html           # Single-page app shell; loads Cytoscape.js 3.x from CDN
Ôö£ÔöÇÔöÇ app.js               # Canvas render, node click/dim, filter panel, search, edge tooltips
ÔööÔöÇÔöÇ style.css            # Full-height dark-theme layout; confidence_score edge encoding

tests/
Ôö£ÔöÇÔöÇ conftest.py
Ôö£ÔöÇÔöÇ unit/
Ôöé   Ôö£ÔöÇÔöÇ dashboard/
Ôöé   Ôöé   Ôö£ÔöÇÔöÇ test_auth.py           # JWT auth (401/403, expired, missing claims)
Ôöé   Ôöé   Ôö£ÔöÇÔöÇ test_graph_service.py  # Scope enforcement, 500-node cap, confidence clamp
Ôöé   Ôöé   ÔööÔöÇÔöÇ test_performance.py    # SC-002 serialisation Ôëñ1.5s, SC-005 filter Ôëñ50ms
Ôöé   Ôö£ÔöÇÔöÇ test_ontology.py
Ôöé   Ôö£ÔöÇÔöÇ test_ingestion.py
Ôöé   Ôö£ÔöÇÔöÇ test_stigmergy.py
Ôöé   Ôö£ÔöÇÔöÇ test_decay.py
Ôöé   Ôö£ÔöÇÔöÇ test_domain_scoping.py
Ôöé   Ôö£ÔöÇÔöÇ test_function_object_model.py
Ôöé   Ôö£ÔöÇÔöÇ test_remaining_rules.py
Ôöé   ÔööÔöÇÔöÇ test_serialization.py
Ôö£ÔöÇÔöÇ integration/
Ôöé   Ôö£ÔöÇÔöÇ test_dashboard_api.py      # Scope isolation, response shape, health probe, edge fields
Ôöé   ÔööÔöÇÔöÇ test_function_objects_e2e.py
ÔööÔöÇÔöÇ contract/
    ÔööÔöÇÔöÇ test_dashboard_mutations.py  # Assert zero WRITE Cypher ops from any dashboard route
```

---

## Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | 3.11+ | |
| Docker | Latest | Runs FalkorDB |
| pip | any | |

---

## Setup

1. **Start FalkorDB**:
   ```bash
   docker run -p 6379:6379 -it --rm falkordb/falkordb
   ```

2. **Install dependencies**:
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

## Running the MCP Server

Runs on `http://127.0.0.1:8000` (SSE transport).

```bash
python -m src.mcp_server.server
```

Expected log output:
```
INFO: src.graph.client: Connecting to FalkorDB at localhost:6379
INFO: src.mcp_server.server: [FastMCP] MCP tools registered: 17
INFO: uvicorn.server: Uvicorn running on http://127.0.0.1:8000
```

Or directly via uvicorn:
```bash
uvicorn src.mcp_server.app:app --host 127.0.0.1 --port 8000
```

---

## Running the Visual Dashboard

Runs on `http://127.0.0.1:8080` as a **separate process**. Requires the `DASHBOARD_JWT_SECRET` env var.

```bash
export DASHBOARD_JWT_SECRET="your-secret-here"
python -m src.dashboard.server
```

Open `http://localhost:8080` in a browser, paste a valid JWT, and the metadata graph renders automatically.

### Dashboard environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DASHBOARD_JWT_SECRET` | *(required)* | HS256 secret for JWT Bearer token validation |
| `DASHBOARD_PORT` | `8080` | Port the dashboard server listens on |
| `DASHBOARD_NODE_LIMIT` | `500` | Max nodes returned per scoped payload |
| `FALKORDB_HOST` | `localhost` | FalkorDB hostname |
| `FALKORDB_PORT` | `6379` | FalkorDB port |

---

## Dashboard Features

### US1 ÔÇö Interactive Graph Canvas
Nodes in the authenticated user's permitted scope render as a pan/zoom Cytoscape.js canvas within 3 seconds. Click a node to open a properties side-panel and dim non-adjacent nodes. Press Escape or click the background to restore.

### US2 ÔÇö Stigmergic vs Structural Edges
Stigmergic edges encode `confidence_score` as line width (1 px at 0.0 ÔåÆ 6 px at 1.0). Edges below 0.2 render dashed and de-emphasised. Structural edges are a fixed 1.5 px solid grey line. Hover any edge for a tooltip ÔÇö stigmergic tooltips include `confidence_score`, `rationale_summary`, and `last_accessed`.

### US3 ÔÇö Filter & Search
Select one or more Object Types from the filter panel to restrict visible nodes. Type a `business_name` substring to dim non-matching nodes and auto-centre on the most-connected match. Refresh button resets both.

### US4 ÔÇö Profile-Aware Scoped View
Every API request requires a JWT bearing `profile_id` and `domain_scope`. Domain scoping is enforced server-side on every query ÔÇö no cross-domain data leaks are possible. Missing token ÔåÆ HTTP 401; missing claims ÔåÆ HTTP 403.

---

## Testing with MCP Inspector

```bash
npx @modelcontextprotocol/inspector
```

Configure an SSE connection to `http://127.0.0.1:8000`.

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

### Example: branch node for domain (Rule 5.4 ÔÇö Parallel Truths)

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
| **Dynamic Meta-Ontology** | 2.1ÔÇô2.8 | Ô£à Complete |
| **Context Frugality (MCP)** | 3.1ÔÇô3.5 | Ô£à Complete |
| **Human Viewport Exception** | 3.6 | Ô£à Complete ÔÇö dashboard API exempt from TOON/compression |
| **Stigmergic Execution** | 4.1ÔÇô4.5 | Ô£à Complete |
| **Human Override Authority** | 4.7 | ÔÜá´©Å Ratified v1.3.0 ÔÇö implementation pending (4.6 reserved) |
| **Profile-Aware Scoping** | 5.1ÔÇô5.5 | Ô£à Complete |
| **Dashboard Unified Security Layer** | 5.6 | Ô£à Implemented on `001-schema-health-widget` ÔÇö pending merge to `main` |
| **Audit Logging (Human Viewport)** | 5.7 | ÔÜá´©Å Ratified v1.2.0 ÔÇö implementation pending |
| **Testing & Validation** | 6.1ÔÇô6.3 | Ô£à Complete |

26 rules defined. Constitution v1.3.1: Rule 5.6 implemented on `001-schema-health-widget` (pending merge). Rules 4.7 and 5.7 remain pending implementation. Rule 4.6 reserved.

---

## TOON Serialisation (MCP tools only)

All MCP tools that return lists use the **TOON** compact format:

- Keys are abbreviated (`confidence_score` ÔåÆ `cs`, `name` ÔåÆ `n`, etc.)
- Default / empty values are stripped
- Hard cap: 10 KB per response payload
- Paginated envelope: `{"items": [...], "total": N, "page": P, "has_more": bool}`

The dashboard API is **explicitly exempt** from TOON per Rule 3.6 ÔÇö it serves full JSON to the browser.

---

## Stigmergic Decay

Edges decay passively over time (0.05 / day) once the 24-hour access threshold passes. Edges whose `confidence_score` drops below **0.1** are automatically pruned. Run a full decay sweep at any time:

```python
from src.graph.decay import run_all_decay
result = run_all_decay()
# {"processed": 42, "pruned": 3}
```

---

## Testing

```bash
# All tests (requires FalkorDB running)
pytest tests/ -v

# Dashboard tests only (no live FalkorDB needed)
pytest tests/unit/dashboard/ tests/contract/ tests/integration/test_dashboard_api.py -v
```

Dashboard tests use FastAPI `TestClient` with monkeypatched service methods ÔÇö no live FalkorDB required. All other tests use an ephemeral random-named FalkorDB graph torn down on completion. `freezegun` is used to simulate time passage for decay assertions.

---

## Linting & Type Checking

```bash
ruff check src/ tests/
mypy src/
```
