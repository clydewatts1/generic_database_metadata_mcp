"""Tests for TOON frugality bounds: serialisation and pagination (T018)."""

import json
import pytest

from src.models.serialization import serialise, serialise_list, _MAX_PAYLOAD_BYTES


class TestSerialise:
    def test_basic_dict(self):
        result = serialise({"id": "abc", "name": "Table"})
        data = json.loads(result)
        assert data["id"] == "abc"
        assert data["n"] == "Table"  # abbreviated

    def test_omits_null(self):
        result = serialise({"id": "x", "name": None})
        data = json.loads(result)
        assert "name" not in data
        assert "n" not in data

    def test_omits_empty_string(self):
        result = serialise({"id": "x", "rationale_summary": ""})
        data = json.loads(result)
        assert "rs" not in data
        assert "rationale_summary" not in data

    def test_omits_empty_dict(self):
        result = serialise({"id": "x", "properties": {}})
        data = json.loads(result)
        assert "p" not in data

    def test_omits_empty_list(self):
        result = serialise({"id": "x", "items": []})
        data = json.loads(result)
        assert "items" not in data

    def test_keeps_boolean_false(self):
        """Booleans must never be skipped even if falsy – avoids True==1 collision."""
        result = serialise({"is_active": False})
        data = json.loads(result)
        assert data["is_active"] is False

    def test_keeps_boolean_true(self):
        result = serialise({"is_active": True})
        data = json.loads(result)
        assert data["is_active"] is True

    def test_default_value_skip(self):
        """Global and SYSTEM_GENERATED defaults are stripped to save tokens."""
        result = serialise({"domain_scope": "Global", "created_by_prompt_hash": "SYSTEM_GENERATED"})
        data = json.loads(result)
        assert "ds" not in data
        assert "ph" not in data

    def test_key_abbreviation(self):
        result = serialise({
            "health_score": 0.8,
            "type_category": "NODE",
            "schema_definition": {"f": "string"},
            "version": 2,
        })
        data = json.loads(result)
        assert "hs" in data
        assert "tc" in data
        assert "sd" in data
        assert "v" in data

    def test_truncation_at_10kb(self):
        """Payloads larger than 10 KB must be truncated."""
        big_data = {"items": ["x" * 100] * 200}
        result = serialise(big_data, truncate=True)
        assert len(result.encode()) <= _MAX_PAYLOAD_BYTES

    def test_no_truncation_when_disabled(self):
        """When truncate=False, the full payload is returned regardless of size."""
        big_data = {"items": ["x" * 100] * 200}
        result = serialise(big_data, truncate=False)
        # Should be larger than 10 KB
        assert len(result.encode()) > _MAX_PAYLOAD_BYTES

    def test_single_item_list_flattened(self):
        """A single-element list at the top level should be flattened to its sole item."""
        # Flattening happens when the list is a value passed directly to _compact_value,
        # not when it is a key inside a dict passed to serialise().
        result = serialise([{"id": "abc"}])
        data = json.loads(result)
        # When a single-element list is the top-level value it becomes the item itself
        assert isinstance(data, dict)
        assert data["id"] == "abc"

    def test_multi_item_list_not_flattened(self):
        result = serialise({"items": [{"id": "a"}, {"id": "b"}]})
        data = json.loads(result)
        assert isinstance(data["items"], list)
        assert len(data["items"]) == 2


class TestSerialiseList:
    def _make_items(self, n: int) -> list[dict]:
        return [{"id": f"node-{i}", "name": f"Item{i}"} for i in range(n)]

    def test_page_zero_returns_first_5(self):
        items = self._make_items(10)
        result = serialise_list(items, page=0, page_size=5)
        data = json.loads(result)
        assert data["page"] == 0
        assert data["total"] == 10
        assert len(data["items"]) == 5
        assert data["has_more"] is True

    def test_page_one_returns_next_5(self):
        items = self._make_items(10)
        result = serialise_list(items, page=1, page_size=5)
        data = json.loads(result)
        assert data["page"] == 1
        assert len(data["items"]) == 5
        assert data["has_more"] is False

    def test_partial_last_page(self):
        items = self._make_items(7)
        result = serialise_list(items, page=1, page_size=5)
        data = json.loads(result)
        assert len(data["items"]) == 2
        assert data["has_more"] is False

    def test_empty_items(self):
        result = serialise_list([], page=0, page_size=5)
        data = json.loads(result)
        assert data["total"] == 0
        assert data["has_more"] is False
        # Empty list is omitted by TOON compaction (_should_skip returns True for []);
        # absence of the key is the correct compact representation.
        assert "items" not in data or data.get("items") == []

    def test_default_page_size_5(self):
        """Rule 3.3: max 5 nodes per page."""
        items = self._make_items(20)
        result = serialise_list(items)
        data = json.loads(result)
        assert data["page_size"] == 5
        assert len(data["items"]) == 5
