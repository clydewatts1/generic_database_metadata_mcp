# Contract: GET /api/health/meta-types

**Feature**: `001-schema-health-widget`  
**Route**: `GET /api/health/meta-types`  
**Service**: Visual Web Dashboard (FastAPI, port 8080)  
**Auth**: Bearer JWT (HS256, `DASHBOARD_JWT_SECRET`)

---

## Overview

Read-only endpoint that returns all `(:MetaType)` graph nodes visible to the authenticated user's `domain_scope`, with their current `health_score` and derived `health_band`. Protected by the Unified Security Layer (Rule 5.6); exempt from TOON serialisation (Rule 3.6).

---

## Request

```
GET /api/health/meta-types
Authorization: Bearer <jwt>
```

**Headers**:
| Header | Required | Value |
|--------|----------|-------|
| `Authorization` | Yes | `Bearer <HS256 JWT>` |
| `X-Forwarded-For` | No | Passed through for `human_session_id` IP fallback |

**Path parameters**: none  
**Query parameters**: none (domain scope is read ONLY from JWT claim — Rule 5.2; no `?scope=` override permitted)  
**Request body**: none

---

## Responses

### 200 OK — Normal response

```json
{
  "items": [
    {
      "id": "a1b2c3d4-...",
      "name": "CustomerLoan",
      "type_category": "NODE",
      "health_score": 0.9,
      "health_band": "green",
      "domain_scope": "Finance"
    },
    {
      "id": "e5f6g7h8-...",
      "name": "LoanProduct",
      "type_category": "NODE",
      "health_score": 0.3,
      "health_band": "red",
      "domain_scope": "Finance"
    }
  ],
  "total_available": 2,
  "truncated": false,
  "audit_status": "ok"
}
```

**Response model**: `HealthPayloadResponse`

| Field | Type | Notes |
|-------|------|-------|
| `items` | `MetaTypeHealthResponse[]` | In-scope MetaTypes, capped to `DASHBOARD_NODE_LIMIT` |
| `total_available` | `int` | Total count in scope before cap |
| `truncated` | `bool` | `true` if `total_available > DASHBOARD_NODE_LIMIT` |
| `audit_status` | `"ok" \| "failed"` | `"ok"` on normal path; `"failed"` only in degraded audit transparency edge case |

**MetaTypeHealthResponse model**:

| Field | Type | Constraints |
|-------|------|-------------|
| `id` | `str` | Non-empty UUID |
| `name` | `str` | PascalCase |
| `type_category` | `str` | `"NODE"` \| `"EDGE"` |
| `health_score` | `float` | `[0.0, 1.0]` inclusive |
| `health_band` | `str` | `"green"` \| `"amber"` \| `"red"` |
| `domain_scope` | `str` | Matches JWT `domain_scope` claim |

### 200 OK — Empty domain (no MetaTypes in scope)

```json
{
  "items": [],
  "total_available": 0,
  "truncated": false,
  "audit_status": "ok"
}
```

### 200 OK — Truncated (>500 MetaTypes in scope)

```json
{
  "items": [ "...500 items..." ],
  "total_available": 743,
  "truncated": true,
  "audit_status": "ok"
}
```

### 401 Unauthorized — Missing, malformed, or expired JWT

```json
{
  "detail": "Missing Bearer token"
}
```
```json
{
  "detail": "Token has expired"
}
```

**Headers**: `WWW-Authenticate: Bearer`  
No audit log is written (USL exits before audit step when no valid token exists).

### 403 Forbidden — Valid JWT missing required claims

```json
{
  "detail": "Missing required claim: domain_scope"
}
```

No audit log is written (USL exits at claim-check before audit step).

### 405 Method Not Allowed — Non-GET request

Any `POST`, `PUT`, `PATCH`, or `DELETE` to this path returns HTTP 405 (FastAPI default for unregistered methods).

### 503 Service Unavailable — FalkorDB unreachable OR audit write failure

```json
{
  "status": "degraded",
  "message": "Schema health data temporarily unavailable"
}
```

```json
{
  "status": "degraded",
  "message": "Schema health data temporarily unavailable",
  "audit_status": "failed"
}
```

The second form is returned when FalkorDB is unreachable for both the audit write and the data query. `audit_status: "failed"` is present only when the audit write itself failed.

---

## Security Constraints

1. **JWT validation** (Rule 5.6 step 1): 401 for absent/malformed/expired token
2. **Claims check** (Rule 5.6 step 2): 403 for missing `profile_id` or `domain_scope`
3. **Scope injection** (Rule 5.6 step 3): `domain_scope` passed as Cypher parameter only — no query-string override
4. **Audit write** (Rule 5.6 step 4 / Rule 5.7): `(:HumanAuditLog)` created before data query
5. **Read-only** (FR-004): Zero `CREATE`/`SET`/`DELETE`/`MERGE` in any code path from this route
6. **TOON exempt** (Rule 3.6): Full JSON returned — no abbreviation or compression

---

## Side Effects

| Effect | Conditions |
|--------|-----------|
| `(:HumanAuditLog)` node created in FalkorDB | Every successful request (post-auth, post-claims-check) |
| No MetaType nodes mutated | Always — read-only by constitution |

---

## Colour Band Thresholds

| `health_score` range | `health_band` | CSS class |
|--------------------|---------------|-----------|
| 0.8 ≤ score ≤ 1.0 | `"green"` | `health-green` |
| 0.5 ≤ score < 0.8 | `"amber"` | `health-amber` |
| 0.0 ≤ score < 0.5 | `"red"` | `health-red` |

*Boundary values are inclusive on the lower bound of each band.*
