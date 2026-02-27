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


@mcp.tool()
def confirm_schema_heal(
    meta_type_id: str,
    profile_id: str,
) -> str:
    """Confirm that a schema has been healed (Rule 2.7).

    Resets the health_score of a MetaType to 1.0 after the AI has patched/evolved it.

    Args:
        meta_type_id: ID of the MetaType that was healed.
        profile_id: ID of the user/profile confirming the heal (Rule 5.1).

    Returns:
        TOON JSON {"status": "healed"} on success.
    """
    try:
        reset_health_score(meta_type_id)
        logger.info("Tool confirm_schema_heal: reset health for %s by user %s", meta_type_id, profile_id)
        return serialise({"status": "healed", "meta_type_id": meta_type_id})
    except Exception as exc:
        return serialise({"error": "HEAL_FAILED", "message": str(exc)})
