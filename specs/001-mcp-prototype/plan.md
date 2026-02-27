# Implementation Plan: Stigmergic MCP Metadata Server Prototype

**Branch**: `001-mcp-prototype` | **Date**: 2026-02-27 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-mcp-prototype/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Build a lightweight, context-frugal Model Context Protocol (MCP) server that functions as a "Glossary Weaver" using a stigmergic approach. The prototype will support dynamic meta-ontology creation, context-frugal querying with compact serialization, and stigmergic edge reinforcement and decay.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: mcp (FastMCP), Pydantic, freezegun
**Storage**: FalkorDBLite (embedded graph database)
**Testing**: pytest
**Target Platform**: Local MCP Server
**Project Type**: MCP Server
**Performance Goals**: Ingest 10k nodes in < 1 minute
**Constraints**: < 10KB payload size for bulk ingest, bounded Cypher queries (*1..2 hops), pagination (>5 nodes), compact serialization (TOON)
**Scale/Scope**: Small (< 100k nodes/edges)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **Context-Frugal by Design**: Bounded queries, pagination, and compact serialization are mandated.
- [x] **Dynamic Pydantic Meta-Ontology**: Dynamic type registration and pre-insertion validation are required.
- [x] **Stigmergic Confidence Web**: Organic edge creation, reinforcement, and biological decay are included.
- [x] **Scoped Truth**: Profile-aware scoping and parallel truths are specified.
- [x] **Explicit Semantics**: Rationale summary and prompt hash are required for AI modifications.
- [x] **Testing & Validation Mandate**: Test-driven stigmergy, frugality assertions, and ephemeral sandboxes are mandated.

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
│   ├── __init__.py
│   ├── server.py        # FastMCP server setup
│   ├── tools/           # MCP tools (bulk_ingest, query, etc.)
│   └── resources/       # MCP resources
├── graph/
│   ├── __init__.py
│   ├── client.py        # FalkorDBLite client wrapper
│   ├── ontology.py      # Dynamic Pydantic model generation
│   └── stigmergy.py     # Edge creation, reinforcement, decay logic
├── models/
│   ├── __init__.py
│   ├── base.py          # Base Pydantic models
│   └── serialization.py # TOON serialization logic
└── utils/
    ├── __init__.py
    └── context.py       # Profile and scope injection

tests/
├── conftest.py          # Ephemeral FalkorDBLite setup
├── unit/
│   ├── test_ontology.py
│   ├── test_stigmergy.py # Uses freezegun
│   └── test_serialization.py
└── integration/
    ├── test_tools.py    # Frugality assertions
    └── test_server.py
```

**Structure Decision**: Single Python project structure with clear separation of concerns: MCP server logic, graph database interactions, dynamic modeling, and utilities. Tests are separated into unit and integration, with specific focus on stigmergy and frugality.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | N/A |
