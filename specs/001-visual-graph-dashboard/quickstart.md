# Quickstart: Visual Web Dashboard

**Branch**: `001-visual-graph-dashboard`
**Date**: 2026-02-28

---

## Prerequisites

- Python ≥ 3.11 with the project's `.venv` activated
- FalkorDB running on `localhost:6379` (e.g., `docker run -p 6379:6379 -d falkordb/falkordb`)
- MCP server optionally running on port 8000 (not required for the dashboard)

---

## Install the one new dependency

```bash
pip install PyJWT
```

---

## Generate a development JWT

The dashboard validates a pre-issued JWT. During development, generate one with the shared secret:

```python
import jwt, datetime
token = jwt.encode(
    {"profile_id": "dev-user", "domain_scope": "Global",
     "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=8)},
    "dev-secret-change-me",
    algorithm="HS256"
)
print(token)
```

Set the secret in your environment:

```bash
export DASHBOARD_JWT_SECRET=dev-secret-change-me
```

---

## Start the dashboard server

```bash
python -m src.dashboard.server
```

Dashboard will be available at: **http://localhost:8080**

---

## Open the dashboard

1. Navigate to `http://localhost:8080` in a browser.
2. The page prompts for your JWT token (paste the value from the generation step above).
3. The graph canvas loads all nodes in `domain_scope = "Global"` (or your configured scope).

---

## Run the dashboard tests

```bash
pytest tests/unit/dashboard/ tests/integration/test_dashboard_api.py tests/contract/test_dashboard_mutations.py -v
```

---

## Environment variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `DASHBOARD_JWT_SECRET` | *(required)* | HS256 signing secret for JWT validation |
| `DASHBOARD_PORT` | `8080` | Port the dashboard server listens on |
| `DASHBOARD_NODE_LIMIT` | `500` | Max nodes returned per `GET /api/graph` |
| `FALKORDB_HOST` | `localhost` | FalkorDB host |
| `FALKORDB_PORT` | `6379` | FalkorDB port |

---

## Key files

| Path | Purpose |
|------|---------|
| `src/dashboard/api.py` | FastAPI app; route definitions |
| `src/dashboard/auth.py` | JWT decode + `DashboardUser` dependency |
| `src/dashboard/graph_service.py` | Wraps `src/graph/query.py`; maps to response models |
| `src/dashboard/server.py` | `uvicorn` entrypoint (port 8080) |
| `dashboard/index.html` | Single-page app shell |
| `dashboard/app.js` | Cytoscape.js canvas, filter panel, search, tooltips |
| `dashboard/style.css` | Layout and edge/node visual styles |
