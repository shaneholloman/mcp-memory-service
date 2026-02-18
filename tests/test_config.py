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


def test_validate_config_returns_error_for_https_without_cert(monkeypatch):
    """HTTPS enabled without cert/key files should return validation error."""
    monkeypatch.setenv('MCP_HTTPS_ENABLED', 'true')
    monkeypatch.setenv('MCP_SSL_CERT_FILE', '')
    monkeypatch.setenv('MCP_SSL_KEY_FILE', '')

    import importlib
    import mcp_memory_service.config as cfg
    importlib.reload(cfg)

    errors = cfg.validate_config()
    assert any('ssl' in e.lower() or 'cert' in e.lower() for e in errors), \
        f"Expected SSL error, got: {errors}"


def test_validate_config_returns_no_errors_for_valid_sqlite_config(monkeypatch):
    """Default sqlite_vec config should have no validation errors."""
    monkeypatch.setenv('MCP_MEMORY_STORAGE_BACKEND', 'sqlite_vec')
    # Explicitly disable HTTPS to avoid .env file setting interfering
    monkeypatch.setenv('MCP_HTTPS_ENABLED', 'false')
    monkeypatch.setenv('MCP_HYBRID_KEYWORD_WEIGHT', '0.3')
    monkeypatch.setenv('MCP_HYBRID_SEMANTIC_WEIGHT', '0.7')

    import importlib
    import mcp_memory_service.config as cfg
    importlib.reload(cfg)

    errors = cfg.validate_config()
    assert errors == [], f"Expected no errors for default config, got: {errors}"


def test_validate_config_returns_warning_for_hybrid_weight_normalization(monkeypatch):
    """Hybrid search weights not summing to 1.0 should return a warning in validate_config."""
    monkeypatch.setenv('MCP_MEMORY_STORAGE_BACKEND', 'sqlite_vec')
    monkeypatch.setenv('MCP_HYBRID_KEYWORD_WEIGHT', '0.5')
    monkeypatch.setenv('MCP_HYBRID_SEMANTIC_WEIGHT', '0.8')  # 0.5 + 0.8 = 1.3, auto-normalized

    import importlib
    import mcp_memory_service.config as cfg
    importlib.reload(cfg)

    # Config auto-normalizes weights, but validate_config() should report the discrepancy
    warnings = cfg.validate_config()
    assert any('weight' in w.lower() for w in warnings), \
        f"Expected weight normalization warning, got: {warnings}"
