# Data Model: Stigmergic MCP Metadata Server Prototype

## Technology: FalkorDBLite Graph Database

**Choice Rationale**:  
FalkorDBLite was selected as the lightweight graph database (not heavyweight SQL like Teradata) to enable:
- Fast, bounded graph traversals with strict depth limits (1-2 hops max)
- Natural representation of metadata lineage via graph edges
- Built-in context frugality via pagination and query bounds
- Supports dynamic schema registration via Pydantic + Cypher

**Implementation**:  
FalkorDB (lightweight graph DB) runs in Docker for dev/test and as standalone server in production. Python client (`falkordb` package) connects to server on `localhost:6379` by default.

---

## Entities

### 1. MetaType (Schema Definition)
Defines the structure and validation rules for Object Nodes and Edge Types.

**Fields:**
- `id` (UUID v4): Unique identifier.
- `name` (String): Name of the type (e.g., "Dashboard", "Table"). Must be PascalCase, alphanumeric only, max 50 characters. Reserved words: "MetaType", "ObjectNode", "StigmergicEdge".
- `type_category` (Enum: "NODE", "EDGE"): Whether this defines a node or an edge. Properties are defined within the `schema_definition`, not as separate graph elements.
- `schema_definition` (JSON/Dict): A valid JSON Schema representation of the Pydantic model. Supported data types: `string`, `integer`, `float`, `boolean`, `array` of strings.
- `health_score` (Float): Defaults to 1.0. Decrements by 0.1 on validation failures. If `health_score` <= 0.0, the MetaType is permanently locked and requires human intervention.
- `created_at` (Timestamp): Record of schema creation.
- `created_by_prompt_hash` (String): Hash of the prompt that created the schema.
- `rationale_summary` (String): AI-generated explanation detailing why this schema was created or patched.
- `relationship_class` (Enum: "STRUCTURAL", "FLOW", "NONE"): Distinguishes hierarchical containment (STRUCTURAL) from data lineage (FLOW) as mandated by Rule 2.4.
- `version` (Integer): Used for optimistic concurrency control during schema updates.

**Relationships:**
- `[:DEFINES]` -> `Object Node` or `Stigmergic Edge`

**Constraints:**
- MetaTypes cannot be deleted if they have existing Object Node instances.
- Existing Object Nodes are NOT automatically migrated when a MetaType is updated. Data migration is manual.

### 2. Object Node (Instance)
An instance of a MetaType, representing a Business Term or Technical Node.

**Fields:**
- `id` (UUID v4): Unique identifier.
- `meta_type_id` (UUID v4): Reference to the defining MetaType.
- `domain_scope` (String): The domain this node belongs to (e.g., "Finance", "Global"). Defaults to "Global".
- `properties` (JSON/Dict): The actual data, validated against the MetaType schema. Extra, undefined properties are silently stripped during insertion.

**Relationships:**
- `[:INSTANCE_OF]` -> `MetaType`
- `[:STIGMERGIC_LINK]` -> `Object Node`
- `[:VARIANTS]` -> `Object Node` (Used for Parallel Truths polysemy branching. Links domain-specific implementations to global/umbrella concepts).

### 3. Stigmergic Edge (Relationship)
A dynamic, confidence-weighted connection between nodes.

**Fields:**
- `id` (UUID v4): Unique identifier.
- `source_id` (UUID v4): Source Object Node ID.
- `target_id` (UUID v4): Target Object Node ID.
- `edge_type` (String): The type of relationship (e.g., "RELATES_TO", "POPULATES").
- `confidence_score` (Float): 0.0 to 1.0. Initialized at 0.5.
- `last_accessed` (Timestamp): Updated on traversal.
- `rationale_summary` (String): AI-generated explanation for the edge. Max 200 characters.
- `created_by_prompt_hash` (String): Hash of the prompt that created the edge. Defaults to "SYSTEM_GENERATED" if unavailable.
- `domain_scope` (String): The domain this edge belongs to. Defaults to the creator's `domain_scope`. If nodes are in different scopes, the edge takes the more restrictive scope.

### 4. Function Object
Represents an ETL operation or logic transformation.

**Fields:**
- `id` (UUID v4): Unique identifier.
- `name` (String): Name of the function.
- `logic_description` (String): Natural language description of the transformation for the AI to interpret (not executable code).
- `input_schema` (JSON/Dict): Expected input structure.
- `output_schema` (JSON/Dict): Expected output structure.

**Relationships:**
- `[:TRANSFORMS]` -> `Object Node`

## State Transitions

### Stigmergic Edge Lifecycle
1. **Creation**: `confidence_score` = 0.5, `last_accessed` = NOW().
2. **Reinforcement**: On traversal, `confidence_score` += 0.1 (max 1.0), `last_accessed` = NOW().
3. **Decay**: Periodically (decay pass), check each edge: if `NOW() - last_accessed > 7 days` (threshold), `confidence_score` -= 0.02 per 24h elapsed.
4. **Pruning**: If `confidence_score < 0.1`, delete edge automatically.
5. **Cascading Wither**: If attached node is deprecated, apply immediate 0.0 penalty (instant pruning).

### MetaType Health Lifecycle
1. **Creation**: `health_score` = 1.0.
2. **Validation Failure**: On failed insertion attempt (e.g., missing required fields, incorrect data types), `health_score` -= 0.1.
3. **Circuit Breaker**: If 3 consecutive failures in a session, lock actions for this type.
4. **Healing**: AI calls `patch_meta_type` tool with a valid JSON Schema update, which resets `health_score` to 1.0 and unlocks the type.