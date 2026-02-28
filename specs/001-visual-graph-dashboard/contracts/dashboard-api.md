# HTTP API Contract: Dashboard Backend

**Feature**: Visual Web Dashboard
**Branch**: `001-visual-graph-dashboard`
**Date**: 2026-02-28
**Base URL**: `http://localhost:8080`
**Auth**: `Authorization: Bearer <JWT>` on all `/api/*` routes

---

## Endpoints

### `GET /api/graph`

Returns the full scoped graph payload for the authenticated user. Called once on page load and on manual refresh.

**Headers**

| Header | Required | Value |
|--------|----------|-------|
| `Authorization` | ✅ | `Bearer <JWT>` |

**Response `200 OK`**

```json
{
  "nodes": [
    {
      "id": "string",
      "label": "string",
      "business_name": "string | null",
      "meta_type_name": "string",
      "domain_scope": "string",
      "properties": { "key": "value" }
    }
  ],
  "edges": [
    {
      "id": "string",
      "source_id": "string",
      "target_id": "string",
      "edge_type": "string",
      "is_stigmergic": true,
      "confidence_score": 0.85,
      "rationale_summary": "string | null",
      "last_accessed": "2026-02-28T12:00:00Z | null"
    }
  ],
  "meta_types": ["Table", "Dashboard", "Column"],
  "node_count": 42,
  "truncated": false,
  "scope": "Finance"
}
```

**Error responses**

| Status | Condition |
|--------|-----------|
| `401 Unauthorized` | Missing or expired JWT |
| `403 Forbidden` | JWT present but missing required claims (`profile_id`, `domain_scope`) |
| `503 Service Unavailable` | Graph engine unreachable |

**Constraints**
- Response MUST contain only nodes where `domain_scope IN [user.domain_scope, "Global"]` (Rule 5.2).
- Response MUST contain at most 500 nodes (`truncated: true` if capped).
- Response MUST NOT contain any mutation side-effects (read-only, Rule FR-001).
- Cypher query depth MUST be bounded at 1–2 hops (Rule 3.1).
- Response is full JSON (NOT TOON-encoded) per Rule 3.6.

---

### `GET /health`

Liveness check. No auth required.

**Response `200 OK`**

```json
{ "status": "ok" }
```

**Response `503 Service Unavailable`** (if graph engine unreachable)

```json
{ "status": "degraded", "detail": "Graph engine unavailable" }
```

---

### `GET /` and static assets

Serves `dashboard/index.html` and associated `app.js`, `style.css` from the `dashboard/` directory.

**No auth required** (authentication is enforced by the browser JS on first API call).

---

## Security Contract

1. Every `/api/*` route MUST validate the JWT **before** any database interaction.
2. The `domain_scope` claim from the JWT MUST be passed directly to `query_graph()` as the scope filter — it MUST NOT be derived from any query parameter or request body.
3. No `/api/*` route MAY accept a `domain_scope` override from the request (the JWT claim is authoritative).
4. No endpoint may issue a `CREATE`, `SET`, `MERGE`, or `DELETE` Cypher statement.

---

## Intentionally Out of Scope

- Token issuance / login endpoint (pre-issued JWT assumed for this release)
- Pagination cursor API (500 node cap with `truncated` flag used instead)
- WebSocket / push endpoints
- Any write operation
