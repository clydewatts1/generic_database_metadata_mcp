"""MCP tool: register_meta_type – dynamically register a new Object or Edge type."""

from typing import Any, Dict

from pydantic import ValidationError as PydanticValidationError

from ..app import mcp
from ...models.base import MetaTypeCreate, TypeCategory
from ...models.serialization import serialise
from ...graph.ontology import (
    create_meta_type,
    list_meta_types,
    patch_meta_type,
    insert_object_node,
    get_meta_type_by_id,
    get_circuit_breaker_status,
    reset_circuit_breaker,
)
from ...utils.logging import get_logger, LockedError, CircuitBreakerError

logger = get_logger(__name__)


@mcp.tool()
def register_meta_type(
    name: str,
    type_category: str,
    schema_definition: Dict[str, Any],
    profile_id: str,
    domain_scope: str = "Global",
) -> str:
    """Register a new MetaType (Object Type or Edge Type) in the graph.

    Args:
        name: PascalCase type name, e.g. "Dashboard". Max 50 chars.
        type_category: "NODE" or "EDGE".
        schema_definition: JSON Schema dict defining fields and their types.
            Each key is a field name; value is {"type": "string|integer|float|boolean|array",
            "required": true|false}.
        profile_id: ID of the user/profile registering this type (Rule 5.1).
        domain_scope: Domain this MetaType applies to (Rule 5.2). Defaults to "Global".

    Returns:
        TOON JSON with the created MetaType id, name, and schema summary.
    """
    try:
        data = MetaTypeCreate(
            name=name,
            type_category=TypeCategory(type_category),
            schema_definition=schema_definition,
        )
    except (PydanticValidationError, ValueError) as exc:
        return serialise({"error": "VALIDATION_ERROR", "message": str(exc)})

    try:
        mt = create_meta_type(data, profile_id=profile_id, domain_scope=domain_scope)
        logger.info("Tool register_meta_type: created %s by %s in %s", mt.name, profile_id, domain_scope)
        return serialise({
            "id": mt.id,
            "name": mt.name,
            "type_category": mt.type_category.value,
            "fields": list(mt.schema_definition.keys()),
        })
    except ValueError as exc:
        return serialise({"error": "CONFLICT", "message": str(exc)})


@mcp.tool()
def list_meta_types_tool(
    profile_id: str,
    domain_scope: str = "Global",
) -> str:
    """List MetaTypes accessible to the user in their domain.

    Rule 5.2: Only returns MetaTypes in the user's domain_scope or Global scope.

    Args:
        profile_id: ID of the requesting user (Rule 5.1).
        domain_scope: User's domain scope (Rule 5.2). Defaults to "Global".

    Returns:
        TOON JSON array of MetaType summaries accessible to this user.
    """
    types = list_meta_types(domain_scope=domain_scope)
    items = [
        {"id": mt.id, "name": mt.name, "tc": mt.type_category.value, "hs": mt.health_score, "ds": mt.domain_scope}
        for mt in types
    ]
    logger.info("Tool list_meta_types_tool: user %s in domain %s sees %d types", profile_id, domain_scope, len(items))
    return serialise({"count": len(items), "items": items})


@mcp.tool()
def patch_meta_type_tool(
    meta_type_id: str,
    schema_definition: Dict[str, Any],
    profile_id: str,
) -> str:
    """Patch the schema definition of an existing MetaType.

    Updates schema_definition, bumps version by 1, and resets health_score to 1.0.
    Rule 5.1: Change is attributed to profile_id.

    Args:
        meta_type_id: UUID of the MetaType to patch.
        schema_definition: New complete schema_definition dict.
        profile_id: ID of the user performing the patch (Rule 5.1).

    Returns:
        TOON JSON with the updated MetaType summary.
    """
    try:
        mt = patch_meta_type(meta_type_id, schema_definition, profile_id=profile_id)
        logger.info("Tool patch_meta_type_tool: %s v%s by %s", mt.id, mt.version, profile_id)
        return serialise({
            "id": mt.id,
            "name": mt.name,
            "version": mt.version,
            "fields": list(mt.schema_definition.keys()),
            "health_score": mt.health_score,
        })
    except ValueError as exc:
        return serialise({"error": "NOT_FOUND", "message": str(exc)})


@mcp.tool()
def insert_node(
    meta_type_id: str,
    properties: Dict[str, Any],
    profile_id: str,
    domain_scope: str = "Global",
) -> str:
    """Insert a new ObjectNode validated against the MetaType's dynamic schema.

    Validates properties against the MetaType's schema_definition. If validation
    fails, the MetaType's health_score is decremented (Circuit Breaker mechanism).
    If health_score is <= 0, raises a locked error.

    Rule 5.1: Insertion is attributed to profile_id.
    Rule 5.2: Node is stored in domain_scope.

    Args:
        meta_type_id: UUID of the MetaType defining the node's shape.
        properties: Key-value dict of node properties to insert.
        profile_id: ID of the inserting user/profile (Rule 5.1).
        domain_scope: Domain scope for the new node (Rule 5.2).

    Returns:
        TOON JSON with the new node id and meta_type_id.
    """
    try:
        result = insert_object_node(
            meta_type_id=meta_type_id,
            properties=properties,
            profile_id=profile_id,
            domain_scope=domain_scope,
        )
        logger.info("Tool insert_node: %s in %s by %s", result["id"], meta_type_id, profile_id)
        return serialise(result)
    except CircuitBreakerError as exc:
        return serialise({"error": "CIRCUIT_BREAKER_OPEN", "message": str(exc)})
    except LockedError as exc:
        return serialise({"error": "META_TYPE_LOCKED", "message": str(exc)})
    except PydanticValidationError as exc:
        return serialise({"error": "VALIDATION_ERROR", "message": str(exc)})
    except ValueError as exc:
        return serialise({"error": "NOT_FOUND", "message": str(exc)})


@mcp.tool()
def confirm_schema_heal(
    meta_type_id: str,
    profile_id: str,
) -> str:
    """Unlock the Circuit Breaker for a MetaType after a schema patch (FR-005 / SC-005).

    The breaker should only be unlocked after the MetaType schema has been evolved
    via patch_meta_type. This validates that the schema has indeed been updated
    (version > 1) before resetting the breaker.

    Args:
        meta_type_id: UUID of the MetaType whose circuit breaker should be unlocked.
        profile_id: ID of the user performing the heal action (Rule 5.1).

    Returns:
        TOON JSON with status SUCCESS or an error message.
    """
    mt = get_meta_type_by_id(meta_type_id)
    if mt is None:
        return serialise({"error": "NOT_FOUND", "message": f"MetaType not found: {meta_type_id}"})

    cb_status = get_circuit_breaker_status(meta_type_id)
    if not cb_status["is_open"]:
        return serialise({
            "status": "NO_ACTION",
            "message": "Circuit breaker is not open for this MetaType.",
            "consecutive_failures": cb_status["consecutive_failures"],
        })

    # Require the schema to have been patched (version > 1) before allowing heal
    if mt.version <= 1:
        return serialise({
            "error": "APPROVAL_REQUIRED",
            "message": "Schema must be evolved via patch_meta_type before healing the circuit breaker.",
        })

    reset_circuit_breaker(meta_type_id)
    logger.info("Tool confirm_schema_heal: CB reset for MetaType %s by %s", meta_type_id, profile_id)
    return serialise({
        "status": "SUCCESS",
        "meta_type_id": meta_type_id,
        "meta_type_name": mt.name,
        "new_version": mt.version,
        "health_score": 1.0,
        "message": "Circuit breaker unlocked. Schema validated.",
    })


@mcp.tool()
def delete_meta_type_tool(
    meta_type_id: str,
    profile_id: str,
    approval_token: str = "",
) -> str:
    """Request deletion of a MetaType (APPROVAL_REQUIRED guard – Rule 5.5 / FR-017).

    Deletion of MetaTypes is irreversible. An approval_token must be provided
    to confirm the action. Without a valid token, returns [APPROVAL_REQUIRED].

    Args:
        meta_type_id: UUID of the MetaType to delete.
        profile_id: ID of the requesting user (Rule 5.1).
        approval_token: Human-issued approval token. Must equal "APPROVED" to proceed.

    Returns:
        TOON JSON with status APPROVAL_REQUIRED or SUCCESS.
    """
    if approval_token != "APPROVED":
        logger.warning("Tool delete_meta_type_tool: APPROVAL_REQUIRED for %s by %s", meta_type_id, profile_id)
        return serialise({
            "status": "APPROVAL_REQUIRED",
            "action": "delete_meta_type",
            "meta_type_id": meta_type_id,
            "message": "[APPROVAL_REQUIRED] Deleting a MetaType is irreversible. "
                       "Pass approval_token='APPROVED' to confirm.",
        })

    from ...graph.ontology import delete_meta_type
    mt = get_meta_type_by_id(meta_type_id)
    if mt is None:
        return serialise({"error": "NOT_FOUND", "message": f"MetaType not found: {meta_type_id}"})

    delete_meta_type(meta_type_id)
    logger.warning("Tool delete_meta_type_tool: MetaType DELETED %s by %s", meta_type_id, profile_id)
    return serialise({"status": "SUCCESS", "meta_type_id": meta_type_id, "action": "deleted"})


@mcp.tool()
def delete_node_tool(
    node_id: str,
    profile_id: str,
    approval_token: str = "",
) -> str:
    """Request deletion of an ObjectNode (APPROVAL_REQUIRED guard – FR-017).

    Node deletion is irreversible and triggers cascading wither on attached edges.
    An approval_token must be provided to confirm the action.

    Args:
        node_id: UUID of the ObjectNode to delete.
        profile_id: ID of the requesting user (Rule 5.1).
        approval_token: Human-issued approval token. Must equal "APPROVED" to proceed.

    Returns:
        TOON JSON with status APPROVAL_REQUIRED or SUCCESS.
    """
    if approval_token != "APPROVED":
        logger.warning("Tool delete_node_tool: APPROVAL_REQUIRED for %s by %s", node_id, profile_id)
        return serialise({
            "status": "APPROVAL_REQUIRED",
            "action": "delete_node",
            "node_id": node_id,
            "message": "[APPROVAL_REQUIRED] Node deletion triggers cascading wither. "
                       "Pass approval_token='APPROVED' to confirm.",
        })

    from ...graph.nodes import get_node_by_id, delete_node
    from ...graph.edges import cascading_wither

    node = get_node_by_id(node_id)
    if node is None:
        return serialise({"error": "NOT_FOUND", "message": f"ObjectNode not found: {node_id}"})

    pruned = cascading_wither(node_id)
    delete_node(node_id)
    logger.warning("Tool delete_node_tool: ObjectNode DELETED %s by %s, %d edges pruned", node_id, profile_id, pruned)
    return serialise({
        "status": "SUCCESS",
        "node_id": node_id,
        "edges_pruned": pruned,
    })
