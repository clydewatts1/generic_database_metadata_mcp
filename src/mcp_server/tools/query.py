"""MCP tool: query_graph — bounded retrieval with optional traversal (US4 – T023).

Reinforces every edge traversed so that well-used paths accumulate confidence,
embodying the stigmergic «use it or lose it» principle.
"""
from typing import Any, Dict

from ..app import mcp
from ...graph.query import query_graph as _query_graph
from ...utils.logging import get_logger

logger = get_logger(__name__)


@mcp.tool()
def query_graph(
    meta_type_name: str | None = None,
    domain_scope: str | None = None,
    seed_node_id: str | None = None,
    hops: int = 1,
    page: int = 0,
    page_size: int = 5,
) -> Dict:
    """Retrieve ObjectNode records with optional bounded graph traversal.

    Filters nodes by *meta_type_name* and/or *domain_scope* (which always
    includes nodes with domain_scope="Global").  When *seed_node_id* is
    supplied the query walks 1–2 hops from that node instead of performing
    a flat scan.

    Results are returned as a TOON-compact paginated envelope.

    Args:
        meta_type_name: Restrict to nodes of this MetaType.
        domain_scope: Include nodes in this scope plus Global nodes.
        seed_node_id: Start traversal from this node ID.
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
    )

    logger.info(
        "query_graph",
        extra={
            "meta_type_name": meta_type_name,
            "domain_scope": domain_scope,
            "seed_node_id": seed_node_id,
            "total": result["total"],
            "page": page,
        },
    )
    return result
