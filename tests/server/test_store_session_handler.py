"""Tests for handle_store_session handler."""
import pytest
from unittest.mock import AsyncMock, MagicMock


def _make_server():
    """Build a minimal mock server that records what was stored."""
    server = MagicMock()
    server._ensure_storage_initialized = AsyncMock()
    server.memory_service = MagicMock()
    server.memory_service.store_memory = AsyncMock(return_value={
        "success": True,
        "memory": {"content_hash": "abc123"},
    })
    return server


@pytest.mark.asyncio
async def test_store_session_concatenates_turns():
    from mcp_memory_service.server.handlers.memory import handle_store_session
    server = _make_server()

    await handle_store_session(server, {
        "turns": [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
        ]
    })

    call_kwargs = server.memory_service.store_memory.call_args.kwargs
    content = call_kwargs["content"]
    assert "[user] Hello" in content
    assert "[assistant] Hi there" in content


@pytest.mark.asyncio
async def test_store_session_returns_hash_in_message():
    from mcp_memory_service.server.handlers.memory import handle_store_session
    server = _make_server()

    result = await handle_store_session(server, {
        "turns": [{"role": "user", "content": "Hello"}]
    })

    assert len(result) == 1
    assert "abc123" in result[0].text


@pytest.mark.asyncio
async def test_store_session_uses_session_memory_type():
    from mcp_memory_service.server.handlers.memory import handle_store_session
    server = _make_server()

    await handle_store_session(server, {"turns": [{"role": "user", "content": "Test"}]})

    call_kwargs = server.memory_service.store_memory.call_args.kwargs
    assert call_kwargs["memory_type"] == "session"


@pytest.mark.asyncio
async def test_store_session_tags_include_provided_session_id():
    from mcp_memory_service.server.handlers.memory import handle_store_session
    server = _make_server()

    await handle_store_session(server, {
        "turns": [{"role": "user", "content": "Test"}],
        "session_id": "my-session-42",
    })

    call_kwargs = server.memory_service.store_memory.call_args.kwargs
    assert "session:my-session-42" in call_kwargs["tags"]


@pytest.mark.asyncio
async def test_store_session_autogenerates_session_id():
    from mcp_memory_service.server.handlers.memory import handle_store_session
    server = _make_server()

    await handle_store_session(server, {"turns": [{"role": "user", "content": "Test"}]})

    call_kwargs = server.memory_service.store_memory.call_args.kwargs
    assert any(t.startswith("session:") for t in call_kwargs["tags"])


@pytest.mark.asyncio
async def test_store_session_accepts_extra_tags_as_list():
    from mcp_memory_service.server.handlers.memory import handle_store_session
    server = _make_server()

    await handle_store_session(server, {
        "turns": [{"role": "user", "content": "Test"}],
        "tags": ["project:foo", "important"],
    })

    call_kwargs = server.memory_service.store_memory.call_args.kwargs
    assert "project:foo" in call_kwargs["tags"]
    assert "important" in call_kwargs["tags"]


@pytest.mark.asyncio
async def test_store_session_accepts_extra_tags_as_string():
    from mcp_memory_service.server.handlers.memory import handle_store_session
    server = _make_server()

    await handle_store_session(server, {
        "turns": [{"role": "user", "content": "Test"}],
        "tags": "project:foo,important",
    })

    call_kwargs = server.memory_service.store_memory.call_args.kwargs
    assert "project:foo" in call_kwargs["tags"]
    assert "important" in call_kwargs["tags"]


@pytest.mark.asyncio
async def test_store_session_rejects_empty_turns():
    from mcp_memory_service.server.handlers.memory import handle_store_session
    server = _make_server()

    result = await handle_store_session(server, {"turns": []})

    assert "Error" in result[0].text
    server.memory_service.store_memory.assert_not_called()


@pytest.mark.asyncio
async def test_store_session_rejects_missing_turns():
    from mcp_memory_service.server.handlers.memory import handle_store_session
    server = _make_server()

    result = await handle_store_session(server, {})

    assert "Error" in result[0].text
    server.memory_service.store_memory.assert_not_called()


@pytest.mark.asyncio
async def test_store_session_skips_empty_content_turns():
    from mcp_memory_service.server.handlers.memory import handle_store_session
    server = _make_server()

    await handle_store_session(server, {
        "turns": [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "   "},   # whitespace only — skipped
            {"role": "user", "content": "Follow-up"},
        ]
    })

    call_kwargs = server.memory_service.store_memory.call_args.kwargs
    content = call_kwargs["content"]
    assert "[user] Hello" in content
    assert "[user] Follow-up" in content
    assert content.count("\n") == 1  # only 2 non-empty turns
