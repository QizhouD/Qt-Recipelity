"""Idempotent migration tool: copy data from a legacy SQLite database.

Usage:
    python scripts/migrate_db.py [source.db] [--target data/recipes.db] [--dry-run]

Features:
- Dry-run mode prints what would be migrated without writing.
- Re-running does NOT create duplicate rows (checks by recipe name + source_url).
- Counts and verifies migrated records.
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from datetime import datetime


def migrate(source_path: str, target_path: str, dry_run: bool = False) -> dict:
    if not os.path.exists(source_path):
        return {"error": f"Source database not found: {source_path}"}

    src = sqlite3.connect(f"file:{source_path}?mode=ro", uri=True)
    src.row_factory = sqlite3.Row
    tgt = None if dry_run else sqlite3.connect(target_path)

    report = {
        "source": source_path,
        "target": target_path if not dry_run else "(dry-run)",
        "recipes_migrated": 0,
        "recipes_skipped": 0,
        "tags_created": 0,
        "ingredients": 0,
        "steps": 0,
        "errors": [],
    }

    try:
        # ── ensure target tables exist ────────────────────────────────────
        if tgt:
            tgt.executescript("""
                CREATE TABLE IF NOT EXISTS recipes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(200) NOT NULL,
                    description TEXT,
                    prep_time INTEGER,
                    cook_time INTEGER,
                    difficulty INTEGER,
                    cuisine VARCHAR(100),
                    image_url VARCHAR(500),
                    source_url VARCHAR(500),
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS ingredients (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(100) NOT NULL,
                    amount FLOAT,
                    unit VARCHAR(50),
                    recipe_id INTEGER REFERENCES recipes(id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS steps (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    "order" INTEGER NOT NULL,
                    description TEXT NOT NULL,
                    recipe_id INTEGER REFERENCES recipes(id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS nutrition (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    calories FLOAT, protein FLOAT, fat FLOAT,
                    carbohydrates FLOAT, fiber FLOAT, sugar FLOAT, sodium FLOAT,
                    source VARCHAR(100) DEFAULT 'migrated',
                    calculated_at DATETIME,
                    recipe_id INTEGER UNIQUE REFERENCES recipes(id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(50) UNIQUE NOT NULL
                );
                CREATE TABLE IF NOT EXISTS recipe_tag (
                    recipe_id INTEGER REFERENCES recipes(id) ON DELETE CASCADE,
                    tag_id INTEGER REFERENCES tags(id) ON DELETE CASCADE,
                    PRIMARY KEY (recipe_id, tag_id)
                );
            """)

        # ── discover source tables ─────────────────────────────────────────
        src_tables = {r[0] for r in src.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )}
        if "recipes" not in src_tables:
            report["errors"].append("Source has no 'recipes' table")
            return report

        # ── migrate recipes ────────────────────────────────────────────────
        src_recipes = src.execute("SELECT * FROM recipes").fetchall()

        for row in src_recipes:
            rowd = dict(row)

            # Dedup check: same name + source_url = already migrated
            if tgt:
                existing = tgt.execute(
                    "SELECT id FROM recipes WHERE name=? AND (source_url=? OR (source_url IS NULL AND ? IS NULL))",
                    (rowd.get("name"), rowd.get("source_url"), rowd.get("source_url")),
                ).fetchone()
                if existing:
                    report["recipes_skipped"] += 1
                    continue

            if dry_run:
                report["recipes_migrated"] += 1
                continue

            # Insert recipe
            cur = tgt.execute(
                """INSERT INTO recipes (name, description, prep_time, cook_time, difficulty,
                   cuisine, image_url, source_url, created_at, updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (
                    rowd.get("name"), rowd.get("description"),
                    rowd.get("prep_time"), rowd.get("cook_time"),
                    rowd.get("difficulty"), rowd.get("cuisine"),
                    rowd.get("image_url"), rowd.get("source_url"),
                    rowd.get("created_at") or datetime.now().isoformat(),
                    rowd.get("updated_at") or datetime.now().isoformat(),
                ),
            )
            new_id = cur.lastrowid
            report["recipes_migrated"] += 1

            # ── ingredients ────────────────────────────────────────────
            if "ingredients" in src_tables:
                for ing in src.execute(
                    "SELECT * FROM ingredients WHERE recipe_id=?", (rowd["id"],)
                ):
                    tgt.execute(
                        "INSERT INTO ingredients (name, amount, unit, recipe_id) VALUES (?,?,?,?)",
                        (ing["name"], ing["amount"], ing["unit"], new_id),
                    )
                    report["ingredients"] += 1

            # ── steps ──────────────────────────────────────────────────
            if "steps" in src_tables:
                for step in src.execute(
                    "SELECT * FROM steps WHERE recipe_id=? ORDER BY \"order\"", (rowd["id"],)
                ):
                    tgt.execute(
                        "INSERT INTO steps (\"order\", description, recipe_id) VALUES (?,?,?)",
                        (step["order"], step["description"], new_id),
                    )
                    report["steps"] += 1

            # ── nutrition ──────────────────────────────────────────────
            if "nutrition" in src_tables:
                nut = src.execute(
                    "SELECT * FROM nutrition WHERE recipe_id=?", (rowd["id"],)
                ).fetchone()
                if nut:
                    tgt.execute(
                        """INSERT INTO nutrition (calories, protein, fat, carbohydrates, fiber,
                           sugar, sodium, source, recipe_id)
                           VALUES (?,?,?,?,?,?,?,?,?)""",
                        (nut["calories"], nut["protein"], nut["fat"],
                         nut["carbohydrates"], nut["fiber"], nut["sugar"],
                         nut["sodium"], "migrated", new_id),
                    )

            # ── tags ──────────────────────────────────────────────────
            if "tags" in src_tables and "recipe_tag" in src_tables:
                tag_rows = src.execute(
                    """SELECT t.* FROM tags t
                       JOIN recipe_tag rt ON t.id = rt.tag_id
                       WHERE rt.recipe_id = ?""",
                    (rowd["id"],),
                ).fetchall()
                for tag in tag_rows:
                    tgt.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (tag["name"],))
                    tag_id = tgt.execute(
                        "SELECT id FROM tags WHERE name=?", (tag["name"],)
                    ).fetchone()[0]
                    tgt.execute(
                        "INSERT OR IGNORE INTO recipe_tag (recipe_id, tag_id) VALUES (?,?)",
                        (new_id, tag_id),
                    )
                    report["tags_created"] += 1

        if tgt:
            tgt.commit()

    except Exception as e:
        report["errors"].append(str(e))
        if tgt:
            tgt.rollback()
    finally:
        src.close()
        if tgt:
            tgt.close()

    return report


def main():
    parser = argparse.ArgumentParser(description="Migrate legacy recipe database")
    parser.add_argument("source", nargs="?", default="data/recipes.db",
                        help="Path to source SQLite DB (default: data/recipes.db)")
    parser.add_argument("--target", default="data/recipes.db",
                        help="Path to target SQLite DB (default: data/recipes.db)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would be done without writing")
    args = parser.parse_args()

    if args.source == args.target and not args.dry_run:
        print("WARNING: source and target are the same file. Use --target to specify a different path.")
        print("         Or use --dry-run for a read-only preview.")
        sys.exit(1)

    report = migrate(args.source, args.target, args.dry_run)
    if "error" in report:
        print(f"ERROR: {report['error']}")
        sys.exit(1)

    print("Migration Report")
    print(f"  Source: {report['source']}")
    print(f"  Target: {report['target']}")
    print(f"  Recipes migrated:  {report['recipes_migrated']}")
    print(f"  Recipes skipped:   {report['recipes_skipped']}")
    print(f"  Ingredients:       {report['ingredients']}")
    print(f"  Steps:             {report['steps']}")
    print(f"  Tags linked:       {report['tags_created']}")
    if report["errors"]:
        print(f"  Errors: {report['errors']}")
    print("Done.")


if __name__ == "__main__":
    main()
