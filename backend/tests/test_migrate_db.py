"""Integration tests for scripts/migrate_db.py — SQLite → SQLite.

These tests verify the migration logic using a pair of temporary SQLite databases.
MySQL-specific tests can be layered on when a MySQL instance is available.
"""

from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
import tempfile

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.db.session import Base

# ── helpers ──────────────────────────────────────────────────────────────────

def _create_source_db(path: str) -> None:
    """Create a source SQLite DB with sample legacy data."""
    conn = sqlite3.connect(path)
    conn.executescript("""
        CREATE TABLE recipes (
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
        CREATE TABLE ingredients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(100) NOT NULL,
            amount FLOAT,
            unit VARCHAR(50),
            recipe_id INTEGER REFERENCES recipes(id) ON DELETE CASCADE
        );
        CREATE TABLE steps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            "order" INTEGER NOT NULL,
            description TEXT NOT NULL,
            recipe_id INTEGER REFERENCES recipes(id) ON DELETE CASCADE
        );
        CREATE TABLE nutrition (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            calories FLOAT, protein FLOAT, fat FLOAT,
            carbohydrates FLOAT, fiber FLOAT, sugar FLOAT, sodium FLOAT,
            source VARCHAR(100) DEFAULT 'manual',
            calculated_at DATETIME,
            recipe_id INTEGER UNIQUE REFERENCES recipes(id) ON DELETE CASCADE
        );
        CREATE TABLE tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(50) UNIQUE NOT NULL
        );
        CREATE TABLE recipe_tag (
            recipe_id INTEGER REFERENCES recipes(id) ON DELETE CASCADE,
            tag_id INTEGER REFERENCES tags(id) ON DELETE CASCADE,
            PRIMARY KEY (recipe_id, tag_id)
        );

        -- Recipe 1: full data
        INSERT INTO recipes
            (name, description, prep_time, cook_time, difficulty, cuisine, source_url)
        VALUES
            ('Test Recipe 1', 'Description 1', 10, 20, 2, 'Chinese', 'http://example.com/1');
        INSERT INTO ingredients (name, amount, unit, recipe_id)
        VALUES ('Ingredient A', 100, 'g', 1);
        INSERT INTO ingredients (name, amount, unit, recipe_id)
        VALUES ('Ingredient B', 2, 'piece', 1);
        INSERT INTO steps ("order", description, recipe_id) VALUES (1, 'Step 1', 1);
        INSERT INTO steps ("order", description, recipe_id) VALUES (2, 'Step 2', 1);
        INSERT INTO nutrition (calories, protein, fat, carbohydrates, recipe_id)
        VALUES (200, 10, 5, 30, 1);
        INSERT INTO tags (name) VALUES ('Quick');
        INSERT INTO tags (name) VALUES ('Healthy');
        INSERT INTO recipe_tag (recipe_id, tag_id) VALUES (1, 1);
        INSERT INTO recipe_tag (recipe_id, tag_id) VALUES (1, 2);

        -- Recipe 2: minimal data (no nutrition)
        INSERT INTO recipes (name, description, prep_time, cook_time, cuisine)
        VALUES ('Test Recipe 2', 'Description 2', 5, 15, 'Italian');
        INSERT INTO ingredients (name, amount, unit, recipe_id)
        VALUES ('Ingredient C', 50, 'ml', 2);
        INSERT INTO steps ("order", description, recipe_id) VALUES (1, 'Step A', 2);
        INSERT INTO tags (name) VALUES ('Pasta');
        INSERT INTO recipe_tag (recipe_id, tag_id) VALUES (2, 3);
    """)
    conn.commit()
    conn.close()


async def _create_target_tables(db_url: str) -> None:
    """Create Alembic-compatible schema in the target DB."""
    engine = create_async_engine(db_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()


async def _count_all(db_url: str) -> dict:
    """Return row counts for all key tables."""
    engine = create_async_engine(db_url, echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        counts = {}
        for table in ["recipes", "ingredients", "steps", "nutrition", "tags", "recipe_tag"]:
            result = await session.execute(text(f"SELECT COUNT(*) FROM {table}"))
            counts[table] = result.scalar() or 0
    await engine.dispose()
    return counts


def _run_migrate(
    source: str, target_url: str, dry_run: bool = False
) -> subprocess.CompletedProcess:
    """Run migrate_db.py as a subprocess."""
    scripts_dir = os.path.join(os.path.dirname(__file__), "..", "..", "scripts")
    script_path = os.path.join(scripts_dir, "migrate_db.py")
    cmd = [sys.executable, script_path, source, "--target", target_url]
    if dry_run:
        cmd.append("--dry-run")
    return subprocess.run(cmd, capture_output=True, text=True, cwd=scripts_dir)


# ── tests ────────────────────────────────────────────────────────────────────


class TestMigrateDb:
    """SQLite → SQLite migration tests using the migrate() function directly."""

    @pytest.mark.asyncio
    async def test_migrate_basic(self):
        """Full migration: source → target, verify data integrity."""
        with tempfile.TemporaryDirectory() as tmpdir:
            src_path = os.path.join(tmpdir, "source.db")
            tgt_path = os.path.join(tmpdir, "target.db")
            tgt_url = f"sqlite+aiosqlite:///{tgt_path}"

            _create_source_db(src_path)
            await _create_target_tables(tgt_url)

            # Import the migrate function (lazy to avoid side effects at import)
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))
            from migrate_db import migrate  # type: ignore[import-not-found]

            # ── first run ────────────────────────────────────────────────
            report = await migrate(src_path, tgt_url, dry_run=False)
            assert report["recipes_migrated"] == 2
            assert report["recipes_skipped"] == 0
            assert report["ingredients_migrated"] == 3
            assert report["steps_migrated"] == 3
            assert report["nutrition_migrated"] == 1
            assert report["tags_linked"] == 3
            assert not report["errors"]

            # Verify target counts
            counts = await _count_all(tgt_url)
            assert counts["recipes"] == 2
            assert counts["ingredients"] == 3
            assert counts["steps"] == 3
            assert counts["nutrition"] == 1
            assert counts["tags"] == 3
            assert counts["recipe_tag"] == 3

            # ── second run (idempotent) ──────────────────────────────────
            report2 = await migrate(src_path, tgt_url, dry_run=False)
            assert report2["recipes_migrated"] == 0
            assert report2["recipes_skipped"] == 2
            assert report2["ingredients_migrated"] == 0
            assert report2["steps_migrated"] == 0
            assert report2["nutrition_migrated"] == 0
            assert report2["tags_linked"] == 0

            # Counts unchanged
            counts2 = await _count_all(tgt_url)
            assert counts2 == counts

    @pytest.mark.asyncio
    async def test_dry_run_does_not_write(self):
        """Dry-run should report counts but not write any data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            src_path = os.path.join(tmpdir, "source.db")
            tgt_path = os.path.join(tmpdir, "target.db")
            tgt_url = f"sqlite+aiosqlite:///{tgt_path}"

            _create_source_db(src_path)
            await _create_target_tables(tgt_url)

            sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))
            from migrate_db import migrate  # type: ignore[import-not-found]

            report = await migrate(src_path, tgt_url, dry_run=True)
            assert report["recipes_migrated"] == 2
            assert report["recipes_skipped"] == 0
            assert not report["errors"]

            # Target should be empty
            counts = await _count_all(tgt_url)
            assert counts["recipes"] == 0
            assert counts["ingredients"] == 0
            assert counts["steps"] == 0
            assert counts["nutrition"] == 0
            assert counts["tags"] == 0
            assert counts["recipe_tag"] == 0

    @pytest.mark.asyncio
    async def test_missing_source(self):
        """Graceful error when source DB does not exist."""
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))
        from migrate_db import migrate  # type: ignore[import-not-found]

        report = await migrate("/nonexistent/path.db", "sqlite+aiosqlite:///tmp.db")
        assert report["errors"]
        assert "not found" in report["errors"][0].lower()


class TestMigrateDbCli:
    """End-to-end tests via subprocess (CLI)."""

    def test_cli_basic(self):
        """Full CLI migration with --target and verify with --dry-run first."""
        with tempfile.TemporaryDirectory() as tmpdir:
            src_path = os.path.join(tmpdir, "source.db")
            tgt_path = os.path.join(tmpdir, "target.db")
            tgt_url = f"sqlite+aiosqlite:///{tgt_path}"

            _create_source_db(src_path)

            # Create target schema via Alembic-compatible approach (Base.metadata.create_all)
            import asyncio
            asyncio.run(_create_target_tables(tgt_url))

            # ── dry-run ─────────────────────────────────────────────────
            result = _run_migrate(src_path, tgt_url, dry_run=True)
            assert result.returncode == 0, f"dry-run failed:\n{result.stderr}"
            assert "Recipes migrated:" in result.stdout

            # ── actual run ──────────────────────────────────────────────
            result = _run_migrate(src_path, tgt_url, dry_run=False)
            assert result.returncode == 0, f"migrate failed:\n{result.stderr}"
            assert "Recipes migrated:" in result.stdout
            assert "Done." in result.stdout

            # ── re-run (idempotent) ─────────────────────────────────────
            result2 = _run_migrate(src_path, tgt_url, dry_run=False)
            assert result2.returncode == 0, f"re-run failed:\n{result2.stderr}"
            assert "Recipes skipped:" in result2.stdout

            # ── verify counts in target ─────────────────────────────────
            counts = asyncio.run(_count_all(tgt_url))
            assert counts["recipes"] == 2
            assert counts["ingredients"] == 3
            assert counts["steps"] == 3
            assert counts["nutrition"] == 1
            assert counts["tags"] == 3
            assert counts["recipe_tag"] == 3

    def test_missing_source_cli(self):
        """CLI exits with error when source is missing."""
        result = _run_migrate("/nonexistent/path.db", "sqlite+aiosqlite:///tmp.db")
        assert result.returncode != 0
        assert "ERROR" in result.stdout
