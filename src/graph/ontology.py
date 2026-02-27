"""Graph operations for MetaType nodes (CRUD and health management)."""

from __future__ import annotations

import json
from typing import Any

from src.graph.client import execute_query
from src.models.base import MetaType, MetaTypeCreate, TypeCategory
from src.utils.logging import get_logger

logger = get_logger(__name__)

# FalkorDB stores all property values as strings when using params –
# schema_definition (a dict) must be serialised to JSON for storage.


def _row_to_meta_type(row: list[Any]) -> MetaType:
    """Convert a raw FalkorDB result row -> MetaType."""
    node = row[0]  # node object from FalkorDB result
    props = node.properties
    return MetaType(
        id=props["id"],
        name=props["name"],
        type_category=TypeCategory(props["type_category"]),
        schema_definition=json.loads(props["schema_definition"]),
        health_score=float(props["health_score"]),
        version=int(props["version"]),
    )


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------

def create_meta_type(data: MetaTypeCreate) -> MetaType:
    """Persist a new MetaType node and return the full MetaType.

    Raises ValueError if a MetaType with the same name already exists.
    """
    existing = get_meta_type_by_name(data.name)
    if existing is not None:
        raise ValueError(f"MetaType '{data.name}' already exists (id={existing.id}).")

    mt = MetaType(
        name=data.name,
        type_category=data.type_category,
        schema_definition=data.schema_definition,
    )

    query = (
        "CREATE (m:MetaType {"
        "  id: $id,"
        "  name: $name,"
        "  type_category: $type_category,"
        "  schema_definition: $schema_definition,"
        "  health_score: $health_score,"
        "  version: $version"
        "}) RETURN m"
    )
    params = {
        "id": mt.id,
        "name": mt.name,
        "type_category": mt.type_category.value,
        "schema_definition": json.dumps(mt.schema_definition),
        "health_score": mt.health_score,
        "version": mt.version,
    }
    execute_query(query, params)
    logger.info("MetaType created: %s (%s)", mt.name, mt.id)
    return mt


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------

def get_meta_type_by_name(name: str) -> MetaType | None:
    """Return the MetaType with *name* or None if not found."""
    result = execute_query(
        "MATCH (m:MetaType {name: $name}) RETURN m",
        {"name": name},
    )
    rows = result.result_set
    if not rows:
        return None
    return _row_to_meta_type(rows[0])


def get_meta_type_by_id(meta_type_id: str) -> MetaType | None:
    """Return the MetaType with *meta_type_id* or None if not found."""
    result = execute_query(
        "MATCH (m:MetaType {id: $id}) RETURN m",
        {"id": meta_type_id},
    )
    rows = result.result_set
    if not rows:
        return None
    return _row_to_meta_type(rows[0])


def list_meta_types() -> list[MetaType]:
    """Return all MetaType nodes in the graph."""
    result = execute_query("MATCH (m:MetaType) RETURN m")
    return [_row_to_meta_type(row) for row in result.result_set]


# ---------------------------------------------------------------------------
# Update health / version
# ---------------------------------------------------------------------------

def decrement_health_score(meta_type_id: str, delta: float = 0.1) -> None:
    """Decrease health_score by *delta*, floored at 0.0."""
    execute_query(
        "MATCH (m:MetaType {id: $id}) "
        "SET m.health_score = CASE WHEN m.health_score - $delta < 0 THEN 0 "
        "                          ELSE m.health_score - $delta END",
        {"id": meta_type_id, "delta": delta},
    )
    logger.debug("health_score decremented for MetaType %s", meta_type_id)


def reset_health_score(meta_type_id: str) -> None:
    """Reset health_score to 1.0 after healing / schema patch."""
    execute_query(
        "MATCH (m:MetaType {id: $id}) SET m.health_score = 1.0",
        {"id": meta_type_id},
    )
    logger.info("MetaType health_score reset: %s", meta_type_id)
