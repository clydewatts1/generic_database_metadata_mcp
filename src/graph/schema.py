import json
from datetime import datetime, timezone
from typing import Any

from pydantic import create_model, BaseModel, ConfigDict
from src.models.base import MetaType
from src.utils.logging import get_logger

logger = get_logger(__name__)

# Basic type mapping from string representation to actual Python types
TYPE_MAP = {
    "string": str,
    "integer": int,
    "float": float,
    "boolean": bool,
    "dict": dict,
    "list": list,
    "str": str,
    "int": int,
    "bool": bool
}

def generate_pydantic_model(meta_type: MetaType) -> type[BaseModel]:
    """
    Generate a dynamic Pydantic model based on a MetaType's schema definition.
    """
    fields: dict[str, tuple[type, Any]] = {}
    
    for field_name, field_type_str in meta_type.schema_definition.items():
        # Handle simple type mapping
        if isinstance(field_type_str, str):
            mapped_type = TYPE_MAP.get(field_type_str.lower(), str)
            # Default everything to required. In a real system you might want optionals.
            fields[field_name] = (mapped_type, ...)
        elif isinstance(field_type_str, dict):
            # Advanced cases like {"type": "string", "required": false} could go here
            raw_type = field_type_str.get("type", "string")
            mapped_type = TYPE_MAP.get(raw_type.lower(), str)
            if field_type_str.get("required", True):
                fields[field_name] = (mapped_type, ...)
            else:
                fields[field_name] = (mapped_type, None)
        else:
            fields[field_name] = (str, ...)

    # Ensure dynamic schema gets ConfigDict if needed
    model_name = f"Dynamic{meta_type.name.capitalize()}Model"
    return create_model(model_name, **fields, __config__=ConfigDict(extra="ignore"))

def validate_node_data(meta_type: MetaType, data: dict[str, Any]) -> dict[str, Any]:
    """
    Validates dictionary data against the MetaType's dynamic pydantic model.
    T014 validation implementation.
    Returns validated and coerced data, raises ValidationError if invalid.
    """
    logger.debug("Validating node data via schema", meta_type=meta_type.name)
    DynamicModel = generate_pydantic_model(meta_type)
    validated = DynamicModel(**data)
    # Return as primitive dictionary with coerced types
    return validated.model_dump()
