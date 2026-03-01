# Implementation Plan: Neo4j Graph Database Migration

**Branch**: `002-neo4j-migration` | **Date**: 2026-03-01 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/002-neo4j-migration/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Migrate the graph database backend from FalkorDB to Neo4j Community Edition while maintaining full backward compatibility and functional equivalence. The system will auto-detect the available backend (Neo4j preferred) via environment variables and provide a unified adapter interface supporting both databases. Schema constraints and indexes will be created automatically on first connection using idempotent operations. Connection retry logic with exponential backoff (3 retries, max 5s) will handle transient failures. All existing MCP tools, dashboard APIs, and stigmergic mechanics (30-day decay threshold, confidence scoring, pruning) will function identically on the new backend without code changes.

## Technical Context

**Language/Version**: Python 3.11+ (project uses Python 3.14 in dev environment)
**Primary Dependencies**: `mcp` (MCP Python SDK), `fastapi`, `pydantic` v2, `neo4j`>=5.0.0 (new), `falkordb` (existing, backward compat)  
**Storage**: Neo4j Community Edition v5.x (primary), FalkorDB (fallback for transition period)  
**Testing**: `pytest`, `pytest-asyncio`, `freezegun` (for time-based stigmergic decay tests)  
**Target Platform**: Linux/Windows server (tested on Windows 11, deployment-agnostic)  
**Project Type**: MCP server (SSE-based protocol) with FastAPI web dashboard for human viewport  
**Performance Goals**: Context frugal querying (pagination at >5 nodes per Rule 3.3), stigmergic edge reinforcement < 50ms overhead  
**Constraints**: Cypher depth limit *1..2 hops (Rule 3.1), no raw JSON topology dumps (Rule 3.2), ephemeral test databases (Rule 6.3)  
**Scale/Scope**: Enterprise metadata catalog (10k+ nodes), multi-domain scoping (Finance/Marketing/Global), stigmergic confidence scoring with 30-day decay threshold

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Gating Rules**: Section 1 (Tech Stack), Rule 6.3 (Ephemeral Sandbox)

| Rule | Requirement | Compliance Status |
|------|-------------|-------------------|
| **Section 1** | Tech Stack MUST use "Neo4j Community Edition for the local graph database" | ✅ **PASS** — Constitution v1.4.0 mandates Neo4j; this feature implements that mandate |
| **Rule 2.1-2.8** | Dynamic Pydantic Ontology: Schema validation MUST remain backend-agnostic | ✅ **PASS** — Pydantic models unaffected; only storage layer changes |
| **Rule 3.1-3.6** | Context Frugal Mandate: Cypher depth limits (*1..2), pagination (>5 nodes), no raw dumps | ✅ **PASS** — Cypher queries unchanged; adapter maintains identical query interface |
| **Rule 4.1-4.5** | Stigmergic Execution: Confidence scoring, decay (30 days), pruning MUST function identically | ✅ **PASS** — FR-009 ensures stigmergic mechanics unchanged; only persistence layer differs |
| **Rule 5.1-5.7** | Profile-Aware Scoping: `domain_scope` filtering MUST work on Neo4j | ✅ **PASS** — Cypher WHERE clauses identical; Neo4j supports same filtering syntax |
| **Rule 6.3** | Ephemeral Sandbox: Tests MUST use "ephemeral test databases in Neo4j or in-memory fixtures" | ✅ **PASS** — FR-007 specifies per-test database creation/teardown strategy |

**Violations**: None — This is a pure backend substitution maintaining all semantic contracts (as noted in constitution v1.4.0 Sync Impact Report).

**Post-Phase 1 Re-Check**: ✅ **PASS** — Design artifacts (data-model.md, contracts/) confirm no behavioral changes to stigmergic mechanics, scoping, or testing patterns. All constitution rules remain satisfied.

## Project Structure

### Documentation (this feature)

```text
specs/002-neo4j-migration/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   └── neo4j-adapter-interface.md
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/
├── dashboard/           # FastAPI web dashboard (human viewport)
│   ├── server.py       # Uvicorn entrypoint with JWT validation
│   ├── router.py       # Graph data API routes (Rule 5.6 security layer)
│   ├── health_router.py # Health widget endpoints
│   ├── graph_service.py # Graph query service (uses client.py abstraction)
│   ├── health_service.py # MetaType health score service
│   ├── security.py     # Unified Security Layer (Rule 5.6)
│   └── auth.py         # JWT validation utilities
├── graph/              # Graph database abstraction layer
│   ├── client.py       # **TO MODIFY**: Add Neo4j auto-detection logic
│   ├── neo4j_client.py # **TO CREATE**: Neo4j adapter with FalkorDB-compatible interface
│   ├── ontology.py     # Pydantic dynamic meta-model (unchanged)
│   ├── schema.py       # MetaType validation (unchanged)
│   ├── query.py        # Cypher query builders (unchanged)
│   └── nodes.py        # Node creation utilities (unchanged)
├── mcp_server/         # MCP protocol server (SSE-based)
│   ├── server.py       # MCP server entrypoint
│   └── tools/          # MCP tool implementations (use graph/client.py)
└── utils/              # Shared utilities (logging, context)

tests/
├── contract/           # Pydantic validation contract tests
│   └── **TO UPDATE**: Ensure tests pass against Neo4j backend
├── integration/        # End-to-end graph query tests
│   └── **TO UPDATE**: Configure Neo4j test database fixtures
└── unit/               # Isolated component tests
    └── **TO UPDATE**: Mock Neo4j client for unit tests
```

**Structure Decision**: Single project with layered architecture. The `src/graph/client.py` module provides the abstraction boundary — all downstream code (dashboard, MCP tools) imports from `client.py` and remains agnostic to the underlying database. The new `src/graph/neo4j_client.py` adapter will implement the same interface as the existing FalkorDB client, ensuring transparent substitution per FR-011 (migration MUST NOT require changes to existing MCP tool implementations or dashboard API routes).

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

**No violations detected.** All constitution rules pass. This is a backend substitution implementing Constitution v1.4.0's mandate (Section 1: Tech Stack updated to Neo4j Community Edition). No complexity trade-offs or violations requiring justification.
