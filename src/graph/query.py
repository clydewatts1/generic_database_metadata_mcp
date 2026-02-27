"""Bounded graph traversal for the metadata graph (US4 – T022).

`query_graph` supports:
- Filtering by MetaType name
- Filtering by domain_scope (includes "Global" results for any scope)
- Pagination (page / page_size)
- Optional 1-hop or 2-hop traversal from a seed node ID

All results are returned as compact TOON-serialised dicts.
"""

from typing import Any

from .client import get_graph
from ..models.serialization import serialise
from ..utils.logging import get_logger

logger = get_logger(__name__)

_DEFAULT_PAGE_SIZE = 5
_MAX_HOPS = 2


def query_graph(
    *,
    meta_type_name: str | None = None,
    domain_scope: str | None = None,
    seed_node_id: str | None = None,
    hops: int = 1,
    page: int = 0,
    page_size: int = _DEFAULT_PAGE_SIZE,
) -> dict[str, Any]:
    """Query ObjectNode nodes with optional traversal and filters.

    Parameters
    ----------
    meta_type_name:
        Restrict results to nodes whose ``meta_type_name`` matches.
    domain_scope:
        If given, return nodes whose ``domain_scope`` equals *domain_scope*
        **or** "Global".  If omitted, no domain filter is applied.
    seed_node_id:
        If given, start a bounded traversal (1 or 2 hops) from this node and
        return neighbours instead of a flat scan.
    hops:
        Number of hops for traversal (1 or 2).  Clamped to [1, MAX_HOPS].
    page:
        Zero-based page index.
    page_size:
        Items per page (default 5).

    Returns
    -------
    dict with keys: ``items``, ``total``, ``page``, ``page_size``, ``has_more``
    """
    hops = max(1, min(hops, _MAX_HOPS))
    skip = page * page_size

    graph = get_graph()

    if seed_node_id:
        items, total = _traversal_query(graph, seed_node_id, hops, meta_type_name, domain_scope)
    else:
        items, total = _flat_query(graph, meta_type_name, domain_scope)

    paged_items = items[skip: skip + page_size]
    serialised = [serialise(i) for i in paged_items]

    return {
        "items": serialised,
        "total": total,
        "page": page,
        "page_size": page_size,
        "has_more": (skip + page_size) < total,
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_where_clause(
    meta_type_name: str | None,
    domain_scope: str | None,
    alias: str = "n",
) -> tuple[str, dict[str, Any]]:
    """Return (WHERE fragment, params) for common node filters."""
    conditions: list[str] = []
    params: dict[str, Any] = {}

    if meta_type_name:
        conditions.append(f"{alias}.meta_type_name = $mtn")
        params["mtn"] = meta_type_name

    if domain_scope:
        conditions.append(f"({alias}.domain_scope = $ds OR {alias}.domain_scope = 'Global')")
        params["ds"] = domain_scope

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    return where, params


def _flat_query(
    graph: Any,
    meta_type_name: str | None,
    domain_scope: str | None,
) -> tuple[list[dict[str, Any]], int]:
    """Return all matching ObjectNode dicts (unsorted, no pagination at DB level)."""
    where, params = _build_where_clause(meta_type_name, domain_scope, alias="n")
    cypher = f"MATCH (n:ObjectNode) {where} RETURN n"

    result = graph.query(cypher, params)
    rows = result.result_set

    items = [_node_to_dict(row[0]) for row in rows]
    return items, len(items)


def _traversal_query(
    graph: Any,
    seed_node_id: str,
    hops: int,
    meta_type_name: str | None,
    domain_scope: str | None,
) -> tuple[list[dict[str, Any]], int]:
    """Return neighbours of seed_node up to *hops* edges away."""
    where, params = _build_where_clause(meta_type_name, domain_scope, alias="n")
    params["seed"] = seed_node_id
    cypher = (
        f"MATCH (seed:ObjectNode {{id: $seed}})-[*1..{hops}]-(n:ObjectNode) "
        f"{where} "
        "RETURN DISTINCT n"
    )
    result = graph.query(cypher, params)
    rows = result.result_set
    items = [_node_to_dict(row[0]) for row in rows]
    return items, len(items)


def _node_to_dict(node: Any) -> dict[str, Any]:
    """Convert a FalkorDB node to a plain dict for serialisation."""
    if hasattr(node, "properties"):
        return dict(node.properties)
    if isinstance(node, dict):
        return node
    return {}
