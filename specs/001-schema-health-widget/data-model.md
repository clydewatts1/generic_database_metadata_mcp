# Data Model: Schema Health Dashboard Widget

**Feature**: `001-schema-health-widget`  
**Source**: `research.md` (Phase 0) + `spec.md`

---

## Entities

### 1. MetaTypeHealthRecord *(read projection — no new graph nodes)*

A read-only projection of an existing `(:MetaType)` graph node. The dashboard never writes this entity; it is constructed from `src.graph.ontology.list_meta_types()` results.

| Field | Type | Source | Notes |
|-------|------|--------|-------|
| `id` | `str` | `MetaType.id` | UUID, unique globally |
| `name` | `str` | `MetaType.name` | PascalCase, unique within domain |
| `type_category` | `str` | `MetaType.type_category` | `"NODE"` or `"EDGE"` |
| `health_score` | `float` | `MetaType.health_score` | `[0.0, 1.0]`; decremented by Rule 2.6 on validation failure |
| `domain_scope` | `str` | `MetaType.domain_scope` | Scoping value; only returned when matching JWT claim |
| `health_band` | `str` | **computed** | `"green"` (≥0.8) / `"amber"` (0.5–<0.8) / `"red"` (<0.5) — derived server-side; not stored |

**Health band computation** (FR-003):
```
health_score >= 0.8  →  "green"
health_score >= 0.5  →  "amber"   (0.5 is inclusive lower bound of amber)
health_score <  0.5  →  "red"
```

**Validation rules**:
- `health_score` MUST be clamped to `[0.0, 1.0]` in the Pydantic model (defensive; FalkorDB stores floored values)
- `health_band` MUST be derived from `health_score` at serialisation time; it is never stored

---

### 2. HumanAuditEntry *(new graph node — written on every widget request)*

A new `(:HumanAuditLog)` node created by the Unified Security Layer (Rule 5.6 step 4) **before** the data query executes (Rule 5.7 atomicity). Stored in FalkorDB.

| Field | Type | Nullable | Notes |
|-------|------|----------|-------|
| `id` | `str` | No | UUID, generated at write time |
| `profile_id` | `str` | No | From JWT claim `profile_id` |
| `domain_scope` | `str` | No | From JWT claim `domain_scope` |
| `action_type` | `str` | No | Literal `"READ"` for widget loads; `"MUTATION"` for future override ops |
| `endpoint_path` | `str` | No | `Request.url.path` (e.g., `"/api/health/meta-types"`) |
| `human_session_id` | `str` | No | `"tok:{sha256(jwt)[:8]}"` or `"ip:{client_ip}"` (R-002) |
| `timestamp` | `str` | No | UTC ISO-8601 string, e.g. `"2026-02-28T10:00:00Z"` |
| `entity_summary` | `str` \| `None` | Yes | Populated post-query: count of MetaTypes returned (`"count:N"`) |

**Validation rules**:
- `action_type` MUST be `"READ"` or `"MUTATION"` — no other values permitted
- `created_by_prompt_hash` MUST NOT be present (Rule 5.7: reserved for AI actions per Rule 4.4)
- `timestamp` MUST be UTC; local time is forbidden
- `id` MUST be generated at write time, never caller-supplied

**Cypher node label**: `:HumanAuditLog`

**Recommended FalkorDB indices**:
```cypher
CREATE INDEX FOR (a:HumanAuditLog) ON (a.profile_id)
CREATE INDEX FOR (a:HumanAuditLog) ON (a.timestamp)
```

**Retention**: Full operational lifetime of the Stigmergic Graph Engine (Rule 5.7). No TTL or pruning.

---

## API Response Models *(new Pydantic models in `src/dashboard/models.py`)*

### MetaTypeHealthResponse

```python
class MetaTypeHealthResponse(BaseModel):
    id: str
    name: str
    type_category: str
    health_score: float             # [0.0, 1.0], clamped
    health_band: str                # "green" | "amber" | "red"  (computed)
    domain_scope: str
```

### HealthPayloadResponse

```python
class HealthPayloadResponse(BaseModel):
    items: list[MetaTypeHealthResponse]
    total_available: int            # total in-scope count before cap
    truncated: bool                 # True if total_available > DASHBOARD_NODE_LIMIT
    audit_status: str               # "ok" | "failed" (for degraded audit transparency)
```

---

## State Transitions

### MetaType health_score (existing, read here — not modified)

```
1.0  ──(validation failure, Rule 2.6 decrement −0.1)──▶  0.9 → ... → 0.0
0.0  ──(heal confirmed, Rule 2.7 reset)──▶  1.0
```

The widget only reads this state — it never writes to `:MetaType` nodes.

### HumanAuditLog node lifecycle

```
[Request arrives]
    ↓
[USL: JWT valid, claims present]
    ↓
[AuditService: CREATE (:HumanAuditLog {...})]  ← FAILS → HTTP 503
    ↓
[HealthService: MATCH (:MetaType) ...]        ← FAILS → HTTP 503 + audit node retained
    ↓
[200 response]
```

---

## Relationships

| From | Relationship | To | Notes |
|------|-------------|-----|-------|
| `(:HumanAuditLog)` | none (standalone node) | — | No graph edges from audit nodes; avoids polluting the stigmergic graph topology |

Audit nodes deliberately carry no edges — they are event records, not semantic participants in the metadata graph.
