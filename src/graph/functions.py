"""Graph operations for FunctionObject nodes and their ObjectNode relationships."""

from __future__ import annotations

import json
from typing import Any

from .client import execute_query
from ..models.base import FunctionObject, FunctionObjectCreate
from ..utils.logging import NotFoundError, ValidationError, get_logger

logger = get_logger(__name__)

ALLOWED_RELATIONSHIP_TYPES = {"TRANSFORMS", "DEPENDS_ON", "PRODUCES", "CONSUMES"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _row_to_function_object(row: list[Any]) -> FunctionObject:
    node = row[0]
    props = node.properties
    return FunctionObject(
        id=props["id"],
        name=props["name"],
        logic_description=props["logic_description"],
        input_schema=json.loads(props.get("input_schema", "{}")),
        output_schema=json.loads(props.get("output_schema", "{}")),
        created_by_profile_id=props.get("created_by_profile_id", "SYSTEM"),
        domain_scope=props.get("domain_scope", "Global"),
        created_at=props.get("created_at"),
        version=int(props.get("version", 1)),
    )


def _get_object_node_domain_scope(node_id: str) -> str | None:
    result = execute_query(
        "MATCH (n:ObjectNode {id: $id}) RETURN n.domain_scope",
        {"id": node_id},
    )
    rows = result.result_set
    if not rows:
        return None
    return str(rows[0][0])


def _get_function_domain_scope(function_id: str) -> str | None:
    result = execute_query(
        "MATCH (f:FunctionObject {id: $id}) RETURN f.domain_scope",
        {"id": function_id},
    )
    rows = result.result_set
    if not rows:
        return None
    return str(rows[0][0])


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


def create_function(
    data: FunctionObjectCreate,
    domain_scope: str = "Global",
) -> FunctionObject:
    """Create and persist a FunctionObject node.

    Raises:
        ValueError: if a FunctionObject with the same name already exists.
    """
    existing = get_function_by_name(data.name)
    if existing is not None:
        raise ValueError(f"FunctionObject '{data.name}' already exists (id={existing.id}).")

    function_obj = FunctionObject(
        name=data.name,
        logic_description=data.logic_description,
        input_schema=data.input_schema,
        output_schema=data.output_schema,
        created_by_profile_id=data.profile_id,
        domain_scope=domain_scope,
    )

    execute_query(
        "CREATE (f:FunctionObject {"
        "  id: $id,"
        "  name: $name,"
        "  logic_description: $logic_description,"
        "  input_schema: $input_schema,"
        "  output_schema: $output_schema,"
        "  created_by_profile_id: $created_by_profile_id,"
        "  domain_scope: $domain_scope,"
        "  created_at: $created_at,"
        "  version: $version"
        "})",
        {
            "id": function_obj.id,
            "name": function_obj.name,
            "logic_description": function_obj.logic_description,
            "input_schema": json.dumps(function_obj.input_schema),
            "output_schema": json.dumps(function_obj.output_schema),
            "created_by_profile_id": function_obj.created_by_profile_id,
            "domain_scope": function_obj.domain_scope,
            "created_at": function_obj.created_at.isoformat(),
            "version": function_obj.version,
        },
    )
    logger.info(
        "FunctionObject created: %s (%s) by %s in domain %s",
        function_obj.name,
        function_obj.id,
        function_obj.created_by_profile_id,
        function_obj.domain_scope,
    )
    return function_obj


def get_function_by_id(function_id: str, domain_scope: str | None = None) -> FunctionObject | None:
    """Retrieve a FunctionObject by id, optionally scoped by domain."""
    if domain_scope:
        result = execute_query(
            "MATCH (f:FunctionObject {id: $id}) "
            "WHERE f.domain_scope IN [$domain_scope, 'Global'] "
            "RETURN f",
            {"id": function_id, "domain_scope": domain_scope},
        )
    else:
        result = execute_query(
            "MATCH (f:FunctionObject {id: $id}) RETURN f",
            {"id": function_id},
        )
    rows = result.result_set
    return _row_to_function_object(rows[0]) if rows else None


def get_function_by_name(name: str, domain_scope: str | None = None) -> FunctionObject | None:
    """Retrieve a FunctionObject by name, optionally scoped by domain."""
    if domain_scope:
        result = execute_query(
            "MATCH (f:FunctionObject {name: $name}) "
            "WHERE f.domain_scope IN [$domain_scope, 'Global'] "
            "RETURN f",
            {"name": name, "domain_scope": domain_scope},
        )
    else:
        result = execute_query(
            "MATCH (f:FunctionObject {name: $name}) RETURN f",
            {"name": name},
        )
    rows = result.result_set
    return _row_to_function_object(rows[0]) if rows else None


def list_functions(
    domain_scope: str = "Global",
    page: int = 1,
    page_size: int = 5,
) -> tuple[list[FunctionObject], int]:
    """List FunctionObjects visible to domain_scope, with pagination.

    Returns:
        tuple[list[FunctionObject], int]: (items, total_count)
    """
    page = max(page, 1)
    page_size = max(page_size, 1)
    skip = (page - 1) * page_size

    count_result = execute_query(
        "MATCH (f:FunctionObject) "
        "WHERE f.domain_scope IN [$domain_scope, 'Global'] "
        "RETURN count(f)",
        {"domain_scope": domain_scope},
    )
    total_count = int(count_result.result_set[0][0]) if count_result.result_set else 0

    result = execute_query(
        "MATCH (f:FunctionObject) "
        "WHERE f.domain_scope IN [$domain_scope, 'Global'] "
        "RETURN f ORDER BY f.name SKIP $skip LIMIT $limit",
        {
            "domain_scope": domain_scope,
            "skip": skip,
            "limit": page_size,
        },
    )
    return ([_row_to_function_object(row) for row in result.result_set], total_count)


def search_functions(
    filter_text: str,
    domain_scope: str = "Global",
    page: int = 1,
    page_size: int = 5,
) -> tuple[list[FunctionObject], int]:
    """Search FunctionObjects by name/logic_description, with pagination."""
    filter_text = (filter_text or "").strip()
    if not filter_text:
        return list_functions(domain_scope=domain_scope, page=page, page_size=page_size)

    page = max(page, 1)
    page_size = max(page_size, 1)
    skip = (page - 1) * page_size
    lowered = filter_text.lower()

    count_result = execute_query(
        "MATCH (f:FunctionObject) "
        "WHERE f.domain_scope IN [$domain_scope, 'Global'] "
        "  AND (toLower(f.name) CONTAINS $filter OR toLower(f.logic_description) CONTAINS $filter) "
        "RETURN count(f)",
        {"domain_scope": domain_scope, "filter": lowered},
    )
    total_count = int(count_result.result_set[0][0]) if count_result.result_set else 0

    result = execute_query(
        "MATCH (f:FunctionObject) "
        "WHERE f.domain_scope IN [$domain_scope, 'Global'] "
        "  AND (toLower(f.name) CONTAINS $filter OR toLower(f.logic_description) CONTAINS $filter) "
        "RETURN f ORDER BY f.name SKIP $skip LIMIT $limit",
        {
            "domain_scope": domain_scope,
            "filter": lowered,
            "skip": skip,
            "limit": page_size,
        },
    )
    return ([_row_to_function_object(row) for row in result.result_set], total_count)


def update_function(function_id: str, updates: dict[str, Any]) -> FunctionObject:
    """Update mutable fields and increment FunctionObject version."""
    existing = get_function_by_id(function_id)
    if existing is None:
        raise NotFoundError("FunctionObject", function_id)

    mutable_fields = {"name", "logic_description", "input_schema", "output_schema", "domain_scope"}
    safe_updates = {k: v for k, v in updates.items() if k in mutable_fields}
    if not safe_updates:
        return existing

    if "input_schema" in safe_updates:
        safe_updates["input_schema"] = json.dumps(safe_updates["input_schema"])
    if "output_schema" in safe_updates:
        safe_updates["output_schema"] = json.dumps(safe_updates["output_schema"])

    set_clauses = [f"f.{field} = ${field}" for field in safe_updates.keys()]
    set_clauses.append("f.version = f.version + 1")

    query = (
        "MATCH (f:FunctionObject {id: $id}) "
        f"SET {', '.join(set_clauses)} "
        "RETURN f"
    )
    params = {"id": function_id, **safe_updates}
    execute_query(query, params)

    updated = get_function_by_id(function_id)
    if updated is None:
        raise NotFoundError("FunctionObject", function_id)
    return updated


def delete_function(function_id: str) -> bool:
    """Delete a FunctionObject and all attached relationships."""
    existing = get_function_by_id(function_id)
    if existing is None:
        return False

    execute_query(
        "MATCH (f:FunctionObject {id: $id})-[r]-() DELETE r",
        {"id": function_id},
    )
    execute_query(
        "MATCH (f:FunctionObject {id: $id}) DELETE f",
        {"id": function_id},
    )
    logger.info("FunctionObject deleted: %s", function_id)
    return True


# ---------------------------------------------------------------------------
# Relationships to ObjectNode
# ---------------------------------------------------------------------------


def attach_function_to_node(function_id: str, node_id: str, relationship_type: str) -> bool:
    """Create a typed relationship from FunctionObject to ObjectNode.

    Rules:
    - relationship_type must be in ALLOWED_RELATIONSHIP_TYPES
    - function and node must both exist
    - domain scopes must match exactly
    """
    if relationship_type not in ALLOWED_RELATIONSHIP_TYPES:
        raise ValidationError(
            f"Invalid relationship_type '{relationship_type}'. Allowed: {sorted(ALLOWED_RELATIONSHIP_TYPES)}"
        )

    function_scope = _get_function_domain_scope(function_id)
    if function_scope is None:
        raise NotFoundError("FunctionObject", function_id)

    node_scope = _get_object_node_domain_scope(node_id)
    if node_scope is None:
        raise NotFoundError("ObjectNode", node_id)

    if function_scope != node_scope:
        raise ValidationError(
            f"Domain scope mismatch: FunctionObject={function_scope}, ObjectNode={node_scope}."
        )

    query = (
        "MATCH (f:FunctionObject {id: $function_id}), (n:ObjectNode {id: $node_id}) "
        f"MERGE (f)-[r:{relationship_type}]->(n) "
        "RETURN count(r)"
    )
    result = execute_query(
        query,
        {
            "function_id": function_id,
            "node_id": node_id,
        },
    )
    return bool(result.result_set and int(result.result_set[0][0]) >= 1)


def list_functions_for_node(node_id: str) -> list[dict[str, Any]]:
    """Return all FunctionObjects attached to an ObjectNode."""
    result = execute_query(
        "MATCH (f:FunctionObject)-[r]->(n:ObjectNode {id: $node_id}) "
        "RETURN f, type(r)",
        {"node_id": node_id},
    )

    rows = result.result_set
    output: list[dict[str, Any]] = []
    for row in rows:
        function_obj = _row_to_function_object([row[0]])
        output.append(
            {
                "function": function_obj,
                "relationship_type": row[1],
            }
        )
    return output


def detach_function_from_node(function_id: str, node_id: str, relationship_type: str) -> bool:
    """Remove a typed relationship from FunctionObject to ObjectNode."""
    if relationship_type not in ALLOWED_RELATIONSHIP_TYPES:
        raise ValidationError(
            f"Invalid relationship_type '{relationship_type}'. Allowed: {sorted(ALLOWED_RELATIONSHIP_TYPES)}"
        )

    result = execute_query(
        "MATCH (f:FunctionObject {id: $function_id})-[r]->(n:ObjectNode {id: $node_id}) "
        "WHERE type(r) = $relationship_type "
        "DELETE r RETURN count(r)",
        {
            "function_id": function_id,
            "node_id": node_id,
            "relationship_type": relationship_type,
        },
    )
    return bool(result.result_set and int(result.result_set[0][0]) >= 1)
