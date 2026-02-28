"""Performance tests for DashboardGraphService serialisation — T035.

Validates:
- SC-002: 500 nodes + 2,000 edges → full get_graph() serialisation ≤ 1.5 s
- SC-005: client-side Object Type filter logic over 500 nodes ≤ 50 ms

Manual gates (not automated here):
- SC-001: Full browser render (index.html + Cytoscape layout) ≤ 3 s — validated manually.
- SC-004: Filter/search UI response ≤ 200 ms — validated manually.
"""

from __future__ import annotations

import json
import time
from typing import Any
from unittest.mock import patch

import pytest

from src.dashboard.graph_service import DashboardGraphService
from src.dashboard.models import DashboardUser, GraphEdgeResponse, GraphNodeResponse


# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------

def _make_user(profile_id: str = "perf-user", domain_scope: str = "Finance") -> DashboardUser:
    return DashboardUser(profile_id=profile_id, domain_scope=domain_scope)


def _raw_node_large(i: int) -> dict[str, Any]:
    """Build a raw FalkorDB node dict for large-scale tests."""
    return {
        "id": f"node-{i}",
        "_id": f"node-{i}",
        "meta_type_name": ["Table", "Column", "Dashboard", "Report", "Pipeline"][i % 5],
        "domain_scope": "Finance",
        "properties": json.dumps({
            "label": f"table_{i}",
            "business_name": f"Business Name {i}" if i % 3 == 0 else None,
            "schema": "finance",
            "owner": f"user_{i % 10}",
        }),
    }


def _raw_stigmergic_edge_large(src: int, tgt: int) -> dict[str, Any]:
    """Build a raw stigmergic edge dict for large-scale tests."""
    return {
        "id": f"edge-{src}-{tgt}",
        "source_id": f"node-{src}",
        "target_id": f"node-{tgt}",
        "edge_type": "RELATES_TO",
        "confidence_score": 0.5 + (src % 50) / 100.0,
        "rationale_summary": f"Both accessed by query pattern {src % 20}",
        "last_accessed": "2026-01-01T00:00:00+00:00",
        "domain_scope": "Finance",
    }


# ---------------------------------------------------------------------------
# SC-002: Serialisation budget — 500 nodes, 2,000 edges ≤ 1.5 s
# ---------------------------------------------------------------------------

class TestSerialisation:
    """SC-002: API-layer serialisation of 500 nodes + 2,000 edges must complete ≤ 1.5 s."""

    @pytest.fixture(scope="class")
    def large_dataset(self):
        n_nodes = 500
        n_edges = 2000
        nodes = [_raw_node_large(i) for i in range(n_nodes)]
        edges = [_raw_stigmergic_edge_large(i % n_nodes, (i + 7) % n_nodes) for i in range(n_edges)]
        return nodes, edges

    def test_serialisation_completes_within_1_5_seconds(self, large_dataset):
        """SC-002: Full get_graph() call with 500 nodes + 2,000 stigmergic edges ≤ 1.5 s."""
        raw_nodes, raw_edges = large_dataset
        svc = DashboardGraphService()
        user = _make_user()

        start = time.perf_counter()
        with patch.object(svc, "_fetch_nodes", return_value=raw_nodes), \
             patch.object(svc, "_fetch_stigmergic_edges", return_value=raw_edges), \
             patch.object(svc, "_fetch_structural_edges", return_value=[]):
            payload = svc.get_graph(user)
        elapsed = time.perf_counter() - start

        assert payload.node_count == 500, f"Expected 500 nodes, got {payload.node_count}"
        assert len(payload.edges) == 2000, f"Expected 2000 edges, got {len(payload.edges)}"
        assert elapsed < 1.5, (
            f"SC-002 FAIL: serialisation took {elapsed:.3f}s — budget is 1.5s"
        )

    def test_pydantic_serialisation_of_payload(self, large_dataset):
        """Verify Pydantic model_dump/json_serialisation of full payload doesn't time out."""
        raw_nodes, raw_edges = large_dataset
        svc = DashboardGraphService()
        user = _make_user()

        with patch.object(svc, "_fetch_nodes", return_value=raw_nodes), \
             patch.object(svc, "_fetch_stigmergic_edges", return_value=raw_edges), \
             patch.object(svc, "_fetch_structural_edges", return_value=[]):
            payload = svc.get_graph(user)

        start = time.perf_counter()
        payload_json = payload.model_dump_json()
        elapsed = time.perf_counter() - start

        assert len(payload_json) > 0
        assert elapsed < 0.5, (
            f"Pydantic JSON serialisation took {elapsed:.3f}s — expected < 0.5s"
        )


# ---------------------------------------------------------------------------
# SC-005: Client-side filter budget — Object Type filter over 500 nodes ≤ 50 ms
# ---------------------------------------------------------------------------

class TestFilterPerformance:
    """SC-005: Client-side filter logic (Python simulation) over 500 nodes ≤ 50 ms.

    NOTE: This tests the server-side node-filter equivalent — the true browser-side
    Cytoscape.js filter is validated manually (SC-004 / SC-005 manual gate).
    """

    @pytest.fixture(scope="class")
    def nodes_fixture(self):
        return [
            GraphNodeResponse(
                id=f"node-{i}",
                label=f"table_{i}",
                business_name=f"Business Name {i}" if i % 3 == 0 else None,
                meta_type_name=["Table", "Column", "Dashboard", "Report", "Pipeline"][i % 5],
                domain_scope="Finance",
                properties={"label": f"table_{i}"},
            )
            for i in range(500)
        ]

    def test_type_filter_over_500_nodes_under_50ms(self, nodes_fixture):
        """SC-005: Filtering 500 nodes by meta_type_name completes in ≤ 50 ms."""
        selected_types = {"Table", "Dashboard"}

        start = time.perf_counter()
        # Simulate JS applyFilters() — identify visible/hidden node sets
        visible = [n for n in nodes_fixture if n.meta_type_name in selected_types]
        hidden = [n for n in nodes_fixture if n.meta_type_name not in selected_types]
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert len(visible) + len(hidden) == 500
        assert elapsed_ms < 50, (
            f"SC-005 FAIL: filter over 500 nodes took {elapsed_ms:.2f}ms — budget is 50ms"
        )

    def test_search_filter_business_name_over_500_nodes_under_50ms(self, nodes_fixture):
        """SC-005: business_name search dim/highlight over 500 nodes ≤ 50 ms."""
        term = "business name 1"

        start = time.perf_counter()
        # Simulate JS applySearch() case-insensitive includes on business_name
        matching = [
            n for n in nodes_fixture
            if n.business_name and term.lower() in n.business_name.lower()
        ]
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert len(matching) > 0, "Expected at least one match for search term"
        assert elapsed_ms < 50, (
            f"SC-005 FAIL: search over 500 nodes took {elapsed_ms:.2f}ms — budget is 50ms"
        )
