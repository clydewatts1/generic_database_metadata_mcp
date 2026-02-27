"""MCP tools: insert_node and bulk_ingest_seed – context-frugal node ingestion."""

from __future__ import annotations

from typing import Any

from ..app import mcp
from ...models.base import ObjectNodeCreate
from ...models.serialization import serialise
from ...graph.ontology import get_meta_type_by_id, get_meta_type_by_name, decrement_health_score
from ...graph.nodes import create_node, bulk_ingest
from ...utils.logging import ValidationError, CircuitBreakerError, NotFoundError, get_logger

logger = get_logger(__name__)

# In-memory session circuit-breaker state: meta_type_id -> consecutive failure count
_failure_counts: dict[str, int] = {}
_CIRCUIT_BREAKER_THRESHOLD = 3


def _check_circuit_breaker(meta_type_id: str, name: str) -> None:
    if _failure_counts.get(meta_type_id, 0) >= _CIRCUIT_BREAKER_THRESHOLD:
        raise CircuitBreakerError(name)


def _record_failure(meta_type_id: str) -> None:
    _failure_counts[meta_type_id] = _failure_counts.get(meta_type_id, 0) + 1


def _reset_failure_count(meta_type_id: str) -> None:
    _failure_counts.pop(meta_type_id, None)


@mcp.tool()
def insert_node(
    meta_type_name: str,
    properties: dict[str, Any],
    domain_scope: str = "Global",
) -> str:
    """Insert a single Object Node of the given MetaType.

    Validates properties against the registered schema before insertion.
    Tracks consecutive validation failures and fires circuit breaker after 3.

    Args:
        meta_type_name: Name of the registered MetaType (e.g. "Dashboard").
        properties: Dict of field values to store on the node.
        domain_scope: Domain this node belongs to. Defaults to "Global".

    Returns:
        TOON JSON with {"id": "<uuid>"} on success, or {"error": ...} on failure.
    """
    mt = get_meta_type_by_name(meta_type_name)
    if mt is None:
        return serialise({"error": "NOT_FOUND", "message": f"MetaType '{meta_type_name}' not found."})

    try:
        _check_circuit_breaker(mt.id, mt.name)
        data = ObjectNodeCreate(
            meta_type_id=mt.id,
            domain_scope=domain_scope,
            properties=properties,
        )
        node = create_node(mt, data)
        _reset_failure_count(mt.id)
        return serialise({"id": node.id})
    except CircuitBreakerError as exc:
        return serialise(exc.to_dict())
    except ValidationError as exc:
        _record_failure(mt.id)
        decrement_health_score(mt.id)
        logger.warning("Validation failure for %s: %s", meta_type_name, exc.message)
        return serialise(exc.to_dict())


@mcp.tool()
def bulk_ingest_seed(
    meta_type_name: str,
    records: list[dict[str, Any]],
    domain_scope: str = "Global",
) -> str:
    """Bulk-ingest initial seed data for a MetaType without overwhelming AI context.

    Inserts all records and returns ONLY a compact summary (never full node data).
    Intended for cold-start loading of large metadata dumps (e.g. Teradata schemas).

    Args:
        meta_type_name: Name of the registered MetaType.
        records: List of property dicts to insert as ObjectNodes.
        domain_scope: Domain scope for all inserted nodes.

    Returns:
        TOON JSON summary: {"meta_type": ..., "inserted": N, "failed": M}.
        Response is capped at 10 KB regardless of input size.
    """
    mt = get_meta_type_by_name(meta_type_name)
    if mt is None:
        return serialise({"error": "NOT_FOUND", "message": f"MetaType '{meta_type_name}' not found."})

    summary = bulk_ingest(mt, records, domain_scope=domain_scope)
    logger.info("bulk_ingest_seed: %s", summary)
    return serialise(summary)
