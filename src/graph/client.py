"""FalkorDB client wrapper – provides a single shared connection to the lightweight FalkorDB graph.

FalkorDB (FalkorDBLite = lightweight embedded version) is our choice of graph database
to keep metadata querying context-frugal. It runs in a separate container for
development and testing.
"""

from __future__ import annotations

import os
from typing import Any

from falkordb import FalkorDB, Graph

from src.utils.logging import get_logger

logger = get_logger(__name__)

# Defaults – override via environment variables in production
_DEFAULT_HOST = os.getenv("FALKORDB_HOST", "localhost")
_DEFAULT_PORT = int(os.getenv("FALKORDB_PORT", "6379"))
_DEFAULT_GRAPH = os.getenv("FALKORDB_GRAPH", "metadata")

_client: FalkorDB | None = None
_graph: Graph | None = None


def get_client(host: str = _DEFAULT_HOST, port: int = _DEFAULT_PORT) -> FalkorDB:
    """Return (and lazily initialise) the shared FalkorDB client.
    
    FalkorDB (lightweight, embedded graph DB) typically runs via Docker for dev/test,
    or as a standalone server in production.
    """
    global _client
    if _client is None:
        logger.info("Connecting to FalkorDB at %s:%s", host, port)
        _client = FalkorDB(host=host, port=port)
    return _client


def get_graph(graph_name: str = _DEFAULT_GRAPH) -> Graph:
    """Return (and lazily initialise) the named graph handle."""
    global _graph
    if _graph is None:
        _graph = get_client().select_graph(graph_name)
        logger.info("Graph handle acquired: %s", graph_name)
    return _graph


def reset_graph(graph_name: str = _DEFAULT_GRAPH) -> None:
    """Drop and recreate the graph – used in tests to provide ephemeral sandboxes."""
    global _graph, _client
    client = get_client()
    try:
        client.select_graph(graph_name).delete()
    except Exception:  # graph may not exist yet
        pass
    _graph = client.select_graph(graph_name)
    logger.info("Graph reset: %s", graph_name)


def execute_query(query: str, params: dict[str, Any] | None = None) -> Any:
    """Execute a Cypher query and return the raw result set."""
    graph = get_graph()
    params = params or {}
    logger.debug("Cypher: %s | params: %s", query, params)
    return graph.query(query, params)
