# Data Model: Visual Web Dashboard

**Branch**: `001-visual-graph-dashboard`
**Date**: 2026-02-28
**Source**: [spec.md](spec.md) + [research.md](research.md)

---

## Overview

The dashboard introduces no new graph entities — it is a **read-only projection** of the existing graph. All entities below are Pydantic response models (serialisation layer), not new database nodes or edges.

---

## 1. Response Models (API → Browser)

### `GraphNodeResponse`

Represents a single renderable node on the canvas.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `id` | `str` | ✅ | FalkorDB node element ID |
| `label` | `str` | ✅ | Technical object name (always present); shown as secondary text when `business_name` is set |
| `business_name` | `str \| None` | ❌ | Human-readable alias from `ObjectNode.business_name` property; primary canvas label when present |
| `meta_type_name` | `str` | ✅ | Object Type (e.g., `"Table"`, `"Dashboard"`) — drives Object Type filter |
| `domain_scope` | `str` | ✅ | Scope of this node (e.g., `"Finance"`, `"Global"`) |
| `properties` | `dict[str, Any]` | ✅ | All stored key-value properties; rendered in the detail side-panel |

**Validation rules**:
- `id` must be non-empty.
- `domain_scope` must equal the requesting user's `domain_scope` or `"Global"` (enforced by `DashboardGraphService`, not the model itself).
- `properties` must never include raw internal FalkorDB metadata keys (e.g., element IDs).

---

### `GraphEdgeResponse`

Represents a single renderable edge on the canvas.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `id` | `str` | ✅ | Synthetic edge ID (`"{src_id}__{edge_type}__{tgt_id}"`) |
| `source_id` | `str` | ✅ | ID of the source `GraphNodeResponse` |
| `target_id` | `str` | ✅ | ID of the target `GraphNodeResponse` |
| `edge_type` | `str` | ✅ | Relationship type label (e.g., `"CONTAINS"`, `"RELATES_TO"`) |
| `is_stigmergic` | `bool` | ✅ | `True` if this edge is a `StigmergicEdge`; drives visual encoding branch |
| `confidence_score` | `float \| None` | ❌ | Present only when `is_stigmergic = True`; range 0.0–1.0; drives line weight/colour |
| `rationale_summary` | `str \| None` | ❌ | Present only when `is_stigmergic = True`; shown in hover tooltip |
| `last_accessed` | `str \| None` | ❌ | ISO-8601 datetime string; present only when `is_stigmergic = True`; shown in hover tooltip |

**Validation rules**:
- `confidence_score` must be `None` when `is_stigmergic = False`.
- `confidence_score`, when present, must be clamped to `[0.0, 1.0]`.
- Both `source_id` and `target_id` must reference a node present in the same `GraphPayloadResponse`.

---

### `GraphPayloadResponse`

Top-level response envelope returned by `GET /api/graph`. Single call, load-once.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `nodes` | `list[GraphNodeResponse]` | ✅ | All scoped nodes; max 500 per response |
| `edges` | `list[GraphEdgeResponse]` | ✅ | All edges whose source AND target are in `nodes` |
| `meta_types` | `list[str]` | ✅ | Deduplicated list of all `meta_type_name` values present in `nodes`; populates the Object Type filter dropdown |
| `node_count` | `int` | ✅ | `len(nodes)` — included for client-side informational display |
| `truncated` | `bool` | ✅ | `True` if the graph was capped at 500 nodes; `False` otherwise |
| `scope` | `str` | ✅ | Echo of the `domain_scope` from the JWT used to generate this payload |

---

## 2. Auth / Session Model

### `DashboardUser`

Internal model populated by JWT decode. Never serialised to the browser.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `profile_id` | `str` | ✅ | From JWT claim `profile_id`; identifies the user |
| `domain_scope` | `str` | ✅ | From JWT claim `domain_scope`; injected into every graph query |

**JWT claim requirements**:
- Token must be signed with a shared secret (HS256).
- Must include `exp` claim; the API rejects expired tokens with HTTP 401.
- Must include `profile_id` (string) and `domain_scope` (string); missing claims → HTTP 403.

---

## 3. State Transitions

The dashboard is stateless on the server. All client-side state is ephemeral:

```
Page load
  └──► GET /api/graph (with JWT)
         ├── 401 → display "Login required" banner
         ├── 403 → display "Scope unavailable" banner
         └── 200 → render GraphPayloadResponse
                    └── User interaction (filter / search / click / refresh)
                          └── local FilterState mutation → canvas re-render
                                (no additional API calls until "Refresh" is clicked)
```

---

## 4. Mapping: Graph Layer → Response Models

| Existing entity | → Dashboard model |
|----------------|-------------------|
| `ObjectNode` | `GraphNodeResponse` |
| `StigmergicEdge` (is_stigmergic=True) | `GraphEdgeResponse` with `confidence_score`, `rationale_summary`, `last_accessed` |
| Structural / Flow edge (is_stigmergic=False) | `GraphEdgeResponse` with nulls for stigmergic fields |
| `list_meta_types(domain_scope)` result | `meta_types` list in `GraphPayloadResponse` |
