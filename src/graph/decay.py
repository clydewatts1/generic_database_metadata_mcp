"""Decay runner for stigmergic edges (US4 – T021).

`run_decay_pass(edge_id)` applies time-based decay to a single edge.
`run_all_decay()` iterates every edge in the graph and applies decay.

Decay formula: confidence_score -= DECAY_RATE_PER_DAY * days_elapsed
Edges are pruned (deleted) when confidence_score drops below PRUNE_THRESHOLD.
Decay is only applied once 24 h have elapsed since last_accessed_at.
"""
from __future__ import annotations

from datetime import datetime, timezone

from src.graph.client import get_graph
from src.graph.edges import apply_decay, StigmergicEdge
from src.utils.logging import get_logger

logger = get_logger(__name__)


def run_decay_pass(edge_id: str) -> StigmergicEdge | None:
    """Apply decay to a single edge and return the updated edge (or None if pruned).

    Computes hours elapsed since last_accessed_at using the current wall-clock
    time so that freezegun patches in tests work correctly.
    """
    graph = get_graph()
    result = graph.query(
        "MATCH (e:StigmergicEdge {id: $eid}) RETURN e.last_accessed_at AS ts",
        {"eid": edge_id},
    )
    rows = result.result_set
    if not rows:
        return None

    raw_ts = rows[0][0]
    if isinstance(raw_ts, str):
        last_accessed = datetime.fromisoformat(raw_ts)
        if last_accessed.tzinfo is None:
            last_accessed = last_accessed.replace(tzinfo=timezone.utc)
    else:
        # Already a datetime (FalkorDB may return native datetimes)
        last_accessed = raw_ts
        if last_accessed.tzinfo is None:
            last_accessed = last_accessed.replace(tzinfo=timezone.utc)

    now = datetime.now(timezone.utc)
    hours_elapsed = (now - last_accessed).total_seconds() / 3600.0

    return apply_decay(edge_id, hours_elapsed)


def run_all_decay() -> dict[str, int]:
    """Run decay across all StigmergicEdge nodes.

    Returns a summary dict: {"processed": N, "pruned": M}.
    """
    graph = get_graph()
    result = graph.query("MATCH (e:StigmergicEdge) RETURN e.id")
    edge_ids = [row[0] for row in result.result_set]

    processed = 0
    pruned = 0
    for eid in edge_ids:
        outcome = run_decay_pass(eid)
        processed += 1
        if outcome is None:
            pruned += 1

    logger.info("decay_pass_complete", extra={"processed": processed, "pruned": pruned})
    return {"processed": processed, "pruned": pruned}
