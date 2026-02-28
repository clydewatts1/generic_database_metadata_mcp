"""Graph operations for MetaType nodes (CRUD and health management)."""

import json
from typing import Any

from .client import execute_query
from ..models.base import MetaType, MetaTypeCreate, TypeCategory
from ..utils.logging import get_logger, LockedError, CircuitBreakerError

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Circuit Breaker: session-level failure counters (FR-005)
# ---------------------------------------------------------------------------

# Maps meta_type_id → consecutive validation failure count for this process.
_CB_FAILURES: dict[str, int] = {}
_CB_THRESHOLD = 3  # lock after this many consecutive failures (FR-005 / SC-005)


def _row_to_meta_type(row: list[Any]) -> MetaType:
    """Convert a raw FalkorDB result row -> MetaType."""
    node = row[0]  # node object from FalkorDB result
    props = node.properties
    return MetaType(
        id=props["id"],
        name=props["name"],
        type_category=TypeCategory(props["type_category"]),
        schema_definition=json.loads(props["schema_definition"]),
        relationship_class=props.get("relationship_class", "NONE"),
        created_by_prompt_hash=props.get("created_by_prompt_hash", "SYSTEM_GENERATED"),
        rationale_summary=props.get("rationale_summary", ""),
        health_score=float(props["health_score"]),
        version=int(props["version"]),
        domain_scope=props.get("domain_scope", "Global"),  # Rule 5.2
        created_by_profile_id=props.get("created_by_profile_id", "SYSTEM"),  # Rule 5.1
    )


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------

def create_meta_type(
    data: MetaTypeCreate,
    profile_id: str = "SYSTEM",
    domain_scope: str = "Global",
) -> MetaType:
    existing = get_meta_type_by_name(data.name)
    if existing is not None:
        raise ValueError(f"MetaType '{data.name}' already exists (id={existing.id}).")
    from datetime import datetime, timezone
    mt = MetaType(
        name=data.name,
        type_category=data.type_category,
        schema_definition=data.schema_definition,
        domain_scope=domain_scope,
        created_by_profile_id=profile_id,
        relationship_class=data.relationship_class,
        created_by_prompt_hash=data.created_by_prompt_hash,
    )

    query = (
        "CREATE (m:MetaType {"
        "  id: $id,"
        "  name: $name,"
        "  type_category: $type_category,"
        "  schema_definition: $schema_definition,"
        "  health_score: $health_score,"
        "  version: $version,"
        "  domain_scope: $domain_scope,"
        "  created_by_profile_id: $created_by_profile_id,"
        "  relationship_class: $relationship_class,"
        "  created_at: $created_at,"
        "  created_by_prompt_hash: $created_by_prompt_hash,"
        "  rationale_summary: $rationale_summary"
        "}) RETURN m"
    )
    params = {
        "id": mt.id,
        "name": mt.name,
        "type_category": mt.type_category.value,
        "schema_definition": json.dumps(mt.schema_definition),
        "health_score": mt.health_score,
        "version": mt.version,
        "domain_scope": domain_scope,
        "created_by_profile_id": profile_id,
        "relationship_class": mt.relationship_class.value,
        "created_at": mt.created_at.isoformat(),
        "created_by_prompt_hash": mt.created_by_prompt_hash,
        "rationale_summary": mt.rationale_summary,
    }
    execute_query(query, params)
    logger.info("MetaType created: %s (%s) by %s in domain %s", mt.name, mt.id, profile_id, domain_scope)
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


def list_meta_types(domain_scope: str = "Global") -> list[MetaType]:
    """Return MetaType nodes visible to *domain_scope* (includes Global).

    Rule 5.2: Only returns MetaTypes in the user's domain_scope or Global scope.
    """
    result = execute_query(
        "MATCH (m:MetaType) WHERE m.domain_scope IN [$domain_scope, 'Global'] RETURN m",
        {"domain_scope": domain_scope},
    )
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


# ---------------------------------------------------------------------------
# Patch (schema update)
# ---------------------------------------------------------------------------

def patch_meta_type(
    meta_type_id: str,
    schema_definition: dict,
    profile_id: str = "SYSTEM",
) -> MetaType:
    """Update the schema_definition of an existing MetaType and bump version.

    Rule 5.1: Patch is attributed to *profile_id*.
    After a successful patch health_score is reset to 1.0.
    """
    mt = get_meta_type_by_id(meta_type_id)
    if mt is None:
        raise ValueError(f"MetaType not found: {meta_type_id}")

    new_version = mt.version + 1
    execute_query(
        "MATCH (m:MetaType {id: $id}) "
        "SET m.schema_definition = $schema_definition, "
        "    m.version = $version, "
        "    m.health_score = 1.0, "
        "    m.created_by_profile_id = $profile_id",
        {
            "id": meta_type_id,
            "schema_definition": json.dumps(schema_definition),
            "version": new_version,
            "profile_id": profile_id,
        },
    )
    logger.info("MetaType patched: %s v%s by %s", meta_type_id, new_version, profile_id)
    # Return updated object
    updated = get_meta_type_by_id(meta_type_id)
    assert updated is not None
    return updated


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------

def delete_meta_type(meta_type_id: str) -> None:
    """Remove a MetaType node entirely.

    Rule 5.5: This is an irreversible operation – callers must obtain approval.
    """
    execute_query(
        "MATCH (m:MetaType {id: $id}) DETACH DELETE m",
        {"id": meta_type_id},
    )
    logger.warning("MetaType DELETED: %s", meta_type_id)


# ---------------------------------------------------------------------------
# Insert ObjectNode
# ---------------------------------------------------------------------------

def insert_object_node(
    meta_type_id: str,
    properties: dict,
    profile_id: str = "SYSTEM",
    domain_scope: str = "Global",
) -> dict:
    """Insert a new ObjectNode validated against the MetaType's schema.

    FR-004: Decrements health_score on validation failure.
    FR-005: Locks (Circuit Breaker) after 3 consecutive failures.
    Returns {"id": node_id} on success.
    """
    from ..graph.schema import validate_node_data
    from pydantic import ValidationError as PydanticValidationError

    mt = get_meta_type_by_id(meta_type_id)
    if mt is None:
        raise ValueError(f"MetaType not found: {meta_type_id}")

    if mt.health_score <= 0.0:
        raise LockedError(mt.name)

    # Check circuit breaker before attempting
    failures = _CB_FAILURES.get(meta_type_id, 0)
    if failures >= _CB_THRESHOLD:
        raise CircuitBreakerError(mt.name)

    try:
        validated = validate_node_data(mt, properties)
    except PydanticValidationError:
        # Increment failure counter
        _CB_FAILURES[meta_type_id] = failures + 1
        decrement_health_score(meta_type_id)
        logger.warning(
            "Validation failure #%d for MetaType %s (id=%s)",
            _CB_FAILURES[meta_type_id],
            mt.name,
            meta_type_id,
        )
        if _CB_FAILURES[meta_type_id] >= _CB_THRESHOLD:
            logger.error(
                "Circuit Breaker OPEN for MetaType %s after %d failures",
                mt.name,
                _CB_THRESHOLD,
            )
        raise

    # Success – reset failure counter
    _CB_FAILURES.pop(meta_type_id, None)

    import uuid
    node_id = str(uuid.uuid4())
    execute_query(
        "CREATE (n:ObjectNode {"
        "  id: $id,"
        "  meta_type_id: $meta_type_id,"
        "  domain_scope: $domain_scope,"
        "  profile_id: $profile_id,"
        "  properties: $properties"
        "})",
        {
            "id": node_id,
            "meta_type_id": meta_type_id,
            "domain_scope": domain_scope,
            "profile_id": profile_id,
            "properties": json.dumps(validated),
        },
    )
    logger.info("ObjectNode inserted: %s for MetaType %s by %s", node_id, meta_type_id, profile_id)
    return {"id": node_id, "meta_type_id": meta_type_id}


# ---------------------------------------------------------------------------
# Circuit Breaker helpers
# ---------------------------------------------------------------------------

def get_circuit_breaker_status(meta_type_id: str) -> dict:
    """Return circuit breaker state for a MetaType."""
    failures = _CB_FAILURES.get(meta_type_id, 0)
    return {
        "meta_type_id": meta_type_id,
        "consecutive_failures": failures,
        "threshold": _CB_THRESHOLD,
        "is_open": failures >= _CB_THRESHOLD,
    }


def reset_circuit_breaker(meta_type_id: str) -> None:
    """Reset the circuit breaker for a MetaType (called by confirm_schema_heal)."""
    _CB_FAILURES.pop(meta_type_id, None)
    reset_health_score(meta_type_id)
    logger.info("Circuit Breaker reset for MetaType %s", meta_type_id)
