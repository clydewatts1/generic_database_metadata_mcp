# Function Object Tools - Task Breakdown

**Feature**: Implement Function Object management tools to enable ETL operation registration, querying, and linkage to ObjectNodes for transformation lineage tracking.

**Tools to Implement**:
- T065: `create_function` - Register an ETL operation with input/output schemas
- T066: `query_functions` - Query registered Function Objects by name or description
- T067: `attach_function_to_nodes` - Link Function Objects to ObjectNodes

**Status**: Ready for implementation (follows Rules 2.5, specification updated 2026-02-27)

---

## T065: Implement `create_function` MCP Tool

### T065.1 [P] Data Model: Extend `src/models/base.py` with FunctionObject schema
- **Task**: Add `FunctionObject` Pydantic model:
  - `id` (UUID v4): Unique identifier
  - `name` (String, max 100 chars, PascalCase): Function name (e.g., "ExtractPersonalData", "TransformSalaryToUSD")
  - `logic_description` (String, max 500 chars): Natural language description of transformation
  - `input_schema` (Dict/JSON Schema): Expected input structure (required fields, types)
  - `output_schema` (Dict/JSON Schema): Expected output structure
  - `created_by_profile_id` (String): Profile ID of creator (for domain scoping)
  - `domain_scope` (String, default "Global"): Domain this function applies to
  - `created_at` (Timestamp): Creation timestamp
  - `version` (Integer, default 1): Schema version for compatibility tracking
- **Output**: Updated `src/models/base.py` with FunctionObject model
- **Test**: Unit test in `tests/unit/test_models.py` verifying model validation

### T065.2 [P] Graph Layer: Create `src/graph/functions.py` module
- **Task**: Implement FunctionObject CRUD operations:
  - `create_function(name: str, logic_description: str, input_schema: dict, output_schema: dict, profile_id: str, domain_scope: str) -> UUID`: Creates node, validates schemas, returns function_id
  - `get_function(function_id: UUID) -> FunctionObject`: Retrieves function by ID with domain filtering
  - `list_functions(filter: str = None, domain_scope: str = "Global", page: int = 1) -> List[FunctionObject]`: Query with optional name/description filter, paginated
  - `update_function(function_id: UUID, updates: dict) -> bool`: Update function (name, logic_description, schemas), increment version
  - `delete_function(function_id: UUID) -> bool`: Delete function (cascades edge deletion)
- **Output**: New file `src/graph/functions.py` with all 5 operations
- **Dependencies**: Uses `src/graph/client.py` for FalkorDB connection
- **Test**: Unit tests in `tests/unit/test_functions.py` for all CRUD operations with ephemeral DB

### T065.3 MCP Tool: Implement `create_function` in `src/mcp_server/tools/functions.py`
- **Task**: Create tool handler:
  - **Input parameters**:
    - `name` (String): Function name (validation: PascalCase, alphanumeric+underscore, max 100 chars)
    - `logic_description` (String): Natural language description (max 500 chars)
    - `input_schema` (Dict): JSON Schema for inputs (validation: valid JSON Schema)
    - `output_schema` (Dict): JSON Schema for outputs (validation: valid JSON Schema)
    - `profile_id` (String): Creator's profile ID (injected by context middleware)
    - `domain_scope` (String, default "Global"): Domain scope (validated against profile scopes)
  - **Output**:
    - `function_id` (UUID): Created function's ID
    - `status` (String): "SUCCESS" or "VALIDATION_ERROR"
    - `error_details` (String, optional): Validation failure reason (e.g., "Invalid JSON Schema in input_schema")
  - **Logic**:
    - Validate input/output schemas are valid JSON Schema (catch malformed schemas)
    - Call `create_function()` from graph layer
    - Return compact response (TOON-serialized if > 1 function returned, but this tool returns single object)
  - **Error handling**: Return validation errors if name format invalid, schemas malformed, or permission denied
- **Output**: New file `src/mcp_server/tools/functions.py` with `create_function` tool implementation
- **Test**: Integration test in `tests/integration/test_tools.py` testing success and error cases

### T065.4 Update `src/mcp_server/server.py` to register `create_function` tool
- **Task**: Add tool registration:
  ```python
  from src.mcp_server.tools.functions import create_function
  # In _register_tools():
  server.tool("create_function", create_function, ...)
  ```
- **Output**: Updated `src/mcp_server/server.py` with tool registered and accessible via MCP

---

## T066: Implement `query_functions` MCP Tool

### T066.1 [P] Graph Layer: Extend `src/graph/functions.py` with search/filter
- **Task**: Implement smart search:
  - `search_functions(filter: str, domain_scope: str) -> List[FunctionObject]`: Full-text search in name + logic_description
  - Pagination support: `search_functions(..., page: int, page_size: int = 5)`
  - Returns TOON-serialized list if > 5 results
- **Output**: Updated `src/graph/functions.py` with search method
- **Test**: Unit tests for search with various filter patterns (substring, partial match, empty filter)

### T066.2 MCP Tool: Implement `query_functions` in `src/mcp_server/tools/functions.py`
- **Task**: Create tool handler:
  - **Input parameters**:
    - `filter` (String, optional): Search by name or description substring (case-insensitive)
    - `domain_scope` (String): User's domain scope (injected by context middleware)
    - `page` (Integer, default 1): Pagination page number
  - **Output**:
    - `functions` (String): TOON-serialized list of matching FunctionObjects (max 5 per page)
    - `total_count` (Integer): Total Function Objects matching filter
    - `current_page` (Integer): Current page number
    - `total_pages` (Integer): Total pages available
  - **Logic**:
    - Call `search_functions()` with filter and domain_scope
    - TOON-serialize results (strip default values, abbreviate keys)
    - Paginate if > 5 results
    - Return empty list if no matches (not an error)
  - **Error handling**: Return error only if domain_scope validation fails
- **Output**: Updated `src/mcp_server/tools/functions.py` with `query_functions` tool
- **Test**: Integration test for search with various filters

### T066.3 Update `src/mcp_server/server.py` to register `query_functions` tool
- **Task**: Add tool registration for `query_functions`
- **Output**: Updated `src/mcp_server/server.py`

---

## T067: Implement `attach_function_to_nodes` MCP Tool

### T067.1 [P] Graph Layer: Relationship CRUD in `src/graph/functions.py`
- **Task**: Implement attachment operations:
  - `attach_function_to_node(function_id: UUID, node_id: UUID, relationship_type: str) -> bool`: Create (:FunctionObject)-[relationship_type]->(:ObjectNode)
  - `list_function_for_node(node_id: UUID) -> List[Dict]`: Get all functions attached to a node with their relationship types
  - `detach_function_from_node(function_id: UUID, node_id: UUID, relationship_type: str) -> bool`: Delete relationship
  - Validate: Both function_id and node_id must exist; relationship_type in ["TRANSFORMS", "DEPENDS_ON", "PRODUCES", "CONSUMES"] (enum)
- **Output**: Updated `src/graph/functions.py` with relation methods
- **Test**: Unit tests for attach/detach/list operations

### T067.2 MCP Tool: Implement `attach_function_to_nodes` in `src/mcp_server/tools/functions.py`
- **Task**: Create tool handler:
  - **Input parameters**:
    - `function_id` (UUID): Function to attach
    - `target_node_ids` (Array[UUID]): ObjectNode IDs to attach to (supports multiple)
    - `relationship_type` (String): Relationship type ("TRANSFORMS", "DEPENDS_ON", "PRODUCES", "CONSUMES")
    - `profile_id` (String): Caller's profile (injected)
  - **Output**:
    - `attachments_created` (Integer): Number of successful relationships created
    - `attachments_failed` (Integer): Number of failures (e.g., node not found)
    - `failed_node_ids` (Array[UUID], optional): Which node IDs failed (for debugging)
    - `status` (String): "SUCCESS", "PARTIAL_SUCCESS", or "VALIDATION_ERROR"
  - **Logic**:
    - Validate function_id exists
    - For each target_node_id, validate it exists
    - Create relationship for each valid node
    - Return count of successes/failures
    - Domain scoping: Both function and nodes must have compatible domain_scope
  - **Error handling**: 
    - Return error if function_id not found
    - Continue with other nodes if one fails (partial success)
    - Return error if relationship_type invalid
- **Output**: Updated `src/mcp_server/tools/functions.py` with `attach_function_to_nodes` tool
- **Test**: Integration test for single and batch attachments, error cases

### T067.3 Update `src/mcp_server/server.py` to register `attach_function_to_nodes` tool
- **Task**: Add tool registration
- **Output**: Updated `src/mcp_server/server.py`

---

## T068: Integration Testing

### T068.1 [P] Create `tests/unit/test_functions.py`
- **Task**: Unit tests for `src/graph/functions.py`:
  - Test `create_function()` with valid/invalid schemas
  - Test `get_function()` with existing/non-existing IDs
  - Test `list_functions()` pagination
  - Test `search_functions()` with various filters
  - Test `attach_function_to_node()` validation
  - Test cascading delete (delete function → prune edges)
  - Use ephemeral FalkorDB fixture from `conftest.py`
- **Output**: New file `tests/unit/test_functions.py` with >20 test cases

### T068.2 [P] Create `tests/integration/test_function_tools.py`
- **Task**: Integration tests for MCP tools:
  - Test `create_function` tool with valid inputs → returns function_id
  - Test `create_function` with invalid JSON Schema → returns VALIDATION_ERROR
  - Test `query_functions` with empty DB → returns empty list
  - Test `query_functions` with filter matching multiple functions → paginated, TOON-serialized
  - Test `attach_function_to_nodes` with batch inputs → returns partial_success stats
  - Test domain scoping: Finance function can't attach to Global node (validation)
  - Test error handling: non-existent function_id
- **Output**: New file `tests/integration/test_function_tools.py` with >15 integration tests

### T068.3 Update existing tests to verify Function Object don't break other features
- **Task**: Run all existing tests (`test_ontology.py`, `test_ingestion.py`, etc.) to ensure no regressions
- **Output**: Confirmed test suite passes (baseline unchanged)

---

## T069: Documentation Updates

### T069.1 [P] Update `specs/001-mcp-prototype/contracts/mcp-tools.md`
- **Task**: Add function object tool contracts (already done, but verify completeness):
  - Tools 6-8: create_function, query_functions, attach_function_to_nodes
  - Include input/output parameter details
  - Include error codes and examples
- **Output**: Verified `contracts/mcp-tools.md` has all 3 tools fully specified

### T069.2 [P] Update `README.md` with Function Object examples
- **Task**: Add usage examples for the 3 new tools:
  - Example JSON for `create_function` (e.g., ExtractPersonalData with schemas)
  - Example `query_functions` response (paginated, TOON-formatted)
  - Example `attach_function_to_nodes` batch request
- **Output**: Updated `README.md` with tool examples section

### T069.3 Update `specs/001-mcp-prototype/data-model.md`
- **Task**: Add Function Object entity detail (already there, but expand):
  - Relationships: (:FunctionObject)-[TRANSFORMS|DEPENDS_ON|PRODUCES|CONSUMES]->(:ObjectNode)
  - Lifecycle notes: Cascading delete when node is deleted
  - Domain scoping rules: Function → ObjectNode scope validation
- **Output**: Updated `data-model.md` with complete Function Object documentation

---

## T070: Code Integration

### T070.1 Update `src/mcp_server/server.py` to register all 3 tools
- **Task**: Import and register create_function, query_functions, attach_function_to_nodes
- **Output**: Updated `src/mcp_server/server.py` with 3 new tool registrations

### T070.2 [P] Update `src/utils/context.py` if needed for domain scoping injection
- **Task**: Verify profile_id and domain_scope are correctly injected into function tools
- **Output**: Confirmed context middleware works with function tools (or updates made if needed)

### T070.3 [P] Update `src/models/__init__.py` to export FunctionObject
- **Task**: Add FunctionObject to module exports for cleaner imports
- **Output**: Updated `src/models/__init__.py`

---

## Task Summary

| Task ID | Description | File(s) | Dependencies |
|---------|-------------|---------|--------------|
| T065.1 | Data Model: FunctionObject in base.py | src/models/base.py | None |
| T065.2 | Graph Layer: CRUD in functions.py | src/graph/functions.py | T065.1 |
| T065.3 | MCP Tool: create_function | src/mcp_server/tools/functions.py | T065.2 |
| T065.4 | Register create_function in server.py | src/mcp_server/server.py | T065.3 |
| T066.1 | Graph Layer: Search in functions.py | src/graph/functions.py | T065.2 |
| T066.2 | MCP Tool: query_functions | src/mcp_server/tools/functions.py | T066.1 |
| T066.3 | Register query_functions in server.py | src/mcp_server/server.py | T066.2 |
| T067.1 | Graph Layer: Relationships in functions.py | src/graph/functions.py | T065.2 |
| T067.2 | MCP Tool: attach_function_to_nodes | src/mcp_server/tools/functions.py | T067.1 |
| T067.3 | Register attach_function_to_nodes in server.py | src/mcp_server/server.py | T067.2 |
| T068.1 | Unit tests: test_functions.py | tests/unit/test_functions.py | T065-T067 |
| T068.2 | Integration tests: test_function_tools.py | tests/integration/test_function_tools.py | T065-T067 |
| T068.3 | Regression test suite | all tests | T068.1-T068.2 |
| T069.1 | Contracts documentation | specs/.../contracts/mcp-tools.md | Done (verify) |
| T069.2 | README examples | README.md | T065-T067 |
| T069.3 | Data model documentation | data-model.md | Done (expand) |
| T070.1 | Register all tools in server.py | src/mcp_server/server.py | T065.4, T066.3, T067.3 |
| T070.2 | Context injection verification | src/utils/context.py | None |
| T070.3 | Module exports | src/models/__init__.py | T065.1 |

**Total Subtasks**: 19 (organized into 5 major tasks T065-T069)
**Parallel Opportunities**: T065.1 & T065.2 [P], T066.1, T067.1 (data layer independence), T068.1 & T068.2 [P], T069.1 & T069.2 [P]

---

## Implementation Sequence

### Sequential Path (Single Developer)
1. **T065.1** → T065.2 → T065.3 → T065.4 (create_function complete)
2. **T066.1** → T066.2 → T066.3 (query_functions complete)
3. **T067.1** → T067.2 → T067.3 (attach complete)
4. **T068.1 & T068.2** in parallel (tests)
5. **T069** & **T070** (docs + integration)

### Parallel Path (Multiple Developers)
- **Developer A**: T065 (create_function) + T068.1 (unit tests)
- **Developer B**: T066 + T067 (query + attach)
- **Developer C**: T068.2 (integration tests) + T069 (docs)
- **Final Integration**: T070

**Estimated Effort**: 40-60 person-hours for sequential, 20-30 for 3-developer parallel

---

## Success Criteria (Updated SC)

- **SC-006a**: `create_function` tool successfully registers ETL operations with JSON Schema validation
- **SC-006b**: `query_functions` returns paginated, TOON-serialized results (max 5 per page) with optional filtering
- **SC-006c**: `attach_function_to_nodes` creates 1-N relationships with domain scope validation
- **SC-006d**: All 3 tools have >80% unit test coverage with ephemeral DB fixtures
- **SC-006e**: Cascading delete works: deleting a function prunes all attached edges
- **SC-006f**: Domain scoping enforced: Function in Finance scope can't attach to Global-scoped nodes (validation error)
