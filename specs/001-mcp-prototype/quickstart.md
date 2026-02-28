# Quickstart: Stigmergic MCP Metadata Server Prototype

## Prerequisites
- Python 3.11+
- Docker (to run FalkorDB - lightweight graph database)
- `pip` or `poetry` for dependency management

## Setup

1. **Start FalkorDB** (in one terminal):
   ```bash
   docker run -p 6379:6379 -it --rm falkordb/falkordb
   ```

2. **Clone and setup** (in another terminal):
   ```bash
   git clone <repository-url>
   cd generic_database_metadata_mcp
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   # or
   poetry install
   ```

4. **Run the MCP Server**:
   ```bash
   python src/mcp_server/server.py
   ```

## Usage Examples

### 1. Bulk Ingest Seed Data
Use the `bulk_ingest_seed` tool to load initial data without overwhelming the context window.
```json
{
  "tool": "bulk_ingest_seed",
  "arguments": {
    "file_path": "/path/to/seed_data.yaml"
  }
}
```

### 2. Register a New MetaType
Dynamically define a new schema.
```json
{
  "tool": "register_meta_type",
  "arguments": {
    "name": "Dashboard",
    "type_category": "NODE",
    "schema_definition": {
      "url": "string",
      "owner": "string"
    }
  }
}
```

### 3. Query the Graph
Perform a context-frugal query. Results will be paginated and serialized in TOON format.
```json
{
  "tool": "query_graph",
  "arguments": {
    "query_intent": "Find all dashboards related to Finance",
    "domain_scope": "Finance",
    "max_depth": 2
  }
}
```

## Testing
Run the test suite, which includes frugality assertions and stigmergic decay tests using `freezegun`.
```bash
pytest tests/
```
