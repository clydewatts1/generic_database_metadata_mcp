"""MCP tool: register_meta_type – dynamically register a new Object or Edge type."""

from __future__ import annotations

from typing import Any

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
    schema_definition: dict[str, Any],
) -> str:
    """Register a new MetaType (Object Type or Edge Type) in the graph.

    Args:
        name: PascalCase type name, e.g. "Dashboard". Max 50 chars.
        type_category: "NODE" or "EDGE".
        schema_definition: JSON Schema dict defining fields and their types.
            Each key is a field name; value is {"type": "string|integer|float|boolean|array",
            "required": true|false}.

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
        mt = create_meta_type(data)
        logger.info("Tool register_meta_type: created %s", mt.name)
        return serialise({
            "id": mt.id,
            "name": mt.name,
            "type_category": mt.type_category.value,
            "fields": list(mt.schema_definition.keys()),
        })
    except ValueError as exc:
        return serialise({"error": "CONFLICT", "message": str(exc)})


@mcp.tool()
def list_meta_types_tool() -> str:
    """List all registered MetaTypes in the graph.

    Returns:
        TOON JSON array of MetaType summaries.
    """
    types = list_meta_types()
    items = [
        {"id": mt.id, "name": mt.name, "tc": mt.type_category.value, "hs": mt.health_score}
        for mt in types
    ]
    return serialise({"count": len(items), "items": items})

