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


# ---------------------------------------------------------------------------
# ObjectNode
# ---------------------------------------------------------------------------

class ObjectNodeCreate(BaseModel):
    """Input model for inserting a new Object Node."""

    meta_type_id: str
    domain_scope: str = "Global"
    properties: dict[str, Any] = Field(default_factory=dict)


class ObjectNode(BaseModel):
    """Full ObjectNode as stored in the graph."""

    id: str = Field(default_factory=_new_uuid)
    meta_type_id: str
    domain_scope: str = "Global"
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
    domain_scope: str = "Global"


# ---------------------------------------------------------------------------
# FunctionObject
# ---------------------------------------------------------------------------

class FunctionObjectCreate(BaseModel):
    """Input model for creating a Function Object."""

    name: str
    logic_description: str
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)


class FunctionObject(BaseModel):
    """Full FunctionObject as stored in the graph."""

    id: str = Field(default_factory=_new_uuid)
    name: str
    logic_description: str
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
