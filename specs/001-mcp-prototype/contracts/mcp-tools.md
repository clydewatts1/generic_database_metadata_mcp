# MCP Tool Contracts: Stigmergic MCP Metadata Server Prototype

## 1. `bulk_ingest_seed`
**Purpose**: Ingest initial metadata without overwhelming the AI context window.
**Input**:
- `file_path` (String): Absolute path to the data file (e.g., CSV).
**Output**:
- `success` (Boolean): True if ingestion was successful.
- `nodes_created` (Integer): Number of nodes created.
- `edges_created` (Integer): Number of edges created.
- `message` (String): Summary message (must be < 10KB).

## 2. `register_meta_type`
**Purpose**: Dynamically register a new Object Type or Edge Type.
**Input**:
- `name` (String): Name of the type.
- `type_category` (Enum: "NODE", "EDGE"): Category of the type.
- `schema_definition` (Dict): Pydantic schema definition.
**Output**:
- `meta_type_id` (UUID): ID of the created MetaType.
- `status` (String): "SUCCESS" or "VALIDATION_ERROR".

## 3. `insert_node`
**Purpose**: Insert a new Object Node, validated against its MetaType.
**Input**:
- `meta_type_name` (String): Name of the MetaType.
- `properties` (Dict): Data to insert.
- `domain_scope` (String): Domain scope for the node.
**Output**:
- `node_id` (UUID): ID of the created node.
- `status` (String): "SUCCESS", "VALIDATION_ERROR", or "CIRCUIT_BREAKER_LOCKED".
- `error_details` (String, optional): Details if validation failed.

## 4. `create_stigmergic_edge`
**Purpose**: Create a confidence-weighted connection between two nodes.
**Input**:
- `source_id` (UUID): Source node ID.
- `target_id` (UUID): Target node ID.
- `edge_type` (String): Type of relationship.
- `rationale_summary` (String): AI explanation for the edge.
- `created_by_prompt_hash` (String): Hash of the prompt.
**Output**:
- `edge_id` (UUID): ID of the created edge.
- `initial_confidence` (Float): Initial confidence score (e.g., 0.5).

## 5. `query_graph`
**Purpose**: Context-frugal querying of the graph.
**Input**:
- `query_intent` (String): Natural language or simplified query intent.
- `domain_scope` (String): User's domain scope.
- `max_depth` (Integer, default=2): Maximum traversal depth (1-2 hops).
- `page` (Integer, default=1): Pagination page number.
**Output**:
- `results` (String): TOON-serialized, paginated results.
- `total_pages` (Integer): Total number of pages available.
- `current_page` (Integer): Current page number.
- `nodes_returned` (Integer): Number of nodes in this payload (max 5 per page).

## 6. `create_function`
**Purpose**: Register a Function Object representing an ETL operation or transformation.
**Input**:
- `name` (String): Name of the function.
- `logic_description` (String): Natural language description of the transformation (max 500 chars).
- `input_schema` (Dict): Expected input structure (JSON Schema).
- `output_schema` (Dict): Expected output structure (JSON Schema).
**Output**:
- `function_id` (UUID): ID of the created Function Object.
- `status` (String): "SUCCESS" or "VALIDATION_ERROR".

## 7. `query_functions`
**Purpose**: Query registered Function Objects.
**Input**:
- `filter` (String, optional): Search by name or description.
- `domain_scope` (String): User's domain scope.
**Output**:
- `functions` (String): TOON-serialized list of matching Function Objects (paginated if > 5).
- `total_count` (Integer): Total Function Objects matching filter.

## 8. `attach_function_to_nodes`
**Purpose**: Link a Function Object to one or more ObjectNodes (transformation lineage).
**Input**:
- `function_id` (UUID): ID of the Function Object.
- `target_node_ids` (Array[UUID]): ObjectNode IDs to attach the function to.
- `relationship_type` (String): Type of relationship (e.g., "TRANSFORMS", "DEPENDS_ON").
**Output**:
- `attachments_created` (Integer): Number of relationships created.
- `status` (String): "SUCCESS" or "PARTIAL_SUCCESS".