"""TOON formatter – re-exports the canonical TOON serialization helpers.

The implementation lives in src/models/serialization.py (Rule 3.3 / Rule 3.5).
This module provides a stable import path for tool modules and formatters
without duplicating the logic.
"""

from src.models.serialization import serialise, serialise_list  # noqa: F401

__all__ = ["serialise", "serialise_list"]
