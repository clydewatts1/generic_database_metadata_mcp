"""Bootstrap FalkorDB indices required by the Schema Health Dashboard Widget.

Creates the following indices (idempotent — safe to run multiple times):
  - CREATE INDEX FOR (a:HumanAuditLog) ON (a.profile_id)
  - CREATE INDEX FOR (a:HumanAuditLog) ON (a.timestamp)

These are recommended in data-model.md §HumanAuditEntry to support efficient
audit log queries under load.

Usage:
    python scripts/bootstrap_indices.py

Requires FALKORDB_HOST and FALKORDB_PORT env vars (defaults: localhost:6379).
"""

from __future__ import annotations

import os
import sys

# Make sure the src package is importable when run from repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def bootstrap_indices() -> None:
    """Create FalkorDB indices for HumanAuditLog nodes."""
    from src.graph.client import execute_query

    indices = [
        ("profile_id", "CREATE INDEX FOR (a:HumanAuditLog) ON (a.profile_id)"),
        ("timestamp", "CREATE INDEX FOR (a:HumanAuditLog) ON (a.timestamp)"),
    ]

    for field_name, query in indices:
        try:
            execute_query(query, {})
            print(f"[OK] Index on HumanAuditLog.{field_name} created (or already exists).")
        except Exception as exc:  # noqa: BLE001
            # FalkorDB raises an error if the index already exists — skip silently
            err_msg = str(exc).lower()
            if "already exists" in err_msg or "index already" in err_msg:
                print(f"[SKIP] Index on HumanAuditLog.{field_name} already exists.")
            else:
                print(f"[WARN] Could not create index on HumanAuditLog.{field_name}: {exc}")


if __name__ == "__main__":
    bootstrap_indices()
