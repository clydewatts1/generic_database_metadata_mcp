# Phase 0: Research — Neo4j Migration Technical Decisions

**Feature**: Neo4j Graph Database Migration  
**Date**: 2026-03-01  
**Status**: Complete (no unknowns requiring research)

## Summary

All technical decisions for the Neo4j migration are fully specified in the clarified [spec.md](spec.md). This document consolidates the rationale for key architectural choices to guide Phase 1 design.

## Technical Decisions

### Decision 1: Neo4j Python Driver Selection

**Decision**: Use `neo4j>=5.0.0` official Python driver

**Rationale**:
- Official driver from Neo4j Inc. with active maintenance and security updates
- Supports Neo4j Community Edition v5.x (our deployment target)
- Provides connection pooling, retry logic, and transaction management out-of-box
- Well-documented adapter patterns for wrapping existing interfaces
- Compatible with Python 3.11+ (our project requirement)

**Alternatives Considered**:
- `py2neo`: Third-party driver, less active maintenance, older API patterns
- `neomodel`: ORM abstraction layer — too heavy for our Cypher-first approach (violates Rule 3.2 semantic compression)
- Raw HTTP API via `requests`: No connection pooling, manual transaction handling, higher latency

**References**: 
- Neo4j Python Driver docs: https://neo4j.com/docs/python-manual/current/
- Driver API ref: https://neo4j.com/docs/api/python-driver/current/

---

### Decision 2: Connection Retry Strategy

**Decision**: Exponential backoff with 3 retries, max 5 seconds total

**Rationale**:
- Handles transient network failures (temporary DNS resolution, brief Neo4j restarts) without manual intervention
- 3 retries balances resilience with fast failure — genuine outages fail within 5s instead of hanging
- Exponential backoff (e.g., 0.5s, 1s, 2s) prevents retry storms that could overwhelm recovering database
- Aligns with standard cloud reliability patterns (AWS SDK, Kubernetes probes use similar defaults)

**Alternatives Considered**:
- No retries (fail immediately): Too brittle for production — legitimate brief network blips cause unnecessary errors
- Aggressive retries (10+ attempts, 30s): Adds unacceptable latency to genuine failures; violates context-frugal mandate
- Configurable via env var: Over-engineering for local Neo4j deployment; adds unnecessary complexity

**Implementation Note**: Use `neo4j.Driver` built-in `max_retry_time` and `connection_acquisition_timeout` configuration.

**References**:
- Neo4j driver configuration: https://neo4j.com/docs/api/python-driver/current/api.html#neo4j.Driver

---

### Decision 3: Test Isolation Strategy

**Decision**: Per-test database creation/teardown (real Neo4j instances)

**Rationale**:
- Ensures true isolation — no cross-test contamination from shared database state
- Tests real Neo4j behavior (Cypher syntax, constraint enforcement, transaction semantics) rather than mocked abstractions
- Validates constitution Rule 6.3 compliance ("ephemeral test databases in Neo4j")
- Slower than in-memory mocks (~100-200ms per test setup), but acceptable for our test suite size (~50 integration tests)

**Alternatives Considered**:
- In-memory fixtures (mocked graph objects): Fast but doesn't test real Neo4j behavior — could miss Cypher dialect differences
- Single shared test database with transaction rollback: Faster but risky — parallel test execution could cause race conditions
- Neo4j Testcontainers: Over-engineered for local development; requires Docker (user explicitly rejected Docker)

**Implementation Note**: Use `pytest` fixtures with `scope="function"` to create/drop test databases via `CREATE DATABASE test_db_<uuid>` and `DROP DATABASE`.

**References**:
- Neo4j database management: https://neo4j.com/docs/cypher-manual/current/administration/databases/

---

### Decision 4: Database Name Configuration

**Decision**: Configurable via `NEO4J_DATABASE` env var, default "neo4j"

**Rationale**:
- Neo4j Community Edition uses "neo4j" as the default database name (not "system" which is reserved)
- Configurability allows test environments to use separate databases (e.g., "metadata_mcp_test") without code changes
- Follows 12-factor app principles (config via environment)
- Enables multi-tenant deployments if needed in future (different projects → different databases)

**Alternatives Considered**:
- Hardcoded to "metadata_mcp": Non-standard for Neo4j; breaks convention; requires manual database creation
- Always use default database: Least flexible; prevents test isolation via separate databases

**Implementation Note**: Set via `os.getenv("NEO4J_DATABASE", "neo4j")` in `neo4j_client.py`.

---

### Decision 5: Schema Bootstrap Execution

**Decision**: Automatic on first graph client connection, with idempotent CREATE IF NOT EXISTS logic

**Rationale**:
- "Batteries included" approach — no manual setup required for developers or deployments
- Idempotent operations (`CREATE CONSTRAINT IF NOT EXISTS`) mean re-running is safe — no failed setup script if constraints already exist
- Fails fast if Neo4j permissions are insufficient (constraint creation requires WRITE privilege)
- Aligns with FR-011 (transparent backend swap) — existing code just calls `get_graph_client()` and schema auto-initializes

**Alternatives Considered**:
- Manual CLI command (e.g., `python -m src.graph.bootstrap`): Requires documentation, extra step, easy to forget in deployments
- During application startup (dashboard/MCP server init): Guaranteed execution but adds ~200ms startup latency; fails entire server if Neo4j down
- Part of CI/CD pipeline only: Separates infrastructure from application; requires deployment tooling; breaks local dev workflow

**Implementation Note**: Wrap bootstrap logic in try/except, log failures, raise RuntimeError if schema creation fails (blocks all queries until fixed).

**References**:
- Neo4j constraints: https://neo4j.com/docs/cypher-manual/current/constraints/
- Neo4j indexes: https://neo4j.com/docs/cypher-manual/current/indexes-for-search-performance/

---

### Decision 6: Backend Auto-Detection Logic

**Decision**: Check for `NEO4J_URI` environment variable; if present, use Neo4j, else fallback to FalkorDB

**Rationale**:
- Simple precedence rule — explicit configuration (NEO4J_URI set) overrides default (FalkorDB for backward compat)
- Enables gradual migration — teams can test Neo4j without removing FalkorDB dependencies
- Supports CI/CD flexibility — some test environments may still use FalkorDB temporarily
- Clear failure mode — if neither backend available, raise explicit RuntimeError with setup instructions

**Alternatives Considered**:
- Prefer FalkorDB if both present: Contradicts constitution v1.4.0 mandate (Neo4j is primary)
- Require explicit backend selection via env var (e.g., `GRAPH_BACKEND=neo4j`): Extra configuration surface; most deployments will use Neo4j exclusively

**Implementation Note**: In `src/graph/client.py`, modify `get_graph_client()` to check `os.getenv("NEO4J_URI")` first.

---

## Research Closure

All unknowns resolved. No additional research required. Technical Context contains zero NEEDS CLARIFICATION markers.

**Next Phase**: Phase 1 — Design (data-model.md, contracts/, quickstart.md)
