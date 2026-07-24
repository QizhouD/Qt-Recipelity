"""
Read-only audit script for the legacy SQLite database.

Usage:
    python scripts/audit_db.py [path-to-db]

Reports table row counts, orphan records, and empty/null fields.
Does NOT modify the database.
"""

from __future__ import annotations

import os
import sqlite3
import sys
from datetime import datetime


def audit(db_path: str) -> dict:
    if not os.path.exists(db_path):
        return {"error": f"Database not found: {db_path}"}

    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    cur = conn.cursor()

    report: dict = {
        "db_path": db_path,
        "audited_at": datetime.now().isoformat(),
        "tables": {},
        "orphans": {},
        "empty_fields": {},
    }

    # ── discover tables ──────────────────────────────────────────────────
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [r[0] for r in cur.fetchall()]
    report["table_names"] = tables

    for table in tables:
        cur.execute(f"SELECT COUNT(*) FROM [{table}]")
        row_count = cur.fetchone()[0]
        report["tables"][table] = {"row_count": row_count}

        if row_count == 0:
            continue

        # column info
        cur.execute(f"PRAGMA table_info('{table}')")
        cols = {r[1]: r[2] for r in cur.fetchall()}  # name -> type
        report["tables"][table]["columns"] = list(cols.keys())

        # empty / null field counts
        empty: dict[str, int] = {}
        for col_name in cols:
            cur.execute(
                f'SELECT COUNT(*) FROM [{table}] WHERE [{col_name}] IS NULL OR [{col_name}] = ""'
            )
            null_count = cur.fetchone()[0]
            if null_count > 0:
                empty[col_name] = null_count
        if empty:
            report["empty_fields"][table] = empty

    # ── orphan checks ────────────────────────────────────────────────────
    orphan_checks = [
        ("ingredients → recipes", "ingredients", "recipe_id", "recipes", "id"),
        ("steps → recipes", "steps", "recipe_id", "recipes", "id"),
        ("nutrition → recipes", "nutrition", "recipe_id", "recipes", "id"),
        ("recipe_tag → recipes", "recipe_tag", "recipe_id", "recipes", "id"),
        ("recipe_tag → tags", "recipe_tag", "tag_id", "tags", "id"),
    ]

    for label, child_table, fk_col, parent_table, pk_col in orphan_checks:
        if child_table not in tables or parent_table not in tables:
            continue
        cur.execute(
            f"SELECT COUNT(*) FROM [{child_table}] c "
            f"LEFT JOIN [{parent_table}] p ON c.[{fk_col}] = p.[{pk_col}] "
            f"WHERE p.[{pk_col}] IS NULL"
        )
        orphan_count = cur.fetchone()[0]
        report["orphans"][label] = orphan_count

    conn.close()
    return report


def print_report(report: dict) -> None:
    if "error" in report:
        print(f"ERROR: {report['error']}")
        return

    print(f"Database Audit Report")
    print(f"  Path:      {report['db_path']}")
    print(f"  Audited:   {report['audited_at']}")
    print()

    for table, info in report["tables"].items():
        print(f"  [{table}] — {info['row_count']} rows")

    if any(v for v in report["orphans"].values()):
        print(f"\n⚠ Orphan records found:")
        for label, count in report["orphans"].items():
            if count > 0:
                print(f"  {label}: {count} orphans")

    if report["empty_fields"]:
        print(f"\n⚠ Empty / NULL fields:")
        for table, fields in report["empty_fields"].items():
            for col, count in fields.items():
                print(f"  {table}.{col}: {count} rows")

    print("\n✓ Audit complete (read-only, no changes made).")


if __name__ == "__main__":
    db_path = sys.argv[1] if len(sys.argv) > 1 else "data/recipes.db"
    report = audit(db_path)
    print_report(report)
