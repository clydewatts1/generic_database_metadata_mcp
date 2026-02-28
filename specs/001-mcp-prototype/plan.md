# Implementation Plan: Stigmergic MCP Metadata Server Prototype

**Branch**: `001-mcp-prototype` | **Date**: 2026-02-28 | **Spec**: [specs/001-mcp-prototype/spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-mcp-prototype/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Build a lightweight, context-frugal Model Context Protocol (MCP) server that functions as a dynamic, stigmergic metadata graph (mimicking Teradata Metadata Services). Uses FalkorDBLite, strict dynamic Pydantic generation, and highly compact output serialization.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: mcp (MCP SDK for HTTP/SSE), falkordb (client), pydantic (v2), freezegun, structlog, pyyaml
**Storage**: FalkorDBLite (runs via Docker due to client-only v1.6.0 availability)
**Testing**: pytest, freezegun, pytest-asyncio
**Target Platform**: Linux/Windows/Mac server (via Docker)
**Project Type**: mcp-server
**Performance Goals**: <10KB context payloads, fast Cypher traversals (1-2 hops)
**Constraints**: Absolute adherence to token frugality (TOON payload compression), required Human-In-The-Loop on destruction
**Scale/Scope**: Small graph sizes (< 100k nodes), tightly paginated responses (max 5 nodes per page)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Rule 1.1**: Uses FalkorDBLite and MCP protocol for context-frugal Glossary Weaver.
- **Rule 2.2**: Uses `pydantic.create_model` to enforce strong typing dynamically.
- **Rule 3.3/3.5**: Enforces pagination (max 5) and compact format serialization (TOON).
- **Rule 4.3**: Enforces Stigmergic Decay using 7-day threshold.
- **Rule 5.5**: Validated: Deleting schemas requires [APPROVAL_REQUIRED].
- **Rule 6.3**: Validated: Testing utilizes isolated in-memory or ephemeral mock DB states.

## Project Structure

### Documentation (this feature)

```text
specs/001-mcp-prototype/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/
├── mcp_server/
│   ├── server.py              # Main FastMCP definition
│   ├── tools/                 # Tool implementations (functions, ingest, query)
│   └── formatters/            # TOON serialization logic
├── graph/
│   ├── client.py              # FalkorDB client lifecycle
│   ├── schema.py              # Pydantic meta-ontology logic
│   └── queries.py             # Bounded Cypher execution
├── models/
│   └── base.py                # Core Pydantic Base Models

tests/
├── unit/
│   ├── test_stigmergy.py      # freezegun biological decay tests
│   └── test_serialization.py  # Frugality bounds tests
├── integration/
│   └── test_function_objects_e2e.py # Complete mocked logic
```

**Structure Decision**: A single Python package containing the MCP server layer, a graph abstraction layer (for FalkorDB), and dynamic Pydantic definitions, cleanly isolated for testability.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| | | |
