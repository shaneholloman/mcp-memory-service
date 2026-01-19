"""Unit tests for MigrationRunner.

Tests the SQL migration execution utility for both synchronous and
asynchronous database connections.
"""

import sqlite3
from pathlib import Path

import aiosqlite
import pytest

from mcp_memory_service.storage.migration_runner import MigrationRunner


@pytest.mark.unit
def test_migration_runner_sync_executes_sql_files(tmp_path):
    """Test that migration runner executes SQL files synchronously."""
    # Setup: Create test migration file
    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir()

    test_migration = migrations_dir / "001_test.sql"
    test_migration.write_text(
        "CREATE TABLE IF NOT EXISTS test_table (id INTEGER PRIMARY KEY);"
    )

    # Create test database
    db_path = tmp_path / "test.db"

    # Execute migration using sync connection
    conn = sqlite3.connect(db_path)
    try:
        runner = MigrationRunner(migrations_dir)
        success, message = runner.run_migrations_sync(conn, ["001_test.sql"])

        # Verify success
        assert success
        assert "Successfully executed 1 migrations" in message

        # Verify table was created
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='test_table'"
        )
        result = cursor.fetchone()
        assert result is not None
        assert result[0] == "test_table"
    finally:
        conn.close()


@pytest.mark.asyncio
async def test_migration_runner_async_executes_sql_files(tmp_path):
    """Test that migration runner executes SQL files asynchronously."""
    # Setup: Create test migration file
    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir()

    test_migration = migrations_dir / "001_test.sql"
    test_migration.write_text(
        "CREATE TABLE IF NOT EXISTS test_table (id INTEGER PRIMARY KEY);"
    )

    # Create test database
    db_path = tmp_path / "test.db"

    # Execute migration
    runner = MigrationRunner(migrations_dir)
    success, message = await runner.run_migrations_async(str(db_path), ["001_test.sql"])

    # Verify success
    assert success
    assert "Successfully executed 1 migrations" in message

    # Verify table was created
    async with aiosqlite.connect(db_path) as conn:
        cursor = await conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='test_table'"
        )
        result = await cursor.fetchone()
        assert result is not None
        assert result[0] == "test_table"


@pytest.mark.unit
def test_migration_runner_sync_multiple_files(tmp_path):
    """Test that migration runner executes multiple files in order."""
    # Setup: Create multiple migration files
    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir()

    # Create migrations in non-sorted order to test sorting
    (migrations_dir / "002_second.sql").write_text(
        "CREATE TABLE IF NOT EXISTS second_table (id INTEGER);"
    )
    (migrations_dir / "001_first.sql").write_text(
        "CREATE TABLE IF NOT EXISTS first_table (id INTEGER);"
    )

    # Create test database
    db_path = tmp_path / "test.db"

    # Execute migrations (should be sorted automatically)
    conn = sqlite3.connect(db_path)
    try:
        runner = MigrationRunner(migrations_dir)
        success, message = runner.run_migrations_sync(
            conn, ["002_second.sql", "001_first.sql"]
        )

        # Verify success
        assert success
        assert "Successfully executed 2 migrations" in message

        # Verify both tables were created
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        results = cursor.fetchall()
        table_names = [row[0] for row in results]
        assert "first_table" in table_names
        assert "second_table" in table_names
    finally:
        conn.close()


@pytest.mark.asyncio
async def test_migration_runner_async_multiple_files(tmp_path):
    """Test that migration runner executes multiple files in order asynchronously."""
    # Setup: Create multiple migration files
    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir()

    (migrations_dir / "002_second.sql").write_text(
        "CREATE TABLE IF NOT EXISTS second_table (id INTEGER);"
    )
    (migrations_dir / "001_first.sql").write_text(
        "CREATE TABLE IF NOT EXISTS first_table (id INTEGER);"
    )

    # Create test database
    db_path = tmp_path / "test.db"

    # Execute migrations
    runner = MigrationRunner(migrations_dir)
    success, message = await runner.run_migrations_async(
        str(db_path), ["002_second.sql", "001_first.sql"]
    )

    # Verify success
    assert success
    assert "Successfully executed 2 migrations" in message

    # Verify both tables were created
    async with aiosqlite.connect(db_path) as conn:
        cursor = await conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        results = await cursor.fetchall()
        table_names = [row[0] for row in results]
        assert "first_table" in table_names
        assert "second_table" in table_names


@pytest.mark.unit
def test_migration_runner_sync_missing_file(tmp_path):
    """Test that migration runner handles missing files gracefully."""
    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir()

    # Create only one migration file
    (migrations_dir / "001_exists.sql").write_text(
        "CREATE TABLE IF NOT EXISTS exists_table (id INTEGER);"
    )

    # Try to run with a missing file
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(db_path)
    try:
        runner = MigrationRunner(migrations_dir)
        success, message = runner.run_migrations_sync(
            conn, ["001_exists.sql", "999_missing.sql"]
        )

        # Should succeed but skip missing file
        assert success
        assert "Successfully executed 1 migrations" in message

        # Verify existing table was created
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='exists_table'"
        )
        result = cursor.fetchone()
        assert result is not None
    finally:
        conn.close()


@pytest.mark.asyncio
async def test_migration_runner_async_missing_file(tmp_path):
    """Test that migration runner handles missing files gracefully (async)."""
    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir()

    # Create only one migration file
    (migrations_dir / "001_exists.sql").write_text(
        "CREATE TABLE IF NOT EXISTS exists_table (id INTEGER);"
    )

    # Try to run with a missing file
    db_path = tmp_path / "test.db"
    runner = MigrationRunner(migrations_dir)
    success, message = await runner.run_migrations_async(
        str(db_path), ["001_exists.sql", "999_missing.sql"]
    )

    # Should succeed but skip missing file
    assert success
    assert "Successfully executed 1 migrations" in message

    # Verify existing table was created
    async with aiosqlite.connect(db_path) as conn:
        cursor = await conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='exists_table'"
        )
        result = await cursor.fetchone()
        assert result is not None


@pytest.mark.unit
def test_migration_runner_sync_invalid_sql(tmp_path):
    """Test that migration runner handles invalid SQL gracefully."""
    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir()

    # Create migration with invalid SQL
    (migrations_dir / "001_invalid.sql").write_text("INVALID SQL STATEMENT;")

    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(db_path)
    try:
        runner = MigrationRunner(migrations_dir)
        success, message = runner.run_migrations_sync(conn, ["001_invalid.sql"])

        # Should fail
        assert not success
        assert "Migration error" in message
    finally:
        conn.close()


@pytest.mark.asyncio
async def test_migration_runner_async_invalid_sql(tmp_path):
    """Test that migration runner handles invalid SQL gracefully (async)."""
    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir()

    # Create migration with invalid SQL
    (migrations_dir / "001_invalid.sql").write_text("INVALID SQL STATEMENT;")

    db_path = tmp_path / "test.db"
    runner = MigrationRunner(migrations_dir)
    success, message = await runner.run_migrations_async(str(db_path), ["001_invalid.sql"])

    # Should fail
    assert not success
    assert "Migration error" in message


@pytest.mark.unit
def test_migration_runner_sync_idempotent(tmp_path):
    """Test that migrations are idempotent (can run multiple times)."""
    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir()

    # Create idempotent migration with IF NOT EXISTS
    (migrations_dir / "001_idempotent.sql").write_text(
        "CREATE TABLE IF NOT EXISTS idempotent_table (id INTEGER PRIMARY KEY);"
    )

    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(db_path)
    try:
        runner = MigrationRunner(migrations_dir)

        # Run migration first time
        success1, message1 = runner.run_migrations_sync(conn, ["001_idempotent.sql"])
        assert success1
        assert "Successfully executed 1 migrations" in message1

        # Run migration second time (should not fail)
        success2, message2 = runner.run_migrations_sync(conn, ["001_idempotent.sql"])
        assert success2
        assert "Successfully executed 1 migrations" in message2

        # Verify table exists
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='idempotent_table'"
        )
        result = cursor.fetchone()
        assert result is not None
    finally:
        conn.close()


@pytest.mark.asyncio
async def test_migration_runner_async_idempotent(tmp_path):
    """Test that migrations are idempotent (can run multiple times) async."""
    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir()

    # Create idempotent migration with IF NOT EXISTS
    (migrations_dir / "001_idempotent.sql").write_text(
        "CREATE TABLE IF NOT EXISTS idempotent_table (id INTEGER PRIMARY KEY);"
    )

    db_path = tmp_path / "test.db"
    runner = MigrationRunner(migrations_dir)

    # Run migration first time
    success1, message1 = await runner.run_migrations_async(
        str(db_path), ["001_idempotent.sql"]
    )
    assert success1
    assert "Successfully executed 1 migrations" in message1

    # Run migration second time (should not fail)
    success2, message2 = await runner.run_migrations_async(
        str(db_path), ["001_idempotent.sql"]
    )
    assert success2
    assert "Successfully executed 1 migrations" in message2

    # Verify table exists
    async with aiosqlite.connect(db_path) as conn:
        cursor = await conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='idempotent_table'"
        )
        result = await cursor.fetchone()
        assert result is not None
