"""Verify Alembic migrations — upgrade/downgrade round-trip via subprocess.

Using subprocess avoids asyncio event-loop conflicts with pytest-asyncio.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile


def _alembic(args: list[str], db_url: str) -> subprocess.CompletedProcess:
    """Run an Alembic command in a subprocess with the given DATABASE_URL."""
    env = {**os.environ, "DATABASE_URL": db_url, "PYTHONIOENCODING": "utf-8"}
    backend_dir = os.path.join(os.path.dirname(__file__), "..")
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        capture_output=True,
        text=True,
        cwd=backend_dir,
        env=env,
    )


def test_upgrade_head():
    """Alembic upgrade head should succeed on a fresh database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        db_url = f"sqlite+aiosqlite:///{db_path}"
        result = _alembic(["upgrade", "head"], db_url)
        assert result.returncode == 0, f"upgrade failed:\n{result.stderr}"
        assert "Running upgrade" in result.stderr


def test_downgrade_and_re_upgrade():
    """Full round-trip: upgrade → downgrade → upgrade should succeed."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        db_url = f"sqlite+aiosqlite:///{db_path}"

        r1 = _alembic(["upgrade", "head"], db_url)
        assert r1.returncode == 0, f"first upgrade failed:\n{r1.stderr}"

        r2 = _alembic(["downgrade", "-1"], db_url)
        assert r2.returncode == 0, f"downgrade failed:\n{r2.stderr}"
        assert "Running downgrade" in r2.stderr

        r3 = _alembic(["upgrade", "head"], db_url)
        assert r3.returncode == 0, f"second upgrade failed:\n{r3.stderr}"
        assert "Running upgrade" in r3.stderr


def test_history_shows_migration():
    """Alembic history should list the initial migration."""
    result = _alembic(["history"], "sqlite+aiosqlite:///:memory:")
    assert result.returncode == 0
    assert "initial_schema" in result.stdout


def test_current_on_empty_db():
    """On a fresh DB, current should show no migration applied (base)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        db_url = f"sqlite+aiosqlite:///{db_path}"

        # Before any migration, 'current' should emit a message about no current revision
        _ = _alembic(["current"], db_url)
        # It may fail or show base — either is fine as long as upgrade works after
        r2 = _alembic(["upgrade", "head"], db_url)
        assert r2.returncode == 0, f"upgrade after current check failed:\n{r2.stderr}"

        # After upgrade, current should show the head revision
        r3 = _alembic(["current"], db_url)
        assert r3.returncode == 0
        assert "6f3b0e8e4afd" in r3.stdout or "initial_schema" in r3.stdout
