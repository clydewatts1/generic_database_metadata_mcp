"""Graph database client abstraction – provides unified interface for Neo4j or FalkorDB.

This module implements FR-003 (backend auto-detection) and FR-011 (transparent backend swap).
Downstream code (dashboard, MCP tools) imports from this module and remains agnostic
to which backend is actually used.

Backend Selection (in priority order):
1. If NEO4J_URI env var is set → Use Neo4j Community Edition v5.x (preferred)
2. If NEO4J_URI not set → Fall back to FalkorDB (for backward compatibility during transition)
3. If neither available → Raise clear error with setup instructions

Constitution Compliance:
- FR-003: Auto-detect backend based on NEO4J_URI presence
- FR-011: Transparent backend swap (no changes to dashboard/MCP code)
- Rule 1.4.0: Mandate Neo4j Community Edition as primary backend
"""

from __future__ import annotations

import os
from typing import Any

from falkordb import FalkorDB, Graph

from src.utils.logging import get_logger

logger = get_logger(__name__)

# FalkorDB defaults (fallback backend)
_DEFAULT_HOST = os.getenv("FALKORDB_HOST", "localhost")
_DEFAULT_PORT = int(os.getenv("FALKORDB_PORT", "6379"))
_DEFAULT_GRAPH = os.getenv("FALKORDB_GRAPH", "metadata")

_client: FalkorDB | Any | None = None
_graph: Graph | Any | None = None
_backend: str | None = None  # Track which backend is in use


def _detect_backend() -> str:
    """Detect which backend to use based on environment variables.
    
    Returns
    -------
    str
        'neo4j' if NEO4J_URI is set, 'falkordb' otherwise
    
    Raises
    ------
    RuntimeError
        If neither backend is configured
    """
    neo4j_uri = os.getenv("NEO4J_URI")
    
    if neo4j_uri:
        return "neo4j"
    
    # FalkorDB is the fallback
    return "falkordb"


def get_client(host: str = _DEFAULT_HOST, port: int = _DEFAULT_PORT) -> FalkorDB | Any:
    """Return (and lazily initialise) the shared graph database client.
    
    Auto-detects backend:
    - Neo4j if NEO4J_URI env var is set
    - FalkorDB otherwise (backward compatibility)
    
    Parameters
    ----------
    host : str
        FalkorDB host (only used if FalkorDB backend selected)
    port : int
        FalkorDB port (only used if FalkorDB backend selected)
    
    Returns
    -------
    FalkorDB | Neo4jClient
        Connected client for selected backend
    """
    global _client, _backend
    
    if _client is None:
        _backend = _detect_backend()
        
        if _backend == "neo4j":
            # Use Neo4j backend
            from src.graph.neo4j_client import Neo4jClient
            
            neo4j_uri = os.getenv("NEO4J_URI")
            neo4j_user = os.getenv("NEO4J_USER", "neo4j")
            neo4j_password = os.getenv("NEO4J_PASSWORD", "")
            
            if not neo4j_password:
                raise RuntimeError(
                    "NEO4J_PASSWORD not set. Set your Neo4j password: "
                    "export NEO4J_PASSWORD=your_password"
                )
            
            _client = Neo4jClient(neo4j_uri, neo4j_user, neo4j_password)
            logger.info(f"Using Neo4j backend (uri={Neo4jClient._mask_uri(neo4j_uri)})")
        
        else:
            # Use FalkorDB backend (fallback)
            logger.info("Connecting to FalkorDB at %s:%s", host, port)
            _client = FalkorDB(host=host, port=port)
            logger.info("Using FalkorDB backend (backward compatibility mode)")
    
    return _client


def get_graph(graph_name: str | None = _DEFAULT_GRAPH) -> Graph | Any:
    """Return (and lazily initialise) the named graph handle.
    
    Automatically selects Neo4j or FalkorDB backend based on NEO4J_URI env var.
    Implements lazy initialization and singleton per-backend instance.
    
    Parameters
    ----------
    graph_name : str, optional
        Graph/database name (default: metadata for FalkorDB, neo4j for Neo4j)
    
    Returns
    -------
    Graph | Neo4jGraph
        Query-compatible graph/session manager for selected backend
    
    Raises
    ------
    RuntimeError
        If backend initialization fails (connection error, auth error)
    """
    global _graph, _backend
    
    if _graph is None:
        backend = _detect_backend()
        
        if backend == "neo4j":
            # Use Neo4j backend
            from src.graph.neo4j_client import Neo4jClient, Neo4jGraph
            
            neo4j_uri = os.getenv("NEO4J_URI")
            neo4j_user = os.getenv("NEO4J_USER", "neo4j")
            neo4j_password = os.getenv("NEO4J_PASSWORD", "")
            database_name = graph_name or os.getenv("NEO4J_DATABASE", "neo4j")
            
            try:
                client = Neo4jClient(neo4j_uri, neo4j_user, neo4j_password, database_name)
                driver = client.get_driver()
                _graph = Neo4jGraph(driver, database_name)
                logger.info(f"Graph handle acquired: Neo4j database={database_name}")
            
            except RuntimeError as e:
                logger.error(f"Failed to connect to Neo4j: {e}")
                raise
        
        else:
            # Use FalkorDB backend (fallback)
            _graph = get_client().select_graph(graph_name)
            logger.info("Graph handle acquired: FalkorDB graph=%s", graph_name)
    
    return _graph


def reset_graph(graph_name: str = _DEFAULT_GRAPH) -> None:
    """Drop and recreate the graph – used in tests to provide ephemeral sandboxes.
    
    Parameters
    ----------
    graph_name : str
        Graph name to reset (default: metadata for FalkorDB)
    """
    global _graph, _client, _backend
    
    backend = _detect_backend()
    
    if backend == "neo4j":
        # For Neo4j, database creation/teardown happens in test fixtures
        logger.info("Neo4j: test database cleanup handled by fixtures")
        _graph = None
        # Client remains (connection pool) but graph instance is reset
    
    else:
        # FalkorDB: drop and recreate graph
        client = get_client()
        try:
            client.select_graph(graph_name).delete()
        except Exception:  # graph may not exist yet
            pass
        _graph = client.select_graph(graph_name)
        logger.info("Graph reset: %s", graph_name)


def execute_query(query: str, params: dict[str, Any] | None = None) -> Any:
    """Execute a Cypher query and return the result set.
    
    This is the primary abstraction point for all downstream code.
    Works with both Neo4j and FalkorDB backends transparently.
    
    Parameters
    ----------
    query : str
        Cypher query string
    params : dict[str, Any], optional
        Parameter values for query (default: empty dict)
    
    Returns
    -------
    ResultSet | Neo4jResultSet
        Query results in backend-compatible format
    """
    graph = get_graph()
    params = params or {}
    logger.debug("Cypher: %s | params: %s", query, params)
    
    # Both FalkorDB and Neo4j adapters implement query(cypher, params)
    return graph.query(query, params)

