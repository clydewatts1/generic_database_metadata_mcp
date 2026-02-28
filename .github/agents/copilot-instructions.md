# generic_database_metadata_mcp Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-02-27

## Active Technologies
- Python 3.11+ + mcp (MCP SDK for HTTP/SSE), falkordb (client), pydantic (v2), freezegun, structlog, pyyaml (001-mcp-prototype)
- FalkorDBLite (runs via Docker due to client-only v1.6.0 availability) (001-mcp-prototype)

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
- 001-mcp-prototype: Added Python 3.11+ + mcp (MCP SDK for HTTP/SSE), falkordb (client), pydantic (v2), freezegun, structlog, pyyaml

- 001-mcp-prototype: Added Python 3.11+ + mcp (FastMCP), Pydantic, freezegun

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
