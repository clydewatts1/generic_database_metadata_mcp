"""Dynamic Pydantic model factory – generates runtime validation models from MetaType nodes.

Uses pydantic.create_model so the AI can define new types without code changes.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, create_model

from src.models.base import MetaType
from src.utils.logging import get_logger

logger = get_logger(__name__)

# Module-level cache: MetaType.id -> generated pydantic Model class
_model_cache: dict[str, type[BaseModel]] = {}

# Map from JSON-Schema "type" string to Python type
_TYPE_MAP: dict[str, Any] = {
    "string": str,
    "integer": int,
    "float": float,
    "number": float,
    "boolean": bool,
    "array": list[str],
}


def _schema_to_field(field_spec: dict[str, Any]) -> tuple[Any, Any]:
    """Convert a schema_definition field spec to a (python_type, default) tuple.

    Returns:
        (annotation, default)  where default is ... (required) or None (optional).
    """
    type_str = field_spec.get("type", "string")
    py_type = _TYPE_MAP.get(type_str, str)

    required = field_spec.get("required", False)
    if required:
        return (py_type, ...)  # Pydantic required field
    return (Optional[py_type], None)  # optional with None default


def get_or_create_dynamic_model(meta_type: MetaType) -> type[BaseModel]:
    """Return (or lazily generate and cache) the Pydantic model for *meta_type*.

    The generated model:
    - Validates incoming properties against the MetaType schema.
    - Strips unknown extra fields silently.
    - Is cached by MetaType.id to avoid regeneration overhead.
    """
    if meta_type.id in _model_cache:
        return _model_cache[meta_type.id]

    field_definitions: dict[str, Any] = {}
    for field_name, field_spec in meta_type.schema_definition.items():
        field_definitions[field_name] = _schema_to_field(field_spec)

    model = create_model(
        meta_type.name,
        __config__=ConfigDict(extra="ignore"),
        **field_definitions,  # type: ignore[arg-type]
    )

    _model_cache[meta_type.id] = model
    logger.debug("Dynamic model created for MetaType '%s'", meta_type.name)
    return model


def invalidate_cache(meta_type_id: str) -> None:
    """Remove a cached model – call after a MetaType schema is patched."""
    _model_cache.pop(meta_type_id, None)


def validate_properties(meta_type: MetaType, properties: dict[str, Any]) -> dict[str, Any]:
    """Validate *properties* against the dynamic model for *meta_type*.

    Returns the validated (and extra-stripped) properties dict.

    Raises:
        pydantic.ValidationError: if the properties do not match the schema.
    """
    Model = get_or_create_dynamic_model(meta_type)
    instance = Model(**properties)
    return instance.model_dump(exclude_none=True)
