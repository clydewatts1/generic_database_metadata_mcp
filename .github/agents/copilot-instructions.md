# generic_database_metadata_mcp Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-02-27

## Active Technologies
- Python 3.11+ + mcp (MCP SDK for HTTP/SSE), falkordb (client), pydantic (v2), freezegun, structlog, pyyaml (001-mcp-prototype)
- FalkorDBLite (runs via Docker due to client-only v1.6.0 availability) (001-mcp-prototype)
- [e.g., Python 3.11, Swift 5.9, Rust 1.75 or NEEDS CLARIFICATION] + [e.g., FastAPI, UIKit, LLVM or NEEDS CLARIFICATION] (001-visual-graph-dashboard)
- [if applicable, e.g., PostgreSQL, CoreData, files or N/A] (001-visual-graph-dashboard)
- Python 3.11 (existing project standard) + FastAPI + uvicorn (already in requirements), PyJWT (new — JWT Bearer token auth), Cytoscape.js 3.x (CDN, no npm/build step needed) (001-visual-graph-dashboard)
- FalkorDB (existing — read-only queries via `src/graph/query.py`) (001-visual-graph-dashboard)
- Python 3.14.2 + FastAPI 0.11x, uvicorn, PyJWT 2.11.0, falkordb, Pydantic 2.12.5, structlog, httpx (TestClient), freezegun (001-schema-health-widget)
- FalkorDB on localhost:6379 — read: `(:MetaType)` nodes; write: `(:HumanAuditLog)` nodes (001-schema-health-widget)

- Python 3.11+ + mcp (FastMCP), Pydantic, freezegun (001-mcp-prototype)

## Project Structure

```text
src/
tests/
```

## Commands

cd src; pytest; ruff check .

## Code Style

Python 3.11+: Follow standard conventions

## Recent Changes
- 001-schema-health-widget: Added Python 3.14.2 + FastAPI 0.11x, uvicorn, PyJWT 2.11.0, falkordb, Pydantic 2.12.5, structlog, httpx (TestClient), freezegun
- 001-schema-health-widget: Added [e.g., Python 3.11, Swift 5.9, Rust 1.75 or NEEDS CLARIFICATION] + [e.g., FastAPI, UIKit, LLVM or NEEDS CLARIFICATION]
- 001-visual-graph-dashboard: Added Python 3.11 (existing project standard) + FastAPI + uvicorn (already in requirements), PyJWT (new — JWT Bearer token auth), Cytoscape.js 3.x (CDN, no npm/build step needed)


<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
