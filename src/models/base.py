"""Base Pydantic models for MetaType, ObjectNode, StigmergicEdge, and FunctionObject."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _new_uuid() -> str:
    return str(uuid.uuid4())


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class TypeCategory(str, Enum):
    NODE = "NODE"
    EDGE = "EDGE"
class RelationshipClass(str, Enum):
    STRUCTURAL = "STRUCTURAL"
    FLOW = "FLOW"
    NONE = "NONE"

# ---------------------------------------------------------------------------
# MetaType
# ---------------------------------------------------------------------------

class MetaTypeCreate(BaseModel):
    """Input model for registering a new MetaType."""

    name: str = Field(..., min_length=1, max_length=50, pattern=r"^[A-Z][A-Za-z0-9]+$")
    type_category: TypeCategory
    schema_definition: dict[str, Any] = Field(
        ...,
        description="JSON Schema dict defining the fields, types, and required status.",
    )
    relationship_class: RelationshipClass = RelationshipClass.NONE
    created_by_prompt_hash: str = "SYSTEM_GENERATED"
    relationship_class: RelationshipClass = RelationshipClass.NONE
    created_by_prompt_hash: str = "SYSTEM_GENERATED"

    @field_validator("name")
    @classmethod
    def reject_reserved_names(cls, v: str) -> str:
        reserved = {"MetaType", "ObjectNode", "StigmergicEdge"}
        if v in reserved:
            raise ValueError(f"'{v}' is a reserved MetaType name.")
        return v


class MetaType(BaseModel):
    """Full MetaType as stored in the graph."""

    id: str = Field(default_factory=_new_uuid)
    name: str
    type_category: TypeCategory
    schema_definition: dict[str, Any]
    health_score: float = Field(default=1.0, ge=0.0, le=1.0)
    version: int = Field(default=1)
    relationship_class: RelationshipClass = RelationshipClass.NONE
    created_at: datetime = Field(default_factory=_now_utc)
    created_by_prompt_hash: str = "SYSTEM_GENERATED"
    rationale_summary: str = ""
    domain_scope: str = Field(default="Global")  # Rule 5.2: MetaTypes can be domain-scoped
    created_by_profile_id: str = Field(default="SYSTEM")  # Rule 5.1: Track originating user


# ---------------------------------------------------------------------------
# ObjectNode
# ---------------------------------------------------------------------------

class ObjectNodeCreate(BaseModel):
    """Input model for inserting a new Object Node."""

    meta_type_id: str
    domain_scope: str = "Global"
    profile_id: str = Field(default="SYSTEM")  # Rule 5.1: Track which user/profile created this
    properties: dict[str, Any] = Field(default_factory=dict)


class ObjectNode(BaseModel):
    """Full ObjectNode as stored in the graph."""

    id: str = Field(default_factory=_new_uuid)
    meta_type_id: str
    domain_scope: str = "Global"
    profile_id: str = Field(default="SYSTEM")  # Rule 5.1: Originating user/profile
    properties: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# StigmergicEdge
# ---------------------------------------------------------------------------

class StigmergicEdgeCreate(BaseModel):
    """Input model for creating a Stigmergic Edge."""

    source_id: str
    target_id: str
    edge_type: str
    rationale_summary: str = Field(..., max_length=200)
    created_by_prompt_hash: str = "SYSTEM_GENERATED"
    created_by_profile_id: str = Field(default="SYSTEM")  # Rule 5.3: Attribute edge to user
    domain_scope: str = "Global"


class StigmergicEdge(BaseModel):
    """Full StigmergicEdge as stored in the graph."""

    id: str = Field(default_factory=_new_uuid)
    source_id: str
    target_id: str
    edge_type: str
    confidence_score: float = Field(default=0.5, ge=0.0, le=1.0)
    last_accessed: datetime = Field(default_factory=_now_utc)
    rationale_summary: str = Field(default="", max_length=200)
    created_by_prompt_hash: str = "SYSTEM_GENERATED"
    created_by_profile_id: str = Field(default="SYSTEM")  # Rule 5.3: Originating user
    domain_scope: str = "Global"


# ---------------------------------------------------------------------------
# FunctionObject
# ---------------------------------------------------------------------------

class FunctionObjectCreate(BaseModel):
    """Input model for creating a Function Object."""

    name: str = Field(..., min_length=1, max_length=100, pattern=r"^[A-Z][A-Za-z0-9_]*$")
    logic_description: str = Field(..., min_length=1, max_length=500)
    input_schema: dict[str, Any] = Field(
        ..., description="JSON Schema for expected input structure"
    )
    output_schema: dict[str, Any] = Field(
        ..., description="JSON Schema for expected output structure"
    )
    profile_id: str = Field(default="SYSTEM")
    created_by_prompt_hash: str = "SYSTEM_GENERATED"  # Rule 5.1: Creator's profile

    @field_validator("name")
    @classmethod
    def reject_reserved_names(cls, v: str) -> str:
        reserved = {"FunctionObject", "MetaType", "ObjectNode", "StigmergicEdge"}
        if v in reserved:
            raise ValueError(f"'{v}' is a reserved FunctionObject name.")
        return v

    @field_validator("input_schema", "output_schema")
    @classmethod
    def validate_json_schema(cls, v: dict[str, Any]) -> dict[str, Any]:
        """Validate that input/output schemas are valid JSON Schema objects."""
        if not isinstance(v, dict):
            raise ValueError("Schema must be a JSON object (dict).")
        # Basic JSON Schema validation: should have 'type' or '$ref' or 'properties'
        if not any(k in v for k in ["type", "$ref", "properties", "items", "oneOf", "anyOf"]):
            raise ValueError(
                "Schema must be valid JSON Schema (e.g., include 'type', '$ref', 'properties', etc.)"
            )
        return v


class FunctionObject(BaseModel):
    """Full FunctionObject as stored in the graph."""

    id: str = Field(default_factory=_new_uuid)
    name: str = Field(min_length=1, max_length=100, pattern=r"^[A-Z][A-Za-z0-9_]*$")
    logic_description: str = Field(min_length=1, max_length=500)
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    created_by_profile_id: str = Field(default="SYSTEM")  # Rule 5.1: Track originating user
    domain_scope: str = Field(default="Global")  # Rule 5.2: Domain this function applies to
    created_at: datetime = Field(default_factory=_now_utc)  # Creation timestamp
    created_by_prompt_hash: str = "SYSTEM_GENERATED"
    version: int = Field(default=1)  # Schema version for compatibility tracking
