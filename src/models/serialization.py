"""TOON (Compact Output Serialization) – strips verbosity from graph results.

Reduces token usage by:
  - Omitting null/empty/default values
  - Abbreviating well-known keys
  - Flattening single-item lists
  - Enforcing a hard 10 KB ceiling per response
"""

from __future__ import annotations

import json
from typing import Any

from src.utils.logging import get_logger

logger = get_logger(__name__)

# Hard limit on outbound payload size (bytes)
_MAX_PAYLOAD_BYTES = 10_000

# Key abbreviations: full_key -> short_key
_ABBREV: dict[str, str] = {
    "id": "id",
    "name": "n",
    "type_category": "tc",
    "schema_definition": "sd",
    "health_score": "hs",
    "version": "v",
    "meta_type_id": "mt",
    "domain_scope": "ds",
    "properties": "p",
    "confidence_score": "cs",
    "last_accessed": "la",
    "rationale_summary": "rs",
    "created_by_prompt_hash": "ph",
    "edge_type": "et",
    "source_id": "src",
    "target_id": "tgt",
    "logic_description": "ld",
    "input_schema": "is",
    "output_schema": "os",
}

# Scalar values to omit entirely (saves tokens on defaults).
# NOTE: booleans are intentionally not skipped to avoid True == 1 collision.
_SKIP_STRINGS: frozenset = frozenset({"Global", "SYSTEM_GENERATED", ""})


def _should_skip(v: Any) -> bool:
    """Return True if the value should be omitted from compact output."""
    if v is None:
        return True
    if isinstance(v, bool):
        return False  # never skip booleans – True != 1 at the semantic level
    if isinstance(v, (dict, list)):
        return len(v) == 0
    if isinstance(v, str):
        return v in _SKIP_STRINGS
    return False


def _abbreviate(key: str) -> str:
    return _ABBREV.get(key, key)


def _compact_node(obj: dict[str, Any]) -> dict[str, Any]:
    """Compact a single node/edge dict."""
    result: dict[str, Any] = {}
    for k, v in obj.items():
        if _should_skip(v):
            continue
        # Recursively compact nested dicts
        if isinstance(v, dict):
            v = _compact_node(v)
        result[_abbreviate(k)] = v
    return result


def _compact_value(v: Any) -> Any:
    if isinstance(v, dict):
        return _compact_node(v)
    if isinstance(v, list):
        compacted = [_compact_value(i) for i in v]
        return compacted[0] if len(compacted) == 1 else compacted
    return v


def serialise(data: Any, truncate: bool = True) -> str:
    """Serialise *data* to a compact TOON JSON string.

    Args:
        data: Any JSON-serialisable structure (dict, list, primitive).
        truncate: When True, trim the output to _MAX_PAYLOAD_BYTES.

    Returns:
        A compact JSON string safe to return to the AI context.
    """
    compacted = _compact_value(data)
    raw = json.dumps(compacted, separators=(",", ":"), default=str)

    if truncate and len(raw.encode()) > _MAX_PAYLOAD_BYTES:
        logger.warning(
            "TOON payload exceeded %d bytes (%d), truncating.", _MAX_PAYLOAD_BYTES, len(raw.encode())
        )
        raw = raw[: _MAX_PAYLOAD_BYTES - 3] + "..."

    return raw


def serialise_list(
    items: list[dict[str, Any]],
    page: int = 0,
    page_size: int = 5,
) -> str:
    """Paginate *items* and return the requested page as a compact TOON string.

    Always includes pagination metadata so the AI knows how to fetch the next page.
    """
    total = len(items)
    start = page * page_size
    end = start + page_size
    page_items = items[start:end]

    envelope = {
        "page": page,
        "page_size": page_size,
        "total": total,
        "has_more": end < total,
        "items": [_compact_value(i) for i in page_items],
    }
    return serialise(envelope)
