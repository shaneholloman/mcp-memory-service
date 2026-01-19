"""SQL Migration Runner for Database Schema Updates.

This module provides utilities for executing SQL migration files to update
database schemas. Supports both synchronous and asynchronous execution to work
with different connection types in the codebase.

Usage:
    # Async usage with aiosqlite
    runner = MigrationRunner(Path("migrations"))
    success, msg = await runner.run_migrations_async(
        "/path/to/db.sqlite",
        ["001_add_table.sql", "002_add_index.sql"]
    )

    # Sync usage with sqlite3
    runner = MigrationRunner(Path("migrations"))
    success, msg = runner.run_migrations_sync(
        conn,
        ["001_add_table.sql", "002_add_index.sql"]
    )
"""

import logging
import sqlite3
from pathlib import Path
from typing import List, Tuple

import aiosqlite

logger = logging.getLogger(__name__)


class MigrationRunner:
    """Executes SQL migration files for database schema updates.

    Supports both synchronous and asynchronous execution to work with
    different connection types in the codebase. Migration files are
    expected to be idempotent (safe to run multiple times).

    Attributes:
        migrations_dir: Path to directory containing migration SQL files
    """

    def __init__(self, migrations_dir: Path):
        """Initialize the migration runner.

        Args:
            migrations_dir: Path to directory containing migration SQL files
        """
        self.migrations_dir = migrations_dir

    def _get_migration_sql(self, filename: str) -> str | None:
        """Read SQL content from migration file.

        Args:
            filename: Name of migration file

        Returns:
            SQL content if file exists, None otherwise
        """
        migration_path = self.migrations_dir / filename
        if not migration_path.exists():
            logger.warning(f"Migration file not found: {filename}")
            return None
        return migration_path.read_text()

    @staticmethod
    def _is_idempotent_error(error: Exception) -> bool:
        """Check if error indicates migration already applied.

        Args:
            error: Exception from migration execution

        Returns:
            True if error indicates idempotent operation (already applied)
        """
        error_msg = str(error).lower()
        return "duplicate column" in error_msg or "already exists" in error_msg

    @staticmethod
    def _format_result_message(executed_count: int, skipped_count: int) -> str:
        """Format migration result message.

        Args:
            executed_count: Number of migrations executed
            skipped_count: Number of migrations skipped

        Returns:
            Formatted result message
        """
        message = f"Successfully executed {executed_count} migrations"
        if skipped_count > 0:
            message += f" ({skipped_count} already applied)"
        return message

    def run_migrations_sync(
        self, conn: sqlite3.Connection, migration_files: List[str]
    ) -> Tuple[bool, str]:
        """Execute specified migration files synchronously.

        Executes migration files in sorted order. Each file should contain
        valid SQLite SQL statements. Uses executescript() to support multiple
        statements per file.

        Handles idempotency for certain migrations (e.g., adding columns that
        may already exist).

        Args:
            conn: Open sqlite3.Connection
            migration_files: List of migration filenames to execute (e.g.,
                ["001_add_table.sql", "002_add_index.sql"])

        Returns:
            Tuple[bool, str]: (success, message)
                - success: True if all migrations executed successfully
                - message: Summary message with execution count or error details

        Example:
            runner = MigrationRunner(Path("migrations"))
            success, msg = runner.run_migrations_sync(conn, ["001_init.sql"])
            if not success:
                logger.error(f"Migration failed: {msg}")
        """
        try:
            executed_count = 0
            skipped_count = 0

            for filename in sorted(migration_files):
                sql = self._get_migration_sql(filename)
                if sql is None:
                    continue

                logger.info(f"Executing migration: {filename}")

                try:
                    # Execute all statements in the migration file
                    # Note: executescript() commits automatically
                    conn.executescript(sql)
                    executed_count += 1
                    logger.info(f"Migration completed: {filename}")

                except sqlite3.OperationalError as e:
                    # Handle idempotent migrations (e.g., column already exists)
                    if self._is_idempotent_error(e):
                        logger.info(f"Migration {filename} already applied (skipped): {e}")
                        skipped_count += 1
                    else:
                        # Re-raise other operational errors
                        raise

            return True, self._format_result_message(executed_count, skipped_count)

        except Exception as e:
            logger.error(f"Migration failed: {e}")
            return False, f"Migration error: {str(e)}"

    async def run_migrations_async(
        self, db_path: str, migration_files: List[str]
    ) -> Tuple[bool, str]:
        """Execute specified migration files asynchronously.

        Executes migration files in sorted order. Each file should contain
        valid SQLite SQL statements. Uses executescript() to support multiple
        statements per file.

        Handles idempotency for certain migrations (e.g., adding columns that
        may already exist).

        Args:
            db_path: Path to SQLite database file
            migration_files: List of migration filenames to execute (e.g.,
                ["001_add_table.sql", "002_add_index.sql"])

        Returns:
            Tuple[bool, str]: (success, message)
                - success: True if all migrations executed successfully
                - message: Summary message with execution count or error details

        Example:
            runner = MigrationRunner(Path("migrations"))
            success, msg = await runner.run_migrations_async(
                "/tmp/db.sqlite",
                ["001_init.sql"]
            )
            if not success:
                logger.error(f"Migration failed: {msg}")
        """
        try:
            async with aiosqlite.connect(db_path) as conn:
                executed_count = 0
                skipped_count = 0

                for filename in sorted(migration_files):
                    sql = self._get_migration_sql(filename)
                    if sql is None:
                        continue

                    logger.info(f"Executing migration: {filename}")

                    try:
                        # Execute all statements in the migration file
                        # Note: executescript() commits automatically
                        await conn.executescript(sql)
                        executed_count += 1
                        logger.info(f"Migration completed: {filename}")

                    except aiosqlite.OperationalError as e:
                        # Handle idempotent migrations (e.g., column already exists)
                        if self._is_idempotent_error(e):
                            logger.info(f"Migration {filename} already applied (skipped): {e}")
                            skipped_count += 1
                        else:
                            # Re-raise other operational errors
                            raise

            return True, self._format_result_message(executed_count, skipped_count)

        except Exception as e:
            logger.error(f"Migration failed: {e}")
            return False, f"Migration error: {str(e)}"
