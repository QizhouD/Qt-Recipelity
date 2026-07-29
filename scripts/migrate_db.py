"""Idempotent migration: copy data from a legacy SQLite database to a target DB.

Usage:
    python scripts/migrate_db.py SOURCE_SQLITE_DB --target DATABASE_URL [--dry-run]

Requirements:
- source must be a read-only SQLite file path.
- target must be a SQLAlchemy (async) database URL (mysql+asyncmy, sqlite+aiosqlite, …).
- target schema MUST already exist (created by ``alembic upgrade head``).
  This script does NOT create tables — it only inserts data.
- Idempotent: re-running does not create duplicate rows (dedup by recipe name + source_url).
- Pre- and post-migration counts are printed for recipes, ingredients, steps, nutrition,
  tags, and the recipe_tag join table.

Safe migration paths:
  A. (Recommended)  alembic upgrade head → fresh MySQL, then run this script.
  B. (Existing DB)  verify schema, ``alembic stamp head``, then run this script.
  Always back up the original SQLite file before migrating.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sqlite3
import sys
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


# ── helpers ──────────────────────────────────────────────────────────────────

def _count_sqlite(cursor: sqlite3.Cursor, table: str) -> int:
    """Return row count for *table* (0 if it doesn't exist)."""
    try:
        return cursor.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    except sqlite3.OperationalError:
        return 0


async def _count_target(session: AsyncSession, table: str) -> int:
    """Return row count for *table* in the target database."""
    result = await session.execute(text(f"SELECT COUNT(*) FROM {table}"))
    return result.scalar() or 0


async def _count_tag_links(session: AsyncSession) -> int:
    """Return row count for recipe_tag join table."""
    result = await session.execute(text("SELECT COUNT(*) FROM recipe_tag"))
    return result.scalar() or 0


def _format_count(label: str, before: int, after: int) -> str:
    delta = after - before
    sign = "+" if delta >= 0 else ""
    return f"  {label:20s}  {before:>5d}  →  {after:>5d}  ({sign}{delta})"


# ── core migration logic ─────────────────────────────────────────────────────


async def migrate(  # noqa: C901, PLR0912, PLR0915
    source_path: str,
    target_url: str,
    *,
    dry_run: bool = False,
) -> dict:
    """Copy recipes (and related rows) from *source_path* to *target_url*.

    Returns a report dict with keys: source, target, errors, counts_before,
    counts_after, recipes_migrated, recipes_skipped, ingredients_migrated,
    steps_migrated, nutrition_migrated, tags_linked.
    """

    report: dict = {
        "source": source_path,
        "target": target_url if not dry_run else "(dry-run)",
        "errors": [],
        "counts_before": {},
        "counts_after": {},
        "recipes_migrated": 0,
        "recipes_skipped": 0,
        "ingredients_migrated": 0,
        "steps_migrated": 0,
        "nutrition_migrated": 0,
        "tags_linked": 0,
    }

    # ── validate source ──────────────────────────────────────────────────
    if not os.path.exists(source_path):
        return {**report, "errors": [f"Source database not found: {source_path}"]}

    src = sqlite3.connect(f"file:{source_path}?mode=ro", uri=True)
    src.row_factory = sqlite3.Row

    # Discover source tables
    src_tables = {r[0] for r in src.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    )}
    required = {"recipes", "ingredients", "steps", "tags", "recipe_tag"}
    missing = required - src_tables
    if "recipes" not in src_tables:
        src.close()
        return {**report, "errors": ["Source has no 'recipes' table"]}
    if missing:
        report.setdefault("warnings", []).append(
            f"Source missing tables: {', '.join(sorted(missing))}"
        )

    # Pre-migration source counts
    src_counts = {
        "recipes": _count_sqlite(src, "recipes"),
        "ingredients": _count_sqlite(src, "ingredients"),
        "steps": _count_sqlite(src, "steps"),
        "nutrition": _count_sqlite(src, "nutrition"),
        "tags": _count_sqlite(src, "tags"),
        "recipe_tag": _count_sqlite(src, "recipe_tag"),
    }

    # ── connect to target ────────────────────────────────────────────────
    engine = None
    session_factory = None

    if not dry_run:
        engine = create_async_engine(target_url, echo=False)
        session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        # Pre-migration target counts
        if session_factory:
            async with session_factory() as session:
                report["counts_before"] = {
                    "recipes": await _count_target(session, "recipes"),
                    "ingredients": await _count_target(session, "ingredients"),
                    "steps": await _count_target(session, "steps"),
                    "nutrition": await _count_target(session, "nutrition"),
                    "tags": await _count_target(session, "tags"),
                    "recipe_tag": await _count_tag_links(session),
                }
        else:
            report["counts_before"] = {k: 0 for k in src_counts}

        # ── migrate recipes ──────────────────────────────────────────────
        src_recipes = src.execute("SELECT * FROM recipes").fetchall()

        for row in src_recipes:
            rowd = dict(row)
            src_rid = rowd["id"]

            # Dedup: same name + source_url → skip
            if not dry_run and session_factory:
                async with session_factory() as session:
                    result = await session.execute(
                        text(
                            "SELECT id FROM recipes WHERE name=:name "
                            "AND (source_url=:url OR (source_url IS NULL AND :url2 IS NULL))"
                        ),
                        {
                            "name": rowd.get("name"),
                            "url": rowd.get("source_url"),
                            "url2": rowd.get("source_url"),
                        },
                    )
                    if result.first():
                        report["recipes_skipped"] += 1
                        continue

            if dry_run:
                report["recipes_migrated"] += 1
                # Dry-run: still count what would be migrated
                if "ingredients" in src_tables:
                    ing_count = src.execute(
                        "SELECT COUNT(*) FROM ingredients WHERE recipe_id=?", (src_rid,)
                    ).fetchone()[0]
                    report["ingredients_migrated"] += ing_count
                if "steps" in src_tables:
                    step_count = src.execute(
                        "SELECT COUNT(*) FROM steps WHERE recipe_id=?", (src_rid,)
                    ).fetchone()[0]
                    report["steps_migrated"] += step_count
                if "nutrition" in src_tables:
                    nut = src.execute(
                        "SELECT 1 FROM nutrition WHERE recipe_id=?", (src_rid,)
                    ).fetchone()
                    if nut:
                        report["nutrition_migrated"] += 1
                if "tags" in src_tables and "recipe_tag" in src_tables:
                    tag_count = src.execute(
                        "SELECT COUNT(*) FROM recipe_tag WHERE recipe_id=?", (src_rid,)
                    ).fetchone()[0]
                    report["tags_linked"] += tag_count
                continue

            # ── insert recipe ────────────────────────────────────────────
            async with session_factory() as session:
                result = await session.execute(
                    text(
                        """INSERT INTO recipes
                           (name, description, prep_time, cook_time, difficulty,
                            cuisine, image_url, source_url, created_at, updated_at)
                           VALUES
                           (:name, :desc, :prep, :cook, :diff,
                            :cuisine, :img, :src_url, :created, :updated)"""
                    ),
                    {
                        "name": rowd.get("name"),
                        "desc": rowd.get("description"),
                        "prep": rowd.get("prep_time"),
                        "cook": rowd.get("cook_time"),
                        "diff": rowd.get("difficulty"),
                        "cuisine": rowd.get("cuisine"),
                        "img": rowd.get("image_url"),
                        "src_url": rowd.get("source_url"),
                        "created": rowd.get("created_at") or datetime.now().isoformat(),
                        "updated": rowd.get("updated_at") or datetime.now().isoformat(),
                    },
                )
                new_id = result.lastrowid
                report["recipes_migrated"] += 1

                # ── ingredients ──────────────────────────────────────────
                if "ingredients" in src_tables:
                    for ing in src.execute(
                        "SELECT * FROM ingredients WHERE recipe_id=?", (src_rid,)
                    ):
                        await session.execute(
                            text(
                                "INSERT INTO ingredients (name, amount, unit, recipe_id) "
                                "VALUES (:name, :amount, :unit, :rid)"
                            ),
                            {"name": ing["name"], "amount": ing["amount"],
                             "unit": ing["unit"], "rid": new_id},
                        )
                        report["ingredients_migrated"] += 1

                # ── steps ────────────────────────────────────────────────
                if "steps" in src_tables:
                    for step in src.execute(
                        "SELECT * FROM steps WHERE recipe_id=? ORDER BY \"order\"",
                        (src_rid,),
                    ):
                        await session.execute(
                            text(
                                "INSERT INTO steps (\"order\", description, recipe_id) "
                                "VALUES (:order, :desc, :rid)"
                            ),
                            {"order": step["order"], "desc": step["description"],
                             "rid": new_id},
                        )
                        report["steps_migrated"] += 1

                # ── nutrition ────────────────────────────────────────────
                if "nutrition" in src_tables:
                    nut = src.execute(
                        "SELECT * FROM nutrition WHERE recipe_id=?", (src_rid,)
                    ).fetchone()
                    if nut:
                        await session.execute(
                            text(
                                """INSERT INTO nutrition
                                   (calories, protein, fat, carbohydrates, fiber,
                                    sugar, sodium, source, recipe_id)
                                   VALUES
                                   (:cal, :pro, :fat, :carbs, :fiber,
                                    :sugar, :sodium, :source, :rid)"""
                            ),
                            {
                                "cal": nut["calories"], "pro": nut["protein"],
                                "fat": nut["fat"], "carbs": nut["carbohydrates"],
                                "fiber": nut["fiber"], "sugar": nut["sugar"],
                                "sodium": nut["sodium"], "source": "migrated",
                                "rid": new_id,
                            },
                        )
                        report["nutrition_migrated"] += 1

                # ── tags ─────────────────────────────────────────────────
                if "tags" in src_tables and "recipe_tag" in src_tables:
                    tag_rows = src.execute(
                        """SELECT t.* FROM tags t
                           JOIN recipe_tag rt ON t.id = rt.tag_id
                           WHERE rt.recipe_id = ?""",
                        (src_rid,),
                    ).fetchall()
                    for tag in tag_rows:
                        # Upsert tag by name
                        await session.execute(
                            text(
                                "INSERT INTO tags (name) VALUES (:name) "
                                "ON DUPLICATE KEY UPDATE name=name"
                                if "mysql" in target_url
                                else "INSERT OR IGNORE INTO tags (name) VALUES (:name)"
                            ),
                            {"name": tag["name"]},
                        )
                        # Get tag id
                        tag_result = await session.execute(
                            text("SELECT id FROM tags WHERE name=:name"),
                            {"name": tag["name"]},
                        )
                        tag_row = tag_result.first()
                        if not tag_row:
                            # Try again — MySQL ON DUPLICATE KEY UPDATE doesn't
                            # return the existing id; re-query
                            tag_result = await session.execute(
                                text("SELECT id FROM tags WHERE name=:name"),
                                {"name": tag["name"]},
                            )
                            tag_row = tag_result.first()
                        if tag_row:
                            tag_id = tag_row[0]
                            # Insert recipe_tag link (ignore duplicates)
                            try:
                                await session.execute(
                                    text(
                                        "INSERT INTO recipe_tag (recipe_id, tag_id) "
                                        "VALUES (:rid, :tid)"
                                        + (
                                            " ON DUPLICATE KEY UPDATE recipe_id=recipe_id"
                                            if "mysql" in target_url
                                            else ""
                                        )
                                    ),
                                    {"rid": new_id, "tid": tag_id},
                                )
                                report["tags_linked"] += 1
                            except Exception:
                                # Duplicate link — safe to ignore
                                pass

                await session.commit()

        # ── post-migration counts ────────────────────────────────────────
        if session_factory:
            async with session_factory() as session:
                report["counts_after"] = {
                    "recipes": await _count_target(session, "recipes"),
                    "ingredients": await _count_target(session, "ingredients"),
                    "steps": await _count_target(session, "steps"),
                    "nutrition": await _count_target(session, "nutrition"),
                    "tags": await _count_target(session, "tags"),
                    "recipe_tag": await _count_tag_links(session),
                }
        else:
            # Dry-run: estimate after = before + migrated
            report["counts_after"] = {
                "recipes": report["recipes_migrated"],
                "ingredients": report["ingredients_migrated"],
                "steps": report["steps_migrated"],
                "nutrition": report["nutrition_migrated"],
                "tags": report["tags_linked"],
                "recipe_tag": report["tags_linked"],
            }

    except Exception as exc:
        report["errors"].append(str(exc))
    finally:
        src.close()
        if engine:
            await engine.dispose()

    # Attach source counts for reporting
    report["counts_source"] = src_counts
    return report


# ── CLI ──────────────────────────────────────────────────────────────────────


def print_counts(title: str, counts: dict) -> None:
    print(f"  {title}:")
    if counts:
        for table in ["recipes", "ingredients", "steps", "nutrition", "tags", "recipe_tag"]:
            print(f"    {table:20s} = {counts.get(table, '?'):>5}")
    else:
        print("    (not available)")


def main():
    parser = argparse.ArgumentParser(
        description="Migrate legacy SQLite recipe data to a target database "
                    "(schema must already exist via alembic upgrade head)."
    )
    parser.add_argument(
        "source",
        help="Path to source SQLite database (read-only)",
    )
    parser.add_argument(
        "--target",
        required=True,
        help="Target database URL (mysql+asyncmy://…, sqlite+aiosqlite://…, etc.)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be migrated without writing to the target",
    )
    args = parser.parse_args()

    if not os.path.exists(args.source):
        print(f"ERROR: Source database not found: {args.source}")
        sys.exit(1)

    print(f"Source : {args.source}")
    print(f"Target : {args.target if not args.dry_run else '(dry-run)'}")
    print()

    report = asyncio.run(migrate(args.source, args.target, dry_run=args.dry_run))

    if report.get("warnings"):
        for w in report["warnings"]:
            print(f"WARNING: {w}")

    if report.get("errors"):
        for e in report["errors"]:
            print(f"ERROR: {e}")
        sys.exit(1)

    # ── counts summary ──────────────────────────────────────────────────
    print("── Counts ──")
    if "counts_source" in report:
        print_counts("Source (SQLite)", report["counts_source"])
    print_counts("Target (before)", report["counts_before"])
    print()
    print(f"  Recipes migrated:    {report['recipes_migrated']:>5}")
    print(f"  Recipes skipped:     {report['recipes_skipped']:>5}")
    print(f"  Ingredients copied:  {report['ingredients_migrated']:>5}")
    print(f"  Steps copied:        {report['steps_migrated']:>5}")
    print(f"  Nutrition rows:      {report['nutrition_migrated']:>5}")
    print(f"  Tag links created:   {report['tags_linked']:>5}")
    print()
    print_counts("Target (after)", report["counts_after"])
    print()
    print("Done.")


if __name__ == "__main__":
    main()
