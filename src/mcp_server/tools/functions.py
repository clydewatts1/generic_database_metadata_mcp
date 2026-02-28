"""MCP tools for FunctionObject management (create/query/attach)."""

from __future__ import annotations

from typing import Any

from ..app import mcp
from ...graph.functions import (
    attach_function_to_node,
    create_function as create_function_graph,
    search_functions,
)
from ...models.base import FunctionObjectCreate
from ...models.serialization import serialise
from ...utils.logging import NotFoundError, ValidationError, get_logger

logger = get_logger(__name__)


@mcp.tool()
def create_function(
    name: str,
    logic_description: str,
    input_schema: dict[str, Any],
    output_schema: dict[str, Any],
    profile_id: str,
    domain_scope: str = "Global",
) -> str:
    """Register a FunctionObject representing an ETL/logic transformation."""
    try:
        data = FunctionObjectCreate(
            name=name,
            logic_description=logic_description,
            input_schema=input_schema,
            output_schema=output_schema,
            profile_id=profile_id,
        )
        created = create_function_graph(data, domain_scope=domain_scope)
        logger.info(
            "Tool create_function: created %s (%s) by %s in %s",
            created.name,
            created.id,
            profile_id,
            domain_scope,
        )
        return serialise({"status": "SUCCESS", "function_id": created.id})
    except ValidationError as exc:
        return serialise({"status": "VALIDATION_ERROR", **exc.to_dict()})
    except ValueError as exc:
        return serialise({"status": "VALIDATION_ERROR", "error": "VALIDATION_ERROR", "message": str(exc)})
    except Exception as exc:
        return serialise({"status": "VALIDATION_ERROR", "error": "VALIDATION_ERROR", "message": str(exc)})


@mcp.tool()
def query_functions(
    profile_id: str,
    domain_scope: str,
    filter: str = "",
    page: int = 1,
    page_size: int = 5,
) -> str:
    """Query FunctionObjects by name/description with pagination and scoping."""
    try:
        page = max(1, page)
        page_size = max(1, min(page_size, 5))

        items, total_count = search_functions(
            filter_text=filter,
            domain_scope=domain_scope,
            page=page,
            page_size=page_size,
        )

        total_pages = (total_count + page_size - 1) // page_size if total_count else 0
        payload = {
            "functions": [
                {
                    "id": f.id,
                    "name": f.name,
                    "logic_description": f.logic_description,
                    "domain_scope": f.domain_scope,
                    "version": f.version,
                }
                for f in items
            ],
            "total_count": total_count,
            "current_page": page,
            "total_pages": total_pages,
        }

        logger.info(
            "Tool query_functions: profile=%s domain=%s filter='%s' total=%d page=%d",
            profile_id,
            domain_scope,
            filter,
            total_count,
            page,
        )
        return serialise(payload)
    except Exception as exc:
        return serialise({"error": "QUERY_FAILED", "message": str(exc)})


@mcp.tool()
def attach_function_to_nodes(
    function_id: str,
    target_node_ids: list[str],
    relationship_type: str,
    profile_id: str,
) -> str:
    """Attach one FunctionObject to one-or-more ObjectNodes."""
    created = 0
    failed = 0
    failed_node_ids: list[str] = []

    for node_id in target_node_ids:
        try:
            ok = attach_function_to_node(function_id, node_id, relationship_type)
            if ok:
                created += 1
            else:
                failed += 1
                failed_node_ids.append(node_id)
        except (ValidationError, NotFoundError):
            failed += 1
            failed_node_ids.append(node_id)

    status = "SUCCESS"
    if created > 0 and failed > 0:
        status = "PARTIAL_SUCCESS"
    elif created == 0 and failed > 0:
        status = "VALIDATION_ERROR"

    logger.info(
        "Tool attach_function_to_nodes: function=%s rel=%s created=%d failed=%d by %s",
        function_id,
        relationship_type,
        created,
        failed,
        profile_id,
    )
    return serialise(
        {
            "status": status,
            "attachments_created": created,
            "attachments_failed": failed,
            "failed_node_ids": failed_node_ids,
        }
    )
