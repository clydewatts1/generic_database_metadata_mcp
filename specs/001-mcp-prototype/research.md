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
- **Alternatives considered**: `unittest.mock.patch` (rejected as `freezegun` is more robust for time mocking).