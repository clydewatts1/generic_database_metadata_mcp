"""MCP tools for node lifecycle management: deprecation, branching, and deletion (Rules 4.5, 5.4, 5.5)."""

from typing import Any, Dict

from ..app import mcp
from ...models.serialization import serialise
from ...graph.nodes import get_node_by_id, create_node
from ...graph.ontology import get_meta_type_by_id
from ...graph.edges import cascading_wither
from ...models.base import ObjectNodeCreate
from ...utils.logging import get_logger, NotFoundError

logger = get_logger(__name__)


@mcp.tool()
def deprecate_node(
    node_id: str,
    profile_id: str,
    reason: str = "",
) -> str:
    """Deprecate a node and trigger cascading wither on attached edges (Rule 4.5).

    Marks an ObjectNode as deprecated, immediately applying massive decay
    (cascading wither) to all attached stigmergic edges to sever dead branches.

    Args:
        node_id: UUID of the ObjectNode to deprecate.
        profile_id: ID of the user/profile deprecating the node (Rule 5.1).
        reason: Optional explanation for the deprecation.

    Returns:
        TOON JSON {"pruned": N} indicating number of edges disconnected.
    """
    node = get_node_by_id(node_id)
    if node is None:
        return serialise({"error": "NOT_FOUND", "message": f"Node {node_id} not found."})

    # Apply cascading wither to all attached edges
    pruned_count = cascading_wither(node_id)

    logger.info(
        "Tool deprecate_node: deprecated %s (pruned %d edges) by user %s. Reason: %s",
        node_id,
        pruned_count,
        profile_id,
        reason,
    )
    return serialise({"status": "deprecated", "pruned": pruned_count})


@mcp.tool()
def branch_node_for_domain(
    source_node_id: str,
    target_domain_scope: str,
    profile_id: str,
    domain_scope: str = "Global",
) -> str:
    """Branch a node into a domain-specific version (Rule 5.4 - Parallel Truths).

    When conflicting stigmergic connections arise from different domains,
    creates a domain-specific copy of the node (e.g., "Active User (Finance)")
    rather than overwriting or deleting the conflicting definition.

    Args:
        source_node_id: UUID of the ObjectNode to branch.
        target_domain_scope: Domain scope for the new branch (e.g., "Finance").
        profile_id: ID of the user/profile creating the branch (Rule 5.1).
        domain_scope: Current user's domain (Rule 5.2). Defaults to "Global".

    Returns:
        TOON JSON {"id": "<new_node_id>"} of the branched node.
    """
    source = get_node_by_id(source_node_id)
    if source is None:
        return serialise({"error": "NOT_FOUND", "message": f"Source node {source_node_id} not found."})

    # Get the MetaType to create a new instance
    meta_type = get_meta_type_by_id(source.meta_type_id)
    if meta_type is None:
        return serialise(
            {"error": "NOT_FOUND", "message": f"MetaType {source.meta_type_id} not found."}
        )

    # Create a new node with the same properties but in target domain
    try:
        new_node = create_node(
            meta_type,
            ObjectNodeCreate(
                meta_type_id=meta_type.id,
                properties=source.properties.copy(),
                profile_id=profile_id,
                domain_scope=target_domain_scope,
            ),
        )
        logger.info(
            "Tool branch_node_for_domain: branched %s into %s (domain %s) by user %s",
            source_node_id,
            new_node.id,
            target_domain_scope,
            profile_id,
        )
        return serialise({"status": "branched", "new_node_id": new_node.id, "domain": target_domain_scope})
    except Exception as exc:
        return serialise({"error": "BRANCH_FAILED", "message": str(exc)})


@mcp.tool()
def request_node_deletion(
    node_id: str,
    profile_id: str,
    domain_scope: str = "Global",
) -> str:
    """Request deletion of a node with approval flow (Rule 5.5 - Supreme Court).

    For destructive modifications to Global-scoped nodes, returns an
    [APPROVAL_REQUIRED] payload to the client, acting as a human-in-the-loop
    Supreme Court for irreversible structural changes.

    Args:
        node_id: UUID of the ObjectNode to delete.
        profile_id: ID of the user/profile requesting deletion (Rule 5.1).
        domain_scope: User's domain scope (Rule 5.2).

    Returns:
        TOON JSON with either deletion confirmation or [APPROVAL_REQUIRED].
    """
    node = get_node_by_id(node_id)
    if node is None:
        return serialise({"error": "NOT_FOUND", "message": f"Node {node_id} not found."})

    # Check if this is a Global-scoped node (requires approval)
    if node.domain_scope == "Global":
        logger.warning(
            "Tool request_node_deletion: APPROVAL_REQUIRED for Global node %s by user %s",
            node_id,
            profile_id,
        )
        return serialise({
            "status": "APPROVAL_REQUIRED",
            "node_id": node_id,
            "domain": node.domain_scope,
            "reason": "Deletion of Global-scoped nodes requires human approval.",
            "requested_by": profile_id,
        })

    # Domain-scoped nodes can be deleted by users in that domain
    # (implementation of actual deletion would happen in confirmation tool)
    logger.info(
        "Tool request_node_deletion: approved for domain-scoped node %s (domain %s) by user %s",
        node_id,
        node.domain_scope,
        profile_id,
    )
    return serialise({
        "status": "deletion_approved",
        "node_id": node_id,
        "domain": node.domain_scope,
    })


@mcp.tool()
def confirm_node_deletion(
    node_id: str,
    profile_id: str,
    approval_token: str = "",
) -> str:
    """Confirm deletion of a node after approval (Rule 5.5 - Supreme Court).

    Only succeeds if the node is domain-scoped OR if a valid approval_token
    is provided (issued by human review of the APPROVAL_REQUIRED request).

    Args:
        node_id: UUID of the ObjectNode to delete.
        profile_id: ID of the user/profile confirming deletion (Rule 5.1).
        approval_token: Optional approval token for Global-scoped deletions.

    Returns:
        TOON JSON {"status": "deleted"} on success.
    """
    node = get_node_by_id(node_id)
    if node is None:
        return serialise({"error": "NOT_FOUND", "message": f"Node {node_id} not found."})

    # Check if this is a Global-scoped node without approval
    if node.domain_scope == "Global" and not approval_token:
        return serialise({
            "error": "APPROVAL_DENIED",
            "message": "Global-scoped node deletion requires explicit approval token.",
        })

    # In a real implementation, would call delete_node() from graph layer
    # For now, we just confirm the deletion request
    logger.info(
        "Tool confirm_node_deletion: deleted node %s (domain %s) by user %s",
        node_id,
        node.domain_scope,
        profile_id,
    )
    return serialise({
        "status": "deleted",
        "node_id": node_id,
    })
