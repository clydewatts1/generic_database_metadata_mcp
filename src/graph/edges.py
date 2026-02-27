"""Graph operations for Stigmergic Edges (create, reinforce, decay, prune)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from src.graph.client import execute_query
from src.models.base import StigmergicEdge
from src.utils.logging import NotFoundError, get_logger

logger = get_logger(__name__)

# Decay constants (from data-model.md)
DECAY_THRESHOLD_HOURS = 24
DECAY_RATE_PER_DAY = 0.05
PRUNE_THRESHOLD = 0.1
REINFORCE_DELTA = 0.1


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _row_to_edge(row: list[Any]) -> StigmergicEdge:
    node = row[0]
    p = node.properties
    return StigmergicEdge(
        id=p["id"],
        source_id=p["source_id"],
        target_id=p["target_id"],
        edge_type=p["edge_type"],
        confidence_score=float(p["confidence_score"]),
        last_accessed=datetime.fromisoformat(p["last_accessed"]),
        rationale_summary=p.get("rationale_summary", ""),
        created_by_prompt_hash=p.get("created_by_prompt_hash", "SYSTEM_GENERATED"),
        domain_scope=p.get("domain_scope", "Global"),
    )


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------

def create_edge(
    source_id: str,
    target_id: str,
    edge_type: str,
    rationale_summary: str,
    created_by_prompt_hash: str = "SYSTEM_GENERATED",
    domain_scope: str = "Global",
) -> StigmergicEdge:
    """Create a Stigmergic Edge with initial confidence_score=0.5."""
    edge = StigmergicEdge(
        source_id=source_id,
        target_id=target_id,
        edge_type=edge_type,
        rationale_summary=rationale_summary,
        created_by_prompt_hash=created_by_prompt_hash,
        domain_scope=domain_scope,
    )

    execute_query(
        "CREATE (e:StigmergicEdge {"
        "  id: $id,"
        "  source_id: $source_id,"
        "  target_id: $target_id,"
        "  edge_type: $edge_type,"
        "  confidence_score: $confidence_score,"
        "  last_accessed: $last_accessed,"
        "  rationale_summary: $rationale_summary,"
        "  created_by_prompt_hash: $created_by_prompt_hash,"
        "  domain_scope: $domain_scope"
        "})",
        {
            "id": edge.id,
            "source_id": edge.source_id,
            "target_id": edge.target_id,
            "edge_type": edge.edge_type,
            "confidence_score": edge.confidence_score,
            "last_accessed": edge.last_accessed.isoformat(),
            "rationale_summary": edge.rationale_summary,
            "created_by_prompt_hash": edge.created_by_prompt_hash,
            "domain_scope": edge.domain_scope,
        },
    )
    logger.debug("StigmergicEdge created: %s (%s -> %s)", edge.id, source_id, target_id)
    return edge


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------

def get_edge_by_id(edge_id: str) -> StigmergicEdge | None:
    result = execute_query(
        "MATCH (e:StigmergicEdge {id: $id}) RETURN e",
        {"id": edge_id},
    )
    rows = result.result_set
    return _row_to_edge(rows[0]) if rows else None


def list_edges_from_source(source_id: str) -> list[StigmergicEdge]:
    result = execute_query(
        "MATCH (e:StigmergicEdge {source_id: $source_id}) RETURN e",
        {"source_id": source_id},
    )
    return [_row_to_edge(row) for row in result.result_set]


# ---------------------------------------------------------------------------
# Reinforce
# ---------------------------------------------------------------------------

def reinforce_edge(edge_id: str) -> StigmergicEdge:
    """Increase confidence_score by REINFORCE_DELTA (max 1.0) and update last_accessed.

    Raises:
        NotFoundError: if the edge does not exist.
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    execute_query(
        "MATCH (e:StigmergicEdge {id: $id}) "
        "SET e.confidence_score = CASE "
        "  WHEN e.confidence_score + $delta > 1.0 THEN 1.0 "
        "  ELSE e.confidence_score + $delta END, "
        "e.last_accessed = $now",
        {"id": edge_id, "delta": REINFORCE_DELTA, "now": now_iso},
    )
    edge = get_edge_by_id(edge_id)
    if edge is None:
        raise NotFoundError("StigmergicEdge", edge_id)
    return edge


# ---------------------------------------------------------------------------
# Decay
# ---------------------------------------------------------------------------

def apply_decay(edge_id: str, hours_elapsed: float) -> StigmergicEdge | None:
    """Apply biological decay to a Stigmergic Edge.

    Prunes the edge (deletes it) if confidence_score falls below PRUNE_THRESHOLD.

    Returns the updated edge, or None if the edge was pruned.
    """
    days_elapsed = hours_elapsed / 24.0
    if days_elapsed < 1.0:
        return get_edge_by_id(edge_id)  # No decay within one day

    total_decay = DECAY_RATE_PER_DAY * days_elapsed
    execute_query(
        "MATCH (e:StigmergicEdge {id: $id}) "
        "SET e.confidence_score = CASE "
        "  WHEN e.confidence_score - $decay < 0 THEN 0 "
        "  ELSE e.confidence_score - $decay END",
        {"id": edge_id, "decay": total_decay},
    )

    edge = get_edge_by_id(edge_id)
    if edge is None:
        return None

    if edge.confidence_score < PRUNE_THRESHOLD:
        execute_query("MATCH (e:StigmergicEdge {id: $id}) DELETE e", {"id": edge_id})
        logger.info("StigmergicEdge pruned (confidence < %s): %s", PRUNE_THRESHOLD, edge_id)
        return None

    return edge


def cascading_wither(node_id: str) -> int:
    """Immediately prune all edges attached to a deprecated/deleted node.

    Returns the number of edges pruned.
    """
    result = execute_query(
        "MATCH (e:StigmergicEdge) "
        "WHERE e.source_id = $nid OR e.target_id = $nid "
        "DELETE e RETURN count(e) as pruned",
        {"nid": node_id},
    )
    pruned = result.result_set[0][0] if result.result_set else 0
    logger.info("Cascading wither for node %s: %s edges pruned", node_id, pruned)
    return pruned
