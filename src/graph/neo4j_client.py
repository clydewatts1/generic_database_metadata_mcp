"""Neo4j Graph Database Adapter

Provides FalkorDB-compatible interface for Neo4j Community Edition v5.x.
Implements singleton connection pooling, session management, schema bootstrap,
and result set normalization per contracts/neo4j-adapter-interface.md.

Constitution Compliance:
- FR-001: Supports Neo4j Community Edition v5.x as primary backend
- FR-002: Implements FalkorDB-compatible query interface
- FR-005/006: Automatic schema bootstrap with idempotent constraints/indexes
- FR-007: Per-test database support for ephemeral test isolation
- FR-013: Connection retry logic with exponential backoff
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any, Iterator, Optional

from neo4j import GraphDatabase, Driver, Session, Record

logger = logging.getLogger(__name__)


class Neo4jResultSet:
    """Result adapter converting Neo4j Record objects to FalkorDB-compatible format.
    
    Provides dual access pattern:
    - .result_set: list[list[Any]] for backward compatibility (FalkorDB format)
    - __iter__(): dict iteration with Cypher aliases as keys
    
    Per contract: neo4j-adapter-interface.md ResultSetInterface
    """
    
    def __init__(self, records: list[Record], keys: list[str]):
        """
        Parameters
        ----------
        records : list[Record]
            Raw Neo4j Record results from query execution
        keys : list[str]
            Column names from query (e.g., ['n', 'r'] from RETURN n, r)
        """
        self._records = records
        self._keys = keys
        self.result_set: list[list[Any]] = []
        
        # Materialize result_set as list of lists (FalkorDB compatibility)
        for record in records:
            row: list[Any] = []
            for key in keys:
                value = record.get(key)
                row.append(self._convert_value(value))
            self.result_set.append(row)
    
    def _convert_value(self, value: Any) -> Any:
        """Convert Neo4j native types to FalkorDB-compatible dicts.
        
        - Node → dict with properties
        - Relationship → dict with type and properties
        - Primitive → passthrough
        """
        if hasattr(value, 'properties'):
            # Neo4j Node or Relationship
            props = dict(value.properties) if hasattr(value, 'properties') else {}
            
            # Add type/relationship info
            if hasattr(value, 'type'):  # Relationship
                props['_type'] = value.type
            elif hasattr(value, 'labels'):  # Node
                props['_labels'] = list(value.labels)
            
            return props
        elif isinstance(value, list):
            return [self._convert_value(v) for v in value]
        elif isinstance(value, dict):
            return {k: self._convert_value(v) for k, v in value.items()}
        else:
            return value
    
    def __iter__(self) -> Iterator[dict[str, Any]]:
        """Iterate rows as dictionaries with Cypher aliases as keys.
        
        Yields
        ------
        dict[str, Any]
            Row with keys from query result columns
        """
        for record in self._records:
            row_dict = {}
            for key in self._keys:
                value = record.get(key)
                row_dict[key] = self._convert_value(value)
            yield row_dict


class Neo4jGraph:
    """Session manager for Neo4j query execution.
    
    Provides FalkorDB-compatible query(cypher, params) interface.
    Handles parameter binding, schema bootstrap, transaction semantics.
    
    Per contract: neo4j-adapter-interface.md GraphInterface
    """
    
    def __init__(self, driver: Driver, database: str = "neo4j"):
        """
        Parameters
        ----------
        driver : neo4j.Driver
            Neo4j connection driver (shared singleton)
        database : str
            Target database name (default: "neo4j")
        """
        self._driver = driver
        self._database = database
        self._bootstrapped = False
    
    def query(self, cypher: str, params: Optional[dict[str, Any]] = None) -> Neo4jResultSet:
        """Execute Cypher query with parameter binding.
        
        Parameters
        ----------
        cypher : str
            Cypher query string (must not be empty)
        params : dict[str, Any], optional
            Parameter mapping for query (default: None)
        
        Returns
        -------
        Neo4jResultSet
            Materialized result set with FalkorDB-compatible interface
        
        Raises
        ------
        ValueError
            If cypher is empty or params not dict/None
        RuntimeError
            If query execution fails
        """
        if not cypher or not cypher.strip():
            raise ValueError("cypher must not be empty")
        
        if params is not None and not isinstance(params, dict):
            raise ValueError("params must be dict or None")
        
        if params is None:
            params = {}
        
        # Ensure schema is bootstrapped on first query
        if not self._bootstrapped:
            self._ensure_bootstrap()
            self._bootstrapped = True
        
        try:
            with self._driver.session(database=self._database) as session:
                result = session.run(cypher, params)
                records = list(result)
                keys = result.keys()
                
                return Neo4jResultSet(records, keys)
        
        except Exception as exc:
            logger.error(f"Neo4j query failed: {exc}", extra={"cypher": cypher})
            raise RuntimeError(f"Neo4j query execution failed: {exc}") from exc
    
    def _ensure_bootstrap(self) -> None:
        """Create schema constraints and indexes (idempotent).
        
        Per FR-005, FR-006: Create constraints and indexes on first connection.
        Uses CREATE CONSTRAINT/INDEX IF NOT EXISTS for idempotency.
        
        Raises
        ------
        RuntimeError
            If constraint/index creation fails
        """
        constraints = [
            "CREATE CONSTRAINT metadata_type_name_unique IF NOT EXISTS FOR (n:MetaType) REQUIRE n.name IS UNIQUE",
            "CREATE CONSTRAINT object_node_id_unique IF NOT EXISTS FOR (n:ObjectNode) REQUIRE n.node_id IS UNIQUE",
            "CREATE CONSTRAINT audit_log_id_unique IF NOT EXISTS FOR (n:HumanAuditLog) REQUIRE n.audit_id IS UNIQUE",
        ]
        
        indexes = [
            "CREATE INDEX object_node_scope_index IF NOT EXISTS FOR (n:ObjectNode) ON (n.domain_scope)",
            "CREATE INDEX object_node_meta_type_index IF NOT EXISTS FOR (n:ObjectNode) ON (n.meta_type_name)",
        ]
        
        all_statements = constraints + indexes
        
        try:
            with self._driver.session(database=self._database) as session:
                for statement in all_statements:
                    session.run(statement)
            
            logger.info(f"Schema bootstrap complete for database={self._database}")
        
        except Exception as exc:
            logger.error(f"Schema bootstrap failed: {exc}")
            raise RuntimeError(f"Schema bootstrap failed: {exc}") from exc


class Neo4jClient:
    """Singleton wrapper around Neo4j driver with connection pooling.
    
    Manages driver lifecycle, connection retry logic, and lazy initialization.
    Provides get_driver() method for session creation.
    
    Per contract: neo4j-adapter-interface.md get_graph() function
    """
    
    _instance: Optional[Neo4jClient] = None
    _lock = None
    
    def __new__(cls, uri: str, user: str, password: str, database: str = "neo4j", max_retry_time: int = 5):
        """Lazy singleton initialization."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, uri: str, user: str, password: str, database: str = "neo4j", max_retry_time: int = 5):
        """Initialize Neo4j client (singleton, called once).
        
        Parameters
        ----------
        uri : str
            Neo4j connection URI (e.g., "bolt://localhost:7687")
        user : str
            Authentication username
        password : str
            Authentication password
        database : str
            Target database name (default: "neo4j")
        max_retry_time : int
            Max seconds for retry logic (default: 5)
        """
        if self._initialized:
            return
        
        self.uri = uri
        self.user = user
        self.password = password
        self.database = database
        self.max_retry_time = max_retry_time
        self._driver: Optional[Driver] = None
        self._initialized = True
        
        logger.info(f"Neo4jClient initialized (uri={self._mask_uri(uri)})")
    
    @staticmethod
    def _mask_uri(uri: str) -> str:
        """Mask password in URI for logging."""
        if '@' in uri:
            return uri.split('@')[0].rsplit(':', 1)[0] + "@***:***"
        return uri
    
    def get_driver(self) -> Driver:
        """Get (and lazily initialize) the Neo4j driver.
        
        Returns
        -------
        neo4j.Driver
            Shared connection pool
        """
        if self._driver is None:
            self._driver = GraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password),
                max_retry_time=self.max_retry_time,
            )
            self.verify_connectivity()
        
        return self._driver
    
    def verify_connectivity(self) -> bool:
        """Test connection to Neo4j with retry logic.
        
        Per FR-013: implements exponential backoff (3 retries, max 5 seconds).
        
        Returns
        -------
        bool
            True if connection successful
        
        Raises
        ------
        RuntimeError
            If all retry attempts fail with connection error
        """
        max_retries = 3
        backoff_delays = [0.5, 1.0, 2.0]  # Exponential backoff
        cumulative_time = 0
        
        for attempt in range(max_retries):
            try:
                if self._driver:
                    with self._driver.session(database=self.database) as session:
                        session.run("RETURN 1")
                
                logger.info(f"Neo4j connection verified (attempt {attempt + 1})")
                return True
            
            except Exception as exc:
                cumulative_time += backoff_delays[attempt]
                
                if attempt < max_retries - 1:
                    delay = backoff_delays[attempt]
                    logger.warning(
                        f"Neo4j connection failed (attempt {attempt + 1}/{max_retries}), "
                        f"retrying in {delay}s",
                        extra={"error": str(exc)}
                    )
                    time.sleep(delay)
                else:
                    logger.error(
                        f"Neo4j connection failed after {max_retries} attempts "
                        f"({cumulative_time:.1f}s elapsed)",
                        extra={"error": str(exc)}
                    )
                    raise RuntimeError(
                        f"Neo4j unavailable after {max_retries} retries (max {self.max_retry_time}s): {exc}"
                    ) from exc
        
        return False
    
    def close(self) -> None:
        """Close Neo4j driver connection pool."""
        if self._driver:
            self._driver.close()
            logger.info("Neo4j driver closed")


def get_graph(graph_name: Optional[str] = None) -> Neo4jGraph:
    """Factory function returning Neo4jGraph singleton for given database.
    
    Implements lazy initialization, auto-detection, and schema bootstrap.
    Per contract: neo4j-adapter-interface.md get_graph() function
    
    Parameters
    ----------
    graph_name : str, optional
        Database name (default: uses NEO4J_DATABASE env var or "neo4j")
    
    Returns
    -------
    Neo4jGraph
        Query-compatible graph session manager
    
    Raises
    ------
    RuntimeError
        If Neo4j not available (check NEO4J_URI env var)
    RuntimeError
        If connection retry exhaustion
    """
    # Read Neo4j connection config from environment
    neo4j_uri = os.getenv("NEO4J_URI")
    
    if not neo4j_uri:
        raise RuntimeError(
            "NEO4J_URI environment variable not set. "
            "Set your Neo4j connection URI: export NEO4J_URI=bolt://user:password@localhost:7687"
        )
    
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "")
    
    if not neo4j_password:
        raise RuntimeError(
            "NEO4J_PASSWORD environment variable not set. "
            "Set your Neo4j password: export NEO4J_PASSWORD=your_password"
        )
    
    database = graph_name or os.getenv("NEO4J_DATABASE", "neo4j")
    
    # Ensure database name is not reserved
    if database == "system":
        raise ValueError("database name cannot be 'system' (reserved in Neo4j)")
    
    # Get or create singleton client
    client = Neo4jClient(neo4j_uri, neo4j_user, neo4j_password, database)
    driver = client.get_driver()
    
    # Return session manager for this database
    return Neo4jGraph(driver, database)
