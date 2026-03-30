"""Tests for async threading behavior in sqlite_vec storage."""

import asyncio
import time
import pytest
import sqlite3
from unittest.mock import MagicMock


class TestExecuteWithRetryThreading:
    """Verify _execute_with_retry offloads work to a thread."""

    @pytest.mark.asyncio
    async def test_execute_with_retry_does_not_block_loop(self, tmp_path):
        """DB operations inside _execute_with_retry should not block the event loop.

        Strategy: run two _execute_with_retry calls concurrently, each sleeping
        300ms. If they block the loop sequentially, total time ≈ 600ms.
        If they run in threads concurrently, total time ≈ 300ms.
        """
        from mcp_memory_service.storage.sqlite_vec import SqliteVecMemoryStorage

        storage = SqliteVecMemoryStorage.__new__(SqliteVecMemoryStorage)
        storage.conn = sqlite3.connect(str(tmp_path / "test.db"), check_same_thread=False)
        storage.conn.execute("CREATE TABLE t (id INTEGER)")

        def slow_op_a():
            time.sleep(0.3)
            return "a"

        def slow_op_b():
            time.sleep(0.3)
            return "b"

        t0 = time.monotonic()
        results = await asyncio.gather(
            storage._execute_with_retry(slow_op_a),
            storage._execute_with_retry(slow_op_b),
        )
        elapsed = time.monotonic() - t0

        assert set(results) == {"a", "b"}
        # Sequential (blocking): ~600ms. Concurrent (threaded): ~300ms.
        # Threshold of 500ms gives generous margin for slow CI.
        assert elapsed < 0.5, (
            f"Two 300ms ops took {elapsed:.3f}s total — "
            f"expected ~0.3s if concurrent, got ~0.6s if blocking sequentially"
        )
        storage.conn.close()

    @pytest.mark.asyncio
    async def test_execute_with_retry_returns_result(self, tmp_path):
        """_execute_with_retry should return the operation's result."""
        from mcp_memory_service.storage.sqlite_vec import SqliteVecMemoryStorage

        storage = SqliteVecMemoryStorage.__new__(SqliteVecMemoryStorage)
        # check_same_thread=False required because asyncio.to_thread runs in a worker thread
        storage.conn = sqlite3.connect(str(tmp_path / "test.db"), check_same_thread=False)
        storage.conn.execute("CREATE TABLE t (val TEXT)")
        storage.conn.execute("INSERT INTO t VALUES ('hello')")

        def query():
            return storage.conn.execute("SELECT val FROM t").fetchone()[0]

        result = await storage._execute_with_retry(query)
        assert result == "hello"
        storage.conn.close()

    @pytest.mark.asyncio
    async def test_execute_with_retry_retries_on_locked(self, tmp_path):
        """Should retry with backoff on OperationalError('database is locked')."""
        from mcp_memory_service.storage.sqlite_vec import SqliteVecMemoryStorage

        storage = SqliteVecMemoryStorage.__new__(SqliteVecMemoryStorage)
        storage.conn = sqlite3.connect(str(tmp_path / "test.db"), check_same_thread=False)

        call_count = 0

        def flaky_op():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise sqlite3.OperationalError("database is locked")
            return "success"

        result = await storage._execute_with_retry(flaky_op, max_retries=5, initial_delay=0.01)
        assert result == "success"
        assert call_count == 3
        storage.conn.close()
