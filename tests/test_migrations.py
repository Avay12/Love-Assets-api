"""The migration chain has to survive a database whose schema drifted ahead of it.

Two production incidents motivate this file:

* `payments` and `letters.user_id` reached the models without a migration, so
  `alembic upgrade head` built a schema the app could not run against.
* When the migration was finally written, the deploy failed with
  "column user_id of relation letters already exists" -- production had the
  column (left by an old `create_all`) while still stamped at the previous
  revision.

So the chain is exercised three ways: against an empty database, against a
drifted one, and twice in a row.

These run alembic as a subprocess, the same way the deploy does, because
settings are built once at import and the URL has to be set before that.
"""

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PREVIOUS_REVISION = "70e4c68333c6"
HEAD_REVISION = "b1c47a903de2"


def alembic(db_path: Path, *args: str) -> subprocess.CompletedProcess:
    env = {
        **os.environ,
        "DATABASE_URL": f"sqlite+aiosqlite:///{db_path.as_posix()}",
        "SECRET_KEY": "migration-test-key-that-is-at-least-32-bytes",
        "DEBUG": "False",
    }
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=PROJECT_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )


def upgrade(db_path: Path, target: str = "head") -> None:
    result = alembic(db_path, "upgrade", target)
    assert result.returncode == 0, f"alembic upgrade {target} failed:\n{result.stderr}"


def tables(db_path: Path) -> set[str]:
    with sqlite3.connect(db_path) as conn:
        return {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def columns(db_path: Path, table: str) -> set[str]:
    with sqlite3.connect(db_path) as conn:
        return {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}


def indexes(db_path: Path, table: str) -> set[str]:
    with sqlite3.connect(db_path) as conn:
        return {r[1] for r in conn.execute(f"PRAGMA index_list({table})")}


def stamped_revision(db_path: Path) -> str:
    with sqlite3.connect(db_path) as conn:
        return conn.execute("SELECT version_num FROM alembic_version").fetchone()[0]


@pytest.fixture
def db(tmp_path) -> Path:
    return tmp_path / "migration_test.db"


def test_chain_builds_a_complete_schema_from_empty(db):
    upgrade(db)

    assert {"users", "letters", "payments", "sessions", "oauth_identities", "templates"} <= tables(db)
    assert "user_id" in columns(db, "letters")
    assert stamped_revision(db) == HEAD_REVISION


def test_a_user_can_be_inserted_after_migrating(db):
    """The users migration hardcoded now(), which SQLite does not have, so a
    migrated database rejected the very first INSERT."""
    upgrade(db)

    with sqlite3.connect(db) as conn:
        conn.execute(
            "INSERT INTO users (name, email, timezone, role) VALUES (?, ?, ?, ?)",
            ("Alex", "alex@example.com", "UTC", "user"),
        )
        created_at = conn.execute("SELECT created_at FROM users").fetchone()[0]

    assert created_at is not None, "server_default did not populate created_at"


def test_upgrade_survives_a_schema_that_drifted_ahead(db):
    """Production's exact state: the column exists, the stamp does not."""
    upgrade(db, PREVIOUS_REVISION)
    with sqlite3.connect(db) as conn:
        conn.execute("ALTER TABLE letters ADD COLUMN user_id INTEGER")

    upgrade(db)

    assert "payments" in tables(db)
    assert "ix_letters_user_id" in indexes(db, "letters")
    assert stamped_revision(db) == HEAD_REVISION


def test_upgrade_survives_a_fully_drifted_schema(db):
    """Both the column and the table already present."""
    upgrade(db, PREVIOUS_REVISION)
    with sqlite3.connect(db) as conn:
        conn.execute("ALTER TABLE letters ADD COLUMN user_id INTEGER")
        conn.execute(
            """CREATE TABLE payments (
                id INTEGER PRIMARY KEY, payment_code VARCHAR(64) NOT NULL,
                user_id INTEGER, letter_id INTEGER, amount FLOAT NOT NULL,
                currency VARCHAR(8) NOT NULL, payment_method VARCHAR(32) NOT NULL,
                status VARCHAR(32) NOT NULL, created_at DATETIME NOT NULL)"""
        )

    upgrade(db)

    assert stamped_revision(db) == HEAD_REVISION
    assert "ix_payments_payment_code" in indexes(db, "payments")


def test_upgrade_head_is_a_no_op_when_already_current(db):
    upgrade(db)
    upgrade(db)  # the deploy runs this on every push

    assert stamped_revision(db) == HEAD_REVISION


def test_downgrade_then_upgrade_round_trips(db):
    upgrade(db)

    result = alembic(db, "downgrade", "-1")
    assert result.returncode == 0, result.stderr
    assert "payments" not in tables(db)
    assert "user_id" not in columns(db, "letters")

    upgrade(db)
    assert "payments" in tables(db)
    assert "user_id" in columns(db, "letters")
