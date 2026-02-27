# Data Model: Stigmergic MCP Metadata Server Prototype

## Entities

### 1. MetaType (Schema Definition)
Defines the structure and validation rules for Object Nodes and Edge Types.

**Fields:**
- `id` (UUID v4): Unique identifier.
- `name` (String): Name of the type (e.g., "Dashboard", "Table").
- `type_category` (Enum: "NODE", "EDGE"): Whether this defines a node or an edge.
- `schema_definition` (JSON/Dict): The Pydantic schema definition (fields, types, required status).
- `health_score` (Float): Defaults to 1.0. Decrements on validation failures.

**Relationships:**
- `[:DEFINES]` -> `Object Node` or `Stigmergic Edge`

### 2. Object Node (Instance)
An instance of a MetaType, representing a Business Term or Technical Node.

**Fields:**
- `id` (UUID v4): Unique identifier.
- `meta_type_id` (UUID v4): Reference to the defining MetaType.
- `domain_scope` (String): The domain this node belongs to (e.g., "Finance", "Global").
- `properties` (JSON/Dict): The actual data, validated against the MetaType schema.

**Relationships:**
- `[:INSTANCE_OF]` -> `MetaType`
- `[:STIGMERGIC_LINK]` -> `Object Node`

### 3. Stigmergic Edge (Relationship)
A dynamic, confidence-weighted connection between nodes.

**Fields:**
- `id` (UUID v4): Unique identifier.
- `source_id` (UUID v4): Source Object Node ID.
- `target_id` (UUID v4): Target Object Node ID.
- `edge_type` (String): The type of relationship (e.g., "RELATES_TO", "POPULATES").
- `confidence_score` (Float): 0.0 to 1.0. Initialized at 0.5.
- `last_accessed` (Timestamp): Updated on traversal.
- `rationale_summary` (String): AI-generated explanation for the edge.
- `created_by_prompt_hash` (String): Hash of the prompt that created the edge.
- `domain_scope` (String): The domain this edge belongs to.

### 4. Function Object
Represents an ETL operation or logic transformation.

**Fields:**
- `id` (UUID v4): Unique identifier.
- `name` (String): Name of the function.
- `logic_description` (String): Description of the transformation.

**Relationships:**
- `[:TRANSFORMS]` -> `Object Node`

## State Transitions

### Stigmergic Edge Lifecycle
1. **Creation**: `confidence_score` = 0.5, `last_accessed` = NOW().
2. **Reinforcement**: On traversal, `confidence_score` += 0.1 (max 1.0), `last_accessed` = NOW().
3. **Decay**: Periodically, if `NOW() - last_accessed > threshold`, `confidence_score` -= decay_rate.
4. **Pruning**: If `confidence_score < 0.1`, delete edge.
5. **Cascading Wither**: If attached node is deprecated, `confidence_score` = 0.0 (immediate pruning).

### MetaType Health Lifecycle
1. **Creation**: `health_score` = 1.0.
2. **Validation Failure**: On failed insertion attempt, `health_score` -= 0.1.
3. **Circuit Breaker**: If 3 consecutive failures in a session, lock actions for this type.
4. **Healing**: AI patches schema, `health_score` resets to 1.0.