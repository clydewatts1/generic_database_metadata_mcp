# Quickstart: Schema Health Dashboard Widget

**Feature**: `001-schema-health-widget`  
**Branch**: `001-schema-health-widget`

---

## Prerequisites

- Python 3.11+ (project uses 3.14.2)
- FalkorDB running on `localhost:6379` (Docker: `docker run -p 6379:6379 falkordb/falkordb`)
- Virtual environment activated: `.venv\Scripts\activate` (Windows) / `source .venv/bin/activate` (macOS/Linux)
- `DASHBOARD_JWT_SECRET` environment variable set

---

## Setup

```bash
# 1. Install dependencies (no new packages required beyond existing requirements.txt)
pip install -r requirements.txt

# 2. Start FalkorDB
docker run -p 6379:6379 -d --rm falkordb/falkordb

# 3. Set the JWT secret
$env:DASHBOARD_JWT_SECRET = "dev-secret-change-in-production"   # PowerShell
export DASHBOARD_JWT_SECRET="dev-secret-change-in-production"   # bash/zsh

# 4. Start the dashboard server
python -m src.dashboard.server
# Dashboard is now available at http://localhost:8080
```

---

## Using the Widget

1. Open `http://localhost:8080` in a browser.
2. Generate a JWT for your domain (example using Python):

```python
import jwt, datetime
token = jwt.encode(
    {
        "profile_id": "analyst_1",
        "domain_scope": "Finance",
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1),
    },
    "dev-secret-change-in-production",
    algorithm="HS256",
)
print(token)
```

3. Paste the token into the dashboard login prompt.
4. The health widget panel will appear in the sidebar, listing all MetaType nodes in the Finance domain with colour-coded health indicators.
5. Click **Refresh** to re-fetch health scores without reloading the page.

---

## API Access (direct)

```bash
# Get MetaType health scores for the Finance domain
curl -H "Authorization: Bearer <your_jwt>" \
     http://localhost:8080/api/health/meta-types
```

Expected response:
```json
{
  "items": [
    {"id": "...", "name": "CustomerLoan", "type_category": "NODE",
     "health_score": 1.0, "health_band": "green", "domain_scope": "Finance"},
    {"id": "...", "name": "LoanProduct", "type_category": "NODE",
     "health_score": 0.3, "health_band": "red", "domain_scope": "Finance"}
  ],
  "total_available": 2,
  "truncated": false,
  "audit_status": "ok"
}
```

---

## Running Tests

```bash
# Dashboard tests only — no live FalkorDB required
pytest tests/unit/dashboard/ tests/contract/ tests/integration/test_dashboard_api.py -v

# All tests (requires FalkorDB running)
pytest tests/ -v
```

---

## Seeding Test Data

To manually exercise colour bands:

```python
from src.graph.ontology import create_meta_type
from src.models.base import MetaTypeCreate, TypeCategory

create_meta_type(MetaTypeCreate(name="HealthyType", type_category=TypeCategory.NODE,
    schema_definition={}), domain_scope="Finance")  # health_score starts at 1.0 → green

# Trigger degradation (simulates validation failures per Rule 2.6):
from src.graph.ontology import decrement_health_score, get_meta_type_by_name
mt = get_meta_type_by_name("HealthyType")
for _ in range(7):
    decrement_health_score(mt.id)  # → health_score = 0.3 → red band
```

---

## Environment Variables (dashboard)

| Variable | Default | Description |
|----------|---------|-------------|
| `DASHBOARD_JWT_SECRET` | (required) | HS256 signing secret |
| `DASHBOARD_PORT` | `8080` | Dashboard server port |
| `DASHBOARD_NODE_LIMIT` | `500` | Max MetaTypes returned per request |
| `FALKORDB_HOST` | `localhost` | FalkorDB hostname |
| `FALKORDB_PORT` | `6379` | FalkorDB port |
