"""MCP tool: create_stigmergic_edge – create and reinforce confidence-weighted links."""

from __future__ import annotations

from ..app import mcp
from ...models.serialization import serialise
from ...graph.nodes import get_node_by_id
from ...graph.edges import create_edge, get_edge_by_id, reinforce_edge
from ...utils.logging import get_logger

logger = get_logger(__name__)


@mcp.tool()
def create_stigmergic_edge(
    source_id: str,
    target_id: str,
    edge_type: str,
    rationale_summary: str,
    created_by_prompt_hash: str = "SYSTEM_GENERATED",
    domain_scope: str = "Global",
) -> str:
    """Create a stigmergic (confidence-weighted) link between two Object Nodes.

    The edge is initialised with confidence_score=0.5. Confidence increases with
    each traversal (use reinforce_stigmergic_edge) and decays if unused.

    Args:
        source_id: UUID of the source ObjectNode.
        target_id: UUID of the target ObjectNode.
        edge_type: Relationship type label (e.g. "RELATES_TO", "POPULATES").
        rationale_summary: Human-readable explanation of the link (max 200 chars).
        created_by_prompt_hash: Hash of the originating prompt. Defaults to "SYSTEM_GENERATED".
        domain_scope: Domain this edge belongs to.

    Returns:
        TOON JSON {"id": "<uuid>", "cs": 0.5} on success, or {"error": ...} on failure.
    """
    if get_node_by_id(source_id) is None:
        return serialise({"error": "NOT_FOUND", "message": f"Source node {source_id} not found."})
    if get_node_by_id(target_id) is None:
        return serialise({"error": "NOT_FOUND", "message": f"Target node {target_id} not found."})

    edge = create_edge(
        source_id=source_id,
        target_id=target_id,
        edge_type=edge_type,
        rationale_summary=rationale_summary,
        created_by_prompt_hash=created_by_prompt_hash,
        domain_scope=domain_scope,
    )
    return serialise({"id": edge.id, "confidence_score": edge.confidence_score})


@mcp.tool()
def reinforce_stigmergic_edge(edge_id: str) -> str:
    """Reinforce a Stigmergic Edge after a successful traversal.

    Increases confidence_score by 0.1 (capped at 1.0) and updates last_accessed.

    Args:
        edge_id: UUID of the StigmergicEdge to reinforce.

    Returns:
        TOON JSON {"id": ..., "cs": <new_confidence>} on success.
    """
    edge = get_edge_by_id(edge_id)
    if edge is None:
        return serialise({"error": "NOT_FOUND", "message": f"Edge {edge_id} not found."})

    updated = reinforce_edge(edge_id)
    return serialise({"id": updated.id, "confidence_score": updated.confidence_score})
