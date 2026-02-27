"""Graph operations for Object Nodes (CRUD and bulk ingest)."""

import json
from typing import Any

from pydantic import ValidationError as PydanticValidationError

from .client import execute_query
from ..models.base import MetaType, ObjectNode, ObjectNodeCreate
from ..models.dynamic import validate_properties
from ..utils.logging import ValidationError, get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _row_to_object_node(row: list[Any]) -> ObjectNode:
    node = row[0]
    props = node.properties
    return ObjectNode(
        id=props["id"],
        meta_type_id=props["meta_type_id"],
        domain_scope=props.get("domain_scope", "Global"),
        profile_id=props.get("profile_id", "SYSTEM"),  # Rule 5.1
        properties=json.loads(props.get("properties", "{}")),
    )


# ---------------------------------------------------------------------------
# Create (single)
# ---------------------------------------------------------------------------

def create_node(meta_type: MetaType, data: ObjectNodeCreate) -> ObjectNode:
    """Validate *data* against *meta_type* schema then persist to the graph.

    Raises:
        ValidationError: if properties do not satisfy the MetaType schema.
    """
    try:
        clean_props = validate_properties(meta_type, data.properties)
    except PydanticValidationError as exc:
        raise ValidationError(str(exc)) from exc

    node = ObjectNode(
        meta_type_id=meta_type.id,
        domain_scope=data.domain_scope,
        profile_id=data.profile_id,  # Rule 5.1
        properties=clean_props,
    )

    execute_query(
        "CREATE (n:ObjectNode {"
        "  id: $id,"
        "  meta_type_id: $meta_type_id,"
        "  domain_scope: $domain_scope,"
        "  profile_id: $profile_id,"
        "  properties: $properties"
        "})",
        {
            "id": node.id,
            "meta_type_id": node.meta_type_id,
            "domain_scope": node.domain_scope,
            "profile_id": node.profile_id,  # Rule 5.1
            "properties": json.dumps(node.properties),
        },
    )
    logger.debug("ObjectNode created: %s (type=%s)", node.id, meta_type.name)
    return node


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------

def get_node_by_id(node_id: str) -> ObjectNode | None:
    result = execute_query(
        "MATCH (n:ObjectNode {id: $id}) RETURN n",
        {"id": node_id},
    )
    rows = result.result_set
    return _row_to_object_node(rows[0]) if rows else None


def list_nodes_by_type(meta_type_id: str, limit: int = 100) -> list[ObjectNode]:
    result = execute_query(
        "MATCH (n:ObjectNode {meta_type_id: $meta_type_id}) RETURN n LIMIT $limit",
        {"meta_type_id": meta_type_id, "limit": limit},
    )
    return [_row_to_object_node(row) for row in result.result_set]


# ---------------------------------------------------------------------------
# Bulk ingest
# ---------------------------------------------------------------------------

def bulk_ingest(
    meta_type: MetaType,
    property_list: list[dict[str, Any]],
    domain_scope: str = "Global",
) -> dict[str, Any]:
    """Insert many nodes without returning full node data (context-frugal).

    Returns a summary dict: {"inserted": N, "failed": M}.
    """
    inserted = 0
    failed = 0
    errors: list[str] = []

    for props in property_list:
        try:
            create_node(
                meta_type,
                ObjectNodeCreate(
                    meta_type_id=meta_type.id,
                    domain_scope=domain_scope,
                    properties=props,
                ),
            )
            inserted += 1
        except (ValidationError, PydanticValidationError) as exc:
            failed += 1
            # Collect only first 10 error messages to keep summary compact
            if len(errors) < 10:
                errors.append(str(exc)[:100])

    summary: dict[str, Any] = {
        "meta_type": meta_type.name,
        "inserted": inserted,
        "failed": failed,
    }
    if errors:
        summary["sample_errors"] = errors
    return summary
