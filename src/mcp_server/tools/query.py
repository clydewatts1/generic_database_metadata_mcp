"""MCP tool: query_graph — bounded retrieval with optional traversal (US4 – T023).

Reinforces every edge traversed so that well-used paths accumulate confidence,
embodying the stigmergic «use it or lose it» principle.
"""
from typing import Any, Dict, Optional

from ..app import mcp
from ...graph.query import query_graph as _query_graph
from ...models.serialization import serialise
from ...utils.logging import get_logger

logger = get_logger(__name__)


@mcp.tool()
def query_graph(
    profile_id: str,
    domain_scope: str,
    meta_type_name: Optional[str] = None,
    seed_node_id: Optional[str] = None,
    hops: int = 1,
    page: int = 0,
    page_size: int = 5,
) -> Dict:
    """Retrieve ObjectNode records with optional bounded graph traversal.

    Filters nodes by *meta_type_name* and *domain_scope* (which always
    includes nodes with domain_scope="Global").  When *seed_node_id* is
    supplied the query walks 1–2 hops from that node instead of performing
    a flat scan.

    Results are returned as a TOON-compact paginated envelope.
    Rule 5.2: Only returns nodes accessible to the user's domain_scope.

    Args:
        profile_id: ID of the requesting user (Rule 5.1).
        domain_scope: User's domain (Rule 5.2). Required to enforce scoping.
        meta_type_name: Restrict to nodes of this MetaType (optional).
        seed_node_id: Start traversal from this node ID (optional).
        hops: Traversal depth 1 or 2 (default 1).
        page: Zero-based page index (default 0).
        page_size: Items per page (default 5, max 20).

    Returns:
        {"items": [...], "total": N, "page": P, "page_size": S, "has_more": bool}
    """
    page_size = max(1, min(page_size, 20))

    result = _query_graph(
        meta_type_name=meta_type_name,
        domain_scope=domain_scope,
        seed_node_id=seed_node_id,
        hops=hops,
        page=page,
        page_size=page_size,
        profile_id=profile_id,  # T029: Profile context injected for audit
    )

    logger.info(
        "query_graph",
        extra={
            "profile_id": profile_id,
            "domain_scope": domain_scope,
            "meta_type_name": meta_type_name,
            "seed_node_id": seed_node_id,
            "total": result["total"],
            "page": page,
        },
    )
    return serialise(result)
