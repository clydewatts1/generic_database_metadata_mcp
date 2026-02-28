"""DashboardGraphService: read-only projection of the metadata graph for the dashboard.

Queries ObjectNodes and StigmergicEdges from FalkorDB, maps them to dashboard
response models, and enforces the 500-node cap (FR-002 / data-model.md).

Rules enforced:
- Rule 3.1 (bounded depth): only a flat scan of scoped nodes — no unbounded traversal.
- Rule 5.2 (domain_scope from JWT only): domain_scope is passed through from the
  DashboardUser; never read from request params.
- FR-001 (zero mutations): this service issues only MATCH queries.
- FR-010 (full JSON, not TOON): response models use full key names.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from src.graph.client import execute_query
from .models import (
    DashboardUser,
    GraphEdgeResponse,
    GraphNodeResponse,
    GraphPayloadResponse,
)

logger = logging.getLogger(__name__)

_NODE_CAP = 500


class DashboardGraphService:
    """Read-only graph service for the Visual Web Dashboard.

    All methods issue only MATCH (read) Cypher statements — never MERGE, SET,
    CREATE, or DELETE.
    """

    def get_graph(self, user: DashboardUser) -> GraphPayloadResponse:
        """Return a scoped graph payload for the given authenticated user.

        Parameters
        ----------
        user:
            Decoded JWT claims. *domain_scope* from this object is the only
            scope source — never overridden by params (Rule 5.2).
        """
        domain_scope = user.domain_scope

        # ----- 1. Fetch scoped ObjectNodes (read-only MATCH) -----
        raw_nodes = self._fetch_nodes(domain_scope)
        truncated = len(raw_nodes) > _NODE_CAP
        raw_nodes = raw_nodes[:_NODE_CAP]

        # Build a set of all node IDs for edge filtering
        node_ids: set[str] = {n["_id"] for n in raw_nodes}

        # ----- 2. Map nodes to response models -----
        nodes = [self._to_node_response(n) for n in raw_nodes]

        # ----- 3. Fetch StigmergicEdges between scoped nodes -----
        raw_stigmergic = self._fetch_stigmergic_edges(node_ids)
        edges: list[GraphEdgeResponse] = [
            self._to_stigmergic_edge_response(e) for e in raw_stigmergic
        ]

        # ----- 4. Fetch structural / graph-level relationships -----
        structural_edges = self._fetch_structural_edges(node_ids)
        edges.extend(structural_edges)

        # ----- 5. Derive meta_types from nodes -----
        meta_types: list[str] = sorted(
            {n.meta_type_name for n in nodes if n.meta_type_name}
        )

        return GraphPayloadResponse(
            nodes=nodes,
            edges=edges,
            meta_types=meta_types,
            node_count=len(nodes),
            truncated=truncated,
            scope=domain_scope,
        )

    # ------------------------------------------------------------------
    # Private helpers — all read-only Cypher
    # ------------------------------------------------------------------

    def _fetch_nodes(self, domain_scope: str) -> list[dict[str, Any]]:
        """Return all ObjectNode raw dicts within the given domain_scope (including Global).

        Returns one dict per node with an ``_id`` helper key for edge lookup.
        """
        cypher = (
            "MATCH (n:ObjectNode) "
            "WHERE n.domain_scope = $ds OR n.domain_scope = 'Global' "
            "RETURN n"
        )
        result = execute_query(cypher, {"ds": domain_scope})
        out: list[dict[str, Any]] = []
        for row in result.result_set:
            node = row[0]
            props = dict(node.properties) if hasattr(node, "properties") else dict(node)
            # Attach internal ID helper
            props["_id"] = props.get("id", "")
            out.append(props)
        return out

    def _to_node_response(self, raw: dict[str, Any]) -> GraphNodeResponse:
        """Map a raw FalkorDB ObjectNode property dict to a GraphNodeResponse.

        ``properties`` in FalkorDB is stored as a JSON string; we unpack it
        to a dict for the side-panel display.
        """
        raw_props_json = raw.get("properties", "{}")
        try:
            inner_props: dict[str, Any] = (
                json.loads(raw_props_json) if isinstance(raw_props_json, str) else raw_props_json
            )
        except (json.JSONDecodeError, TypeError):
            inner_props = {}

        label: str = inner_props.get("label") or raw.get("id", "")
        business_name: str | None = inner_props.get("business_name") or None

        # Sanitise: never expose internal FalkorDB metadata keys
        clean_props = {k: v for k, v in inner_props.items() if not k.startswith("_")}

        return GraphNodeResponse(
            id=raw.get("id", ""),
            label=label,
            business_name=business_name,
            meta_type_name=raw.get("meta_type_name", ""),
            domain_scope=raw.get("domain_scope", "Global"),
            properties=clean_props,
        )

    def _fetch_stigmergic_edges(self, node_ids: set[str]) -> list[dict[str, Any]]:
        """Return all StigmergicEdge property dicts where BOTH endpoints are in node_ids."""
        if not node_ids:
            return []
        ids_list = list(node_ids)
        cypher = (
            "MATCH (e:StigmergicEdge) "
            "WHERE e.source_id IN $ids AND e.target_id IN $ids "
            "RETURN e"
        )
        result = execute_query(cypher, {"ids": ids_list})
        out: list[dict[str, Any]] = []
        for row in result.result_set:
            edge_node = row[0]
            props = dict(edge_node.properties) if hasattr(edge_node, "properties") else dict(edge_node)
            out.append(props)
        return out

    def _to_stigmergic_edge_response(self, raw: dict[str, Any]) -> GraphEdgeResponse:
        """Map a raw StigmergicEdge FalkorDB node to a GraphEdgeResponse."""
        source_id = raw.get("source_id", "")
        target_id = raw.get("target_id", "")
        edge_type = raw.get("edge_type", "STIGMERGIC")

        # Clamp confidence_score to [0.0, 1.0]
        raw_score = raw.get("confidence_score")
        if raw_score is not None:
            try:
                score = float(raw_score)
                score = max(0.0, min(1.0, score))
            except (ValueError, TypeError):
                score = 0.5
        else:
            score = 0.5

        last_accessed = raw.get("last_accessed")
        rationale_summary = raw.get("rationale_summary") or None

        return GraphEdgeResponse(
            id=f"{source_id}__{edge_type}__{target_id}",
            source_id=source_id,
            target_id=target_id,
            edge_type=edge_type,
            is_stigmergic=True,
            confidence_score=score,
            rationale_summary=rationale_summary,
            last_accessed=str(last_accessed) if last_accessed else None,
        )

    def _fetch_structural_edges(self, node_ids: set[str]) -> list[GraphEdgeResponse]:
        """Return graph-level (structural/flow) FalkorDB relationships between scoped nodes.

        Returns GraphEdgeResponse instances with is_stigmergic=False.
        """
        if not node_ids:
            return []
        ids_list = list(node_ids)
        cypher = (
            "MATCH (a:ObjectNode)-[r]-(b:ObjectNode) "
            "WHERE a.id IN $ids AND b.id IN $ids "
            "RETURN a.id, type(r), b.id"
        )
        try:
            result = execute_query(cypher, {"ids": ids_list})
        except Exception as exc:  # noqa: BLE001
            logger.warning("Structural edge query failed (may be normal if no relationships): %s", exc)
            return []

        seen: set[str] = set()
        edges: list[GraphEdgeResponse] = []
        for row in result.result_set:
            try:
                src_id, rel_type, tgt_id = str(row[0]), str(row[1]), str(row[2])
                edge_id = f"{src_id}__{rel_type}__{tgt_id}"
                if edge_id in seen:
                    continue
                seen.add(edge_id)
                edges.append(
                    GraphEdgeResponse(
                        id=edge_id,
                        source_id=src_id,
                        target_id=tgt_id,
                        edge_type=rel_type,
                        is_stigmergic=False,
                        confidence_score=None,
                        rationale_summary=None,
                        last_accessed=None,
                    )
                )
            except (IndexError, ValueError):
                continue
        return edges
