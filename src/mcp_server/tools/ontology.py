"""MCP tool: register_meta_type – dynamically register a new Object or Edge type."""

from typing import Any, Dict

from pydantic import ValidationError as PydanticValidationError

from ..app import mcp
from ...models.base import MetaTypeCreate, TypeCategory
from ...models.serialization import serialise
from ...graph.ontology import create_meta_type, list_meta_types
from ...utils.logging import get_logger

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

