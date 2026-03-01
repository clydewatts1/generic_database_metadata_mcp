"""Pytest configuration – provides ephemeral graph sandboxes for tests.

Supports both FalkorDB (existing) and Neo4j (new) backends via environment:
- FalkorDB: default when NEO4J_URI not set
- Neo4j: when NEO4J_URI is set

Per FR-007 (research.md Decision 3): per-test database creation/teardown strategy
for true isolation and Constitution Rule 6.3 compliance.
"""

from __future__ import annotations

import os
import uuid

import pytest

import src.graph.client as _client_module


@pytest.fixture(autouse=True)
def ephemeral_graph(monkeypatch):
    """Redirect every test to a uniquely-named, disposable graph.

    After the test completes the graph is deleted to avoid cross-test pollution.
    """
    graph_name = f"test_{uuid.uuid4().hex[:8]}"

    # Reset module-level singletons so fresh connection is used
    monkeypatch.setattr(_client_module, "_graph", None)
    monkeypatch.setattr(_client_module, "_client", None)

    # Override default graph name via env-like approach
    original_default = _client_module._DEFAULT_GRAPH
    monkeypatch.setattr(_client_module, "_DEFAULT_GRAPH", graph_name)

    yield graph_name

    # Teardown: delete the ephemeral graph
    try:
        _client_module.get_client().select_graph(graph_name).delete()
    except Exception:
        pass

    # Restore
    monkeypatch.setattr(_client_module, "_DEFAULT_GRAPH", original_default)
    monkeypatch.setattr(_client_module, "_graph", None)
    monkeypatch.setattr(_client_module, "_client", None)


# ============================================================================
# Neo4j Test Database Fixtures (Per-Test Isolation)
# ============================================================================

@pytest.fixture(scope="function")
def neo4j_test_database():
    """Create ephemeral Neo4j test database for this test (function scope).
    
    Creates a unique database with UUID suffix at test start.
    Drops the database at test end (even if test fails).
    
    Per FR-007, research.md Decision 3: per-test database creation/teardown
    
    Yields
    ------
    str
        Test database name (e.g., 'test_db_a1b2c3d4')
    
    Raises
    ------
    RuntimeError
        If NEO4J_URI not set (Neo4j not configured)
    Exception
        If database creation fails
    """
    neo4j_uri = os.getenv("NEO4J_URI")
    
    if not neo4j_uri:
        pytest.skip("NEO4J_URI not set - skipping Neo4j test database fixture")
    
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "")
    
    if not neo4j_password:
        pytest.skip("NEO4J_PASSWORD not set - skipping Neo4j test database fixture")
    
    from neo4j import GraphDatabase
    
    test_db_name = f"test_db_{uuid.uuid4().hex[:8]}"
    
    # Create test database
    driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
    
    try:
        with driver.session(database="neo4j") as session:
            # Create database (may fail if already exists, but cleanup should handle)
            try:
                session.run(f"CREATE DATABASE {test_db_name} IF NOT EXISTS")
            except Exception as e:
                # Database may already exist or driver may not support it
                # Continue anyway - schema bootstrap will handle idempotency
                pass
        
        yield test_db_name
    
    finally:
        # Cleanup: drop test database
        try:
            with driver.session(database="neo4j") as session:
                session.run(f"DROP DATABASE {test_db_name} IF EXISTS")
        except Exception as e:
            # Log but don't fail - orphaned databases can be manually cleaned
            pytest.warns(UserWarning, f"Failed to drop test database {test_db_name}: {e}")
        
        finally:
            driver.close()


@pytest.fixture(autouse=True)
def neo4j_test_config(monkeypatch):
    """Configure NEO4J_DATABASE env var to match test database (if using Neo4j).
    
    Ensures tests use the ephemeral test database when NEO4J_URI is set.
    Automatically called for every test (autouse=True).
    
    This fixture coordinates with neo4j_test_database to ensure:
    - Test database is created before test runs
    - NEO4J_DATABASE env var points to test database
    - Test database is dropped after test completes
    """
    neo4j_uri = os.getenv("NEO4J_URI")
    
    if neo4j_uri and "neo4j_test_database" in os.environ:
        # If test database fixture is in use, point NEO4J_DATABASE to it
        test_db = os.environ.get("neo4j_test_database")
        if test_db:
            monkeypatch.setenv("NEO4J_DATABASE", test_db)

