# MCP Tool Contracts: Stigmergic MCP Metadata Server Prototype

## 1. `bulk_ingest_seed`
**Purpose**: Ingest initial metadata without overwhelming the AI context window.
**Input**:
- `file_path` (String): Absolute path to the YAML bulk specification file.      
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
- `relationship_class` (Enum: "STRUCTURAL", "FLOW", "NONE"): Defines context grouping for Edge MetaTypes.
- `created_by_prompt_hash` (String): Hash of the prompt that requested the registration.
**Output**:
- `meta_type_id` (UUID): ID of the created MetaType.
- `status` (String): "SUCCESS" or "VALIDATION_ERROR".

## 3. `patch_meta_type`
**Purpose**: Heal or evolve a broken schema based on new data constraints.
**Input**:
- `name` (String): Name of the MetaType to patch.
- `patch_definition` (Dict): Partial Pydantic schema to apply.
- `created_by_prompt_hash` (String): Audit trail of prompting.
- `rationale_summary` (String): Why this schema is being updated.
**Output**:
- `status` (String): "SUCCESS" or "VALIDATION_ERROR".
- `new_version` (Integer): Updated version number of the schema.

## 4. `confirm_schema_heal`
**Purpose**: Unlocks the circuit breaker after an AI successfully evolves/patches a broken MetaType definition.
**Input**:
- `meta_type_name` (String): Name of the schema that was patched.
**Output**:
- `status` (String): SUCCESS if the breaker is unlocked.

## 5. `insert_node`
**Purpose**: Insert a new Object Node, validated against its MetaType.
**Input**:
- `meta_type_name` (String): Name of the MetaType.
- `properties` (Dict): Data to insert.
- `domain_scope` (String): Domain scope for the node.
- `created_by_prompt_hash` (String): Hash of the prompt.
**Output**:
- `node_id` (UUID): ID of the created node.
- `status` (String): "SUCCESS", "VALIDATION_ERROR", or "CIRCUIT_BREAKER_LOCKED".
- `error_details` (String, optional): Details if validation failed.

## 6. `create_stigmergic_edge`
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

## 7. `query_graph`
**Purpose**: Context-frugal querying of the graph.
**Input**:
- `query_intent` (String): Natural language or simplified query intent.
- `domain_scope` (String): User's domain scope.
- `max_depth` (Integer, default=2): Maximum traversal depth (1-2 hops).
- `page` (Integer, default=1): Pagination page number.
- `page_size` (Integer, default=5): Maximum 10 items.
**Output**:
- `results` (String): TOON-serialized, paginated results.
- `total_pages` (Integer): Total number of pages available.
- `current_page` (Integer): Current page number.
- `nodes_returned` (Integer): Number of nodes in this payload (max page_size).

## 8. `create_function`
**Purpose**: Register a Function Object representing an ETL operation or transformation.
**Input**:
- `name` (String): Name of the function.
- `logic_description` (String): Natural language description of the transformation (max 500 chars).
- `input_schema` (Dict): Expected input structure (JSON Schema).
- `output_schema` (Dict): Expected output structure (JSON Schema).
- `created_by_prompt_hash` (String): Audit trail of prompting.
**Output**:
- `function_id` (UUID): ID of the created Function Object.
- `status` (String): "SUCCESS" or "VALIDATION_ERROR".

## 9. `query_functions`
**Purpose**: Query registered Function Objects.
**Input**:
- `filter` (String, optional): Search by name or description.
- `domain_scope` (String): User's domain scope.
- `page` (Integer, default=1): Pagination page number.
**Output**:
- `functions` (String): TOON-serialized list of matching Function Objects (paginated).
- `total_count` (Integer): Total Function Objects matching filter.

## 10. `attach_function_to_nodes`
**Purpose**: Link a Function Object to one or more ObjectNodes (transformation lineage).
**Input**:
- `function_id` (UUID): ID of the Function Object.
- `target_node_ids` (Array[UUID]): ObjectNode IDs to attach the function to.
- `relationship_type` (String): Type of relationship (e.g., "TRANSFORMS", "DEPENDS_ON").
**Output**:
- `attachments_created` (Integer): Number of relationships created.
- `status` (String): "SUCCESS" or "PARTIAL_SUCCESS".

## 11. `delete_node` [APPROVAL_REQUIRED]
**Purpose**: Deletes a data node. Emits warnings or requires explicit cascade flags if relationships exist, as constrained by the Cascading Wither protocol.
**Input**:
- `node_id` (UUID): Target node.
- `cascade` (Boolean, default=False): If true, removes related edges.
- `rationale_summary` (String): Required explanation for deletion.
- `created_by_prompt_hash` (String): Audit tracking.
**Output**:
- `status` (String): "SUCCESS" or "CASCADE_WARNING".
- `edges_deleted` (Integer): Count of connected edges that withered.

## 12. `delete_meta_type` [APPROVAL_REQUIRED]
**Purpose**: Destroys an active schema using Supreme Court destruction hooks. Fails if active nodes depend on this schema without explicit override.
**Input**:
- `meta_type_id` (UUID): Schema to destroy.
- `force_override` (Boolean, default=False): Overrides active node checking.
- `rationale_summary` (String): Reason for dropping schema.
- `created_by_prompt_hash` (String): Audit tracking.
**Output**:
- `status` (String): "SUCCESS" or "IN_USE_ERROR".
- `nodes_affected` (Integer): Counter of objects referencing this MetaType.
