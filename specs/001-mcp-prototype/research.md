# Research: Stigmergic MCP Metadata Server Prototype

## 1. FalkorDBLite Integration
- **Decision**: Use the official `falkordb` Python client, connecting to a local/embedded instance.
- **Rationale**: FalkorDBLite is the mandated embedded graph database. The official client provides the necessary Cypher execution capabilities.
- **Alternatives considered**: Networked Neo4j (rejected due to embedded requirement), Networked RedisGraph (deprecated).

## 2. Dynamic Pydantic Meta-Ontology
- **Decision**: Use `pydantic.create_model` to dynamically generate validation schemas at runtime based on `(:MetaType)` nodes stored in the graph.
- **Rationale**: Mandated by Rule 2.2. Allows the AI to define new types on the fly while maintaining strict pre-insertion validation.
- **Alternatives considered**: Static Pydantic models (rejected due to dynamic requirement), JSON Schema validation (rejected in favor of Pydantic's Pythonic integration).

## 3. Compact Output Serialization (TOON)
- **Decision**: Implement a custom serialization function that strips redundant keys, uses minimal delimiters, and flattens nested structures before returning data to the AI.
- **Rationale**: Mandated by Rule 3.5 to strictly minimize token consumption.
- **Alternatives considered**: Standard JSON (rejected due to verbosity), YAML (rejected as still too verbose for large graphs).

## 4. Stigmergic Decay Testing
- **Decision**: Use the `freezegun` library to mock time progression in unit tests.
- **Rationale**: Mandated by Rule 6.1 to prove that confidence scores decay and dead links are pruned as expected over time.

## 5. Metadata Node Schema Enforcement
- **Decision**: `(:MetaType)` nodes require `type_name`, `description`, `required_fields`, `field_schemas`, `health_score`, `created_at`, `created_by_prompt_hash`.
- **Rationale**: Supports strict Pydantic parsing dynamically and provides required audit ability (Rule 4.4, Rule 2.6).

## 6. Seed Ingestion Format
- **Decision**: The `bulk_ingest_seed` tool strictly accepts YAML bulk specifications.
- **Rationale**: YAML supports highly complex nested metadata more natively than CSV, easily mapped without relational limitations, aligning with modern node parsing implementations.

## 7. Parallel Truths (Polysemy)
- **Decision**: Parallel conflicting facts branch to child nodes connected via `[:VARIANTS]`.
- **Rationale**: Instead of property overrides or name collisions, explicit `[:VARIANTS]` branching preserves the integrity of the original general concept "umbrella" while satisfying rule 5.4.

## 8. Biological Decay Thresholds
- **Decision**: Edges undergo a 7-day inactivity threshold before decaying at 0.02 per 24h. They prune if the score drops below 0.1.
- **Rationale**: Balances context frugality with retention memory ensuring hallucinations prune predictably over an ~50 day period.

## 9. Observability Format
- **Decision**: Telemetry and logs use structured JSON logging to stdout using standard library or `structlog`.
- **Rationale**: Allows automated capture and tracing (e.g. `payload_size`, `health_score`) without bloating the conversational payload context window.
- **Alternatives considered**: `unittest.mock.patch` (rejected as `freezegun` is more robust for time mocking).