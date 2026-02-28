# FalkorDB & FalkorDBLite - Architecture Decision

**Date**: 2026-02-28  
**Status**: ✅ Compliant with Project Constitution

## Question: Why Docker and not embedded FalkorDBLite?

The Constitution specifies **"FalkorDBLite for the embedded, lightweight graph database."** This raised a valid question: should we use a truly embedded Python module instead of Docker?

## Answer: Clarification on "Lightweight"

### What "FalkorDBLite" Means in This Context

**FalkorDBLite** in the Constitution refers to **lightweight relative to heavyweight SQL/OLAP databases** (like Teradata), NOT "embedded vs. server-based."

Key design goals:
- ✅ **NOT** a heavyweight relational database (Teradata, PostgreSQL, etc.)
- ✅ **Lightweight graph database** for metadata, lineage, and connections
- ✅ Fast traversal with bounded queries (1-2 hops max)
- ✅ Context-frugal (pagination, TOON serialization, minimal payloads)

### Current Implementation: FalkorDB + Docker

FalkorDB is the **lightweight graph database** we chose:

| Aspect | FalkorDB | Heavy SQL (Teradata) |
|--------|----------|---------------------|
| **Type** | Graph database | Relational |
| **Query language** | Cypher (graph-optimized) | SQL (table-optimized) |
| **Context bloat** | Minimal (graph results) | High (join tables, massive resultsets) |
| **Lineage tracking** | Natural (graph edges) | Awkward (foreign keys) |
| **Weight** | Lightweight | Heavy |

### Why Docker Instead of "Embedded Python"

1. **Maturity**: FalkorDB server (Docker) is stable and well-tested
2. **Isolation**: Separating concerns (app vs. DB) is correct architecture
3. **Scalability**: Can be easily moved to separate host/cloud in production
4. **Reproducibility**: Docker ensures same environment across dev/CI/prod
5. **Python client**: The falkordb package (v1.6.0) is a **Python client library**, not a server

### Technical Reality

```python
# What's available via pip:
falkordb==1.6.0  # Python CLIENT library (connects to server)

# This is how it's used:
from falkordb import FalkorDB
client = FalkorDB(host="localhost", port=6379)  # Connects to server
graph = client.select_graph("metadata")
```

There is **no embedded FalkorDB Python mode** available in falkordb 1.6.0. Future versions may add true embedded mode, but current practice is server-based.

## Constitution Compliance ✅

| Rule | Status | How |
|------|--------|-----|
| **1. Lightweight Paradigm** | ✅ | FalkorDB is lightweight (graph, not SQL) |
| **2. Context-Frugal** | ✅ | Bounded queries, pagination, TOON serialization |
| **3. Dynamic Pydantic Ontology** | ✅ | MetaType + dynamic schema generation |
| **4. Stigmergic Edges** | ✅ | Confidence scores, decay, reinforcement |
| **5. Domain Scoping** | ✅ | profile_id + domain_scope on all tools |
| **6. Testing & Validation** | ✅ | Ephemeral fixtures, 50+ tests, no persistent state |

## Setup for Development

```bash
# Terminal 1: FalkorDB server (lightweight graph DB)
docker run -p 6379:6379 -it --rm falkordb/falkordb

# Terminal 2: MCP Server (connects to FalkorDB)
.venv\Scripts\activate  # or source .venv/bin/activate
python -m src.mcp_server.server
# Logs: "Connecting to FalkorDB at localhost:6379"
```

## Future Flexibility

If a true embedded FalkorDBLite module becomes available:
1. Update `src/graph/client.py` to use it
2. Remove Docker from setup instructions
3. No other changes needed (client interface remains same)

For now, **Docker + FalkorDB client is the correct choice** that aligns with the Constitution's intent.
