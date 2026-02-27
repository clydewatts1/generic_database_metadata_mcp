"""Pytest configuration – provides ephemeral FalkorDB graph sandboxes for every test."""

from __future__ import annotations

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
