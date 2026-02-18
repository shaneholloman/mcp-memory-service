"""Tests for config.py environment variable parsing robustness."""
import os
import pytest


# ---------------------------------------------------------------------------
# Helper: test safe_get_int_env directly (no module reload needed)
# ---------------------------------------------------------------------------

def test_safe_get_int_env_bad_value_uses_default():
    """safe_get_int_env should return default when value is not an integer."""
    from mcp_memory_service.config import safe_get_int_env

    original = os.environ.pop('_TEST_SAFE_INT_ENV', None)
    try:
        os.environ['_TEST_SAFE_INT_ENV'] = 'not-a-number'
        result = safe_get_int_env('_TEST_SAFE_INT_ENV', 300)
        assert result == 300
    finally:
        os.environ.pop('_TEST_SAFE_INT_ENV', None)
        if original is not None:
            os.environ['_TEST_SAFE_INT_ENV'] = original


def test_safe_get_int_env_valid_value():
    """safe_get_int_env should return parsed integer for valid input."""
    from mcp_memory_service.config import safe_get_int_env

    original = os.environ.pop('_TEST_SAFE_INT_ENV', None)
    try:
        os.environ['_TEST_SAFE_INT_ENV'] = '42'
        result = safe_get_int_env('_TEST_SAFE_INT_ENV', 300)
        assert result == 42
    finally:
        os.environ.pop('_TEST_SAFE_INT_ENV', None)
        if original is not None:
            os.environ['_TEST_SAFE_INT_ENV'] = original


def test_safe_get_int_env_respects_min_value():
    """safe_get_int_env should clamp to min_value when value is too low."""
    from mcp_memory_service.config import safe_get_int_env

    original = os.environ.pop('_TEST_SAFE_INT_ENV', None)
    try:
        os.environ['_TEST_SAFE_INT_ENV'] = '-5'
        result = safe_get_int_env('_TEST_SAFE_INT_ENV', 300, min_value=1)
        assert result == 300  # Falls back to default (below min)
    finally:
        os.environ.pop('_TEST_SAFE_INT_ENV', None)
        if original is not None:
            os.environ['_TEST_SAFE_INT_ENV'] = original


def test_safe_get_int_env_respects_max_value():
    """safe_get_int_env should fall back to default when value exceeds max."""
    from mcp_memory_service.config import safe_get_int_env

    original = os.environ.pop('_TEST_SAFE_INT_ENV', None)
    try:
        os.environ['_TEST_SAFE_INT_ENV'] = '99999'
        result = safe_get_int_env('_TEST_SAFE_INT_ENV', 60, max_value=3600)
        assert result == 60  # Falls back to default (above max)
    finally:
        os.environ.pop('_TEST_SAFE_INT_ENV', None)
        if original is not None:
            os.environ['_TEST_SAFE_INT_ENV'] = original


# ---------------------------------------------------------------------------
# Tests for validate_config() - test the function directly, no reload needed
# ---------------------------------------------------------------------------

def test_validate_config_is_callable_and_returns_list():
    """validate_config() must be importable and return a list."""
    from mcp_memory_service.config import validate_config

    result = validate_config()
    assert isinstance(result, list)


def test_validate_config_returns_error_for_https_without_cert(monkeypatch):
    """HTTPS enabled without cert/key files should return validation error."""
    # Patch the module-level constants directly (no reload needed)
    import mcp_memory_service.config as cfg
    monkeypatch.setattr(cfg, 'HTTPS_ENABLED', True)
    monkeypatch.setattr(cfg, 'SSL_CERT_FILE', None)
    monkeypatch.setattr(cfg, 'SSL_KEY_FILE', None)

    errors = cfg.validate_config()
    assert any('ssl' in e.lower() or 'cert' in e.lower() for e in errors), \
        f"Expected SSL error, got: {errors}"


def test_validate_config_returns_no_errors_when_https_disabled(monkeypatch):
    """When HTTPS is disabled, no SSL errors should be returned."""
    import mcp_memory_service.config as cfg
    monkeypatch.setattr(cfg, 'HTTPS_ENABLED', False)

    # Temporarily patch weight env vars to known-good values to avoid weight warning
    original_keyword = os.environ.get('MCP_HYBRID_KEYWORD_WEIGHT')
    original_semantic = os.environ.get('MCP_HYBRID_SEMANTIC_WEIGHT')
    os.environ['MCP_HYBRID_KEYWORD_WEIGHT'] = '0.3'
    os.environ['MCP_HYBRID_SEMANTIC_WEIGHT'] = '0.7'
    try:
        errors = cfg.validate_config()
        ssl_errors = [e for e in errors if 'ssl' in e.lower() or 'cert' in e.lower()]
        assert ssl_errors == [], f"Expected no SSL errors, got: {ssl_errors}"
    finally:
        if original_keyword is not None:
            os.environ['MCP_HYBRID_KEYWORD_WEIGHT'] = original_keyword
        else:
            os.environ.pop('MCP_HYBRID_KEYWORD_WEIGHT', None)
        if original_semantic is not None:
            os.environ['MCP_HYBRID_SEMANTIC_WEIGHT'] = original_semantic
        else:
            os.environ.pop('MCP_HYBRID_SEMANTIC_WEIGHT', None)


def test_validate_config_returns_warning_for_hybrid_weight_normalization():
    """Hybrid search weights not summing to 1.0 should return a warning."""
    import mcp_memory_service.config as cfg

    # Temporarily set env vars to non-1.0-summing values
    original_keyword = os.environ.get('MCP_HYBRID_KEYWORD_WEIGHT')
    original_semantic = os.environ.get('MCP_HYBRID_SEMANTIC_WEIGHT')
    os.environ['MCP_HYBRID_KEYWORD_WEIGHT'] = '0.5'
    os.environ['MCP_HYBRID_SEMANTIC_WEIGHT'] = '0.8'  # Sum = 1.3

    try:
        warnings = cfg.validate_config()
        assert any('weight' in w.lower() for w in warnings), \
            f"Expected weight normalization warning, got: {warnings}"
    finally:
        if original_keyword is not None:
            os.environ['MCP_HYBRID_KEYWORD_WEIGHT'] = original_keyword
        else:
            os.environ.pop('MCP_HYBRID_KEYWORD_WEIGHT', None)
        if original_semantic is not None:
            os.environ['MCP_HYBRID_SEMANTIC_WEIGHT'] = original_semantic
        else:
            os.environ.pop('MCP_HYBRID_SEMANTIC_WEIGHT', None)
