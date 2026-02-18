"""Tests for config.py environment variable parsing robustness."""
import os
import pytest


def test_hybrid_sync_interval_bad_value_uses_default(monkeypatch):
    """Bad MCP_HYBRID_SYNC_INTERVAL value should use default, not crash."""
    monkeypatch.setenv('MCP_MEMORY_STORAGE_BACKEND', 'hybrid')
    monkeypatch.setenv('MCP_HYBRID_SYNC_INTERVAL', 'not-a-number')
    # Required Cloudflare vars for hybrid
    monkeypatch.setenv('CLOUDFLARE_API_TOKEN', 'tok')
    monkeypatch.setenv('CLOUDFLARE_ACCOUNT_ID', 'acc')
    monkeypatch.setenv('CLOUDFLARE_VECTORIZE_INDEX', 'idx')
    monkeypatch.setenv('CLOUDFLARE_D1_DATABASE_ID', 'db')

    import importlib
    import mcp_memory_service.config as cfg
    importlib.reload(cfg)

    assert cfg.HYBRID_SYNC_INTERVAL == 300  # default


def test_hybrid_batch_size_bad_value_uses_default(monkeypatch):
    """Bad MCP_HYBRID_BATCH_SIZE value should use default, not crash."""
    monkeypatch.setenv('MCP_MEMORY_STORAGE_BACKEND', 'hybrid')
    monkeypatch.setenv('MCP_HYBRID_BATCH_SIZE', 'lots')
    monkeypatch.setenv('CLOUDFLARE_API_TOKEN', 'tok')
    monkeypatch.setenv('CLOUDFLARE_ACCOUNT_ID', 'acc')
    monkeypatch.setenv('CLOUDFLARE_VECTORIZE_INDEX', 'idx')
    monkeypatch.setenv('CLOUDFLARE_D1_DATABASE_ID', 'db')

    import importlib
    import mcp_memory_service.config as cfg
    importlib.reload(cfg)

    assert cfg.HYBRID_BATCH_SIZE == 100  # default
