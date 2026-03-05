"""
Tests for consolidation status handler — GitHub issue #542.

Regression tests verifying that handle_consolidation_status() does not crash
with a KeyError when ConsolidationHealthMonitor.check_overall_health() returns
an empty or partially-populated 'statistics' dict.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from mcp_memory_service.server.handlers.consolidation import (
    handle_consolidation_status,
    handle_memory_consolidate,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_health(*, statistics=None, last_consolidation_times=None, components=None):
    """Return a health dict with the given overrides, mimicking check_overall_health()."""
    return {
        "status": "healthy",
        "timestamp": "2026-01-01T00:00:00",
        "components": components if components is not None else {},
        "metrics": {},
        "alerts": [],
        "recommendations": [],
        "statistics": statistics if statistics is not None else {},
        **({"last_consolidation_times": last_consolidation_times}
           if last_consolidation_times is not None else {}),
    }


def _make_server(health: dict):
    """Return a minimal mock server whose consolidator.health_check() returns *health*."""
    server = MagicMock()
    server.consolidator = MagicMock()
    server.consolidator.health_check = AsyncMock(return_value=health)
    return server


# ---------------------------------------------------------------------------
# Issue #542 — statistics dict is empty → should NOT raise KeyError
# ---------------------------------------------------------------------------

@pytest.mark.unit
@pytest.mark.asyncio
async def test_status_does_not_crash_with_empty_statistics():
    """
    Regression test for GitHub issue #542.

    ConsolidationHealthMonitor.check_overall_health() sets 'statistics' to {}
    and never populates it.  The status handler must not raise KeyError when
    accessing keys such as 'total_runs', 'successful_runs', etc.
    """
    server = _make_server(_make_health(statistics={}))

    # Must not raise
    with patch(
        "mcp_memory_service.server.handlers.consolidation.CONSOLIDATION_ENABLED", True
    ):
        result = await handle_consolidation_status(server, {})

    assert len(result) == 1
    text = result[0].text

    # Defaults of 0 should appear in the output
    assert "Total consolidation runs: 0" in text
    assert "Successful runs: 0" in text
    assert "Total memories processed: 0" in text
    assert "Total associations created: 0" in text
    assert "Total clusters created: 0" in text
    assert "Total memories compressed: 0" in text
    assert "Total memories archived: 0" in text


@pytest.mark.unit
@pytest.mark.asyncio
async def test_status_does_not_crash_when_statistics_key_missing():
    """
    Edge case: health dict has no 'statistics' key at all (e.g. error path).
    The handler must still not raise KeyError.
    """
    health = {
        "status": "critical",
        "timestamp": "2026-01-01T00:00:00",
        "components": {},
        "metrics": {},
        "alerts": [],
        "recommendations": [],
        # 'statistics' intentionally omitted
    }
    server = _make_server(health)

    with patch(
        "mcp_memory_service.server.handlers.consolidation.CONSOLIDATION_ENABLED", True
    ):
        result = await handle_consolidation_status(server, {})

    assert len(result) == 1
    text = result[0].text
    assert "Total consolidation runs: 0" in text


@pytest.mark.unit
@pytest.mark.asyncio
async def test_status_shows_real_stats_when_populated():
    """When statistics is properly populated, the values should appear in output."""
    stats = {
        "total_runs": 42,
        "successful_runs": 40,
        "total_memories_processed": 1000,
        "total_associations_created": 250,
        "total_clusters_created": 15,
        "total_memories_compressed": 80,
        "total_memories_archived": 5,
    }
    server = _make_server(_make_health(statistics=stats))

    with patch(
        "mcp_memory_service.server.handlers.consolidation.CONSOLIDATION_ENABLED", True
    ):
        result = await handle_consolidation_status(server, {})

    text = result[0].text
    assert "Total consolidation runs: 42" in text
    assert "Successful runs: 40" in text
    assert "Total memories processed: 1000" in text
    assert "Total associations created: 250" in text
    assert "Total clusters created: 15" in text
    assert "Total memories compressed: 80" in text
    assert "Total memories archived: 5" in text


@pytest.mark.unit
@pytest.mark.asyncio
async def test_status_handles_partial_statistics():
    """Only some keys present — missing ones default to 0 without raising."""
    stats = {
        "total_runs": 7,
        "successful_runs": 6,
        # rest are absent
    }
    server = _make_server(_make_health(statistics=stats))

    with patch(
        "mcp_memory_service.server.handlers.consolidation.CONSOLIDATION_ENABLED", True
    ):
        result = await handle_consolidation_status(server, {})

    text = result[0].text
    assert "Total consolidation runs: 7" in text
    assert "Successful runs: 6" in text
    assert "Total memories processed: 0" in text
    assert "Total associations created: 0" in text


@pytest.mark.unit
@pytest.mark.asyncio
async def test_status_handles_missing_last_consolidation_times():
    """
    The original code also referenced health['last_consolidation_times'] which
    is not a key returned by check_overall_health().  Verify no KeyError.
    """
    # health has no 'last_consolidation_times' key at all
    server = _make_server(_make_health())

    with patch(
        "mcp_memory_service.server.handlers.consolidation.CONSOLIDATION_ENABLED", True
    ):
        result = await handle_consolidation_status(server, {})

    assert len(result) == 1
    # Should not crash and should not include the "Last Consolidation Times" section
    assert "Last Consolidation Times" not in result[0].text


@pytest.mark.unit
@pytest.mark.asyncio
async def test_status_shows_last_consolidation_times_when_present():
    """When last_consolidation_times is present it should be rendered."""
    server = _make_server(
        _make_health(
            last_consolidation_times={
                "daily": "2026-01-01T06:00:00",
                "weekly": "2025-12-28T02:00:00",
            }
        )
    )

    with patch(
        "mcp_memory_service.server.handlers.consolidation.CONSOLIDATION_ENABLED", True
    ):
        result = await handle_consolidation_status(server, {})

    text = result[0].text
    assert "Last Consolidation Times" in text
    assert "daily: 2026-01-01T06:00:00" in text
    assert "weekly: 2025-12-28T02:00:00" in text


@pytest.mark.unit
@pytest.mark.asyncio
async def test_status_includes_component_health():
    """Component health section should list components and their status."""
    components = {
        "decay_calculator": {"status": "healthy"},
        "scheduler": {"status": "unhealthy", "error": "APScheduler not running"},
    }
    server = _make_server(_make_health(components=components))

    with patch(
        "mcp_memory_service.server.handlers.consolidation.CONSOLIDATION_ENABLED", True
    ):
        result = await handle_consolidation_status(server, {})

    text = result[0].text
    assert "decay_calculator: HEALTHY" in text
    assert "scheduler: UNHEALTHY" in text
    assert "APScheduler not running" in text


@pytest.mark.unit
@pytest.mark.asyncio
async def test_unified_handler_status_action_does_not_crash():
    """
    Verify that calling handle_memory_consolidate with action='status' and an
    empty statistics dict does not raise — covers the top-level MCP handler.
    """
    server = _make_server(_make_health(statistics={}))

    with patch(
        "mcp_memory_service.server.handlers.consolidation.CONSOLIDATION_ENABLED", True
    ):
        result = await handle_memory_consolidate(server, {"action": "status"})

    assert len(result) == 1
    assert "Total consolidation runs: 0" in result[0].text


@pytest.mark.unit
@pytest.mark.asyncio
async def test_status_returns_disabled_when_consolidation_off():
    """When CONSOLIDATION_ENABLED is False the handler returns a disabled message."""
    server = MagicMock()

    with patch(
        "mcp_memory_service.server.handlers.consolidation.CONSOLIDATION_ENABLED", False
    ):
        result = await handle_consolidation_status(server, {})

    assert len(result) == 1
    assert "DISABLED" in result[0].text


@pytest.mark.unit
@pytest.mark.asyncio
async def test_status_returns_disabled_when_consolidator_is_none():
    """When server.consolidator is None the handler returns a disabled message."""
    server = MagicMock()
    server.consolidator = None

    with patch(
        "mcp_memory_service.server.handlers.consolidation.CONSOLIDATION_ENABLED", True
    ):
        result = await handle_consolidation_status(server, {})

    assert len(result) == 1
    assert "DISABLED" in result[0].text
