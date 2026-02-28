"""MCP tools for schema self-correction and healing (Rule 2.7)."""

from typing import Any, Dict

from ..app import mcp
from ...models.serialization import serialise
from ...graph.ontology import list_meta_types, reset_health_score
from ...utils.logging import get_logger

logger = get_logger(__name__)

# Health threshold for suggesting healing
HEALING_THRESHOLD = 0.5


@mcp.tool()
def suggest_schema_heals(
    profile_id: str,
    domain_scope: str = "Global",
) -> str:
    """Suggest schema heals for unhealthy MetaTypes (Rule 2.7).

    Returns MetaTypes in the user's domain with health_score below HEALING_THRESHOLD.
    The AI can then use this to relax or evolve the schema constraints.

    Args:
        profile_id: ID of the requesting user (Rule 5.1).
        domain_scope: User's domain scope (Rule 5.2). Defaults to "Global".

    Returns:
        TOON JSON array of unhealthy MetaTypes with their health scores.
    """
    types = list_meta_types(domain_scope=domain_scope)
    unhealthy = [
        {
            "id": mt.id,
            "name": mt.name,
            "hs": mt.health_score,
            "suggestion": f"Schema for '{mt.name}' has low health ({mt.health_score}). "
                         f"Consider relaxing constraints or making fewer fields required.",
        }
        for mt in types
        if mt.health_score < HEALING_THRESHOLD
    ]
    logger.info(
        "Tool suggest_schema_heals: found %d unhealthy types in domain %s",
        len(unhealthy),
        domain_scope,
    )
    return serialise({"count": len(unhealthy), "suggestions": unhealthy})
