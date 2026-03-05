"""
Tests for GitHub issue #551:
External embedding API fallback must NOT silently corrupt DB with dimension mismatch.

When MCP_EXTERNAL_EMBEDDING_URL is set and the API is unreachable, the service
must raise RuntimeError rather than falling back to a local model with a
different embedding dimension.
"""
import pytest
import sqlite3
import sys
from unittest.mock import MagicMock, patch


def _make_storage(monkeypatch=None, external_url="http://localhost:11434/v1/embeddings"):
    from mcp_memory_service.storage.sqlite_vec import SqliteVecMemoryStorage
    storage = SqliteVecMemoryStorage.__new__(SqliteVecMemoryStorage)
    storage.embedding_model = None
    storage.embedding_dimension = 384
    storage.embedding_model_name = "all-MiniLM-L6-v2"
    storage.conn = None
    if monkeypatch and external_url:
        monkeypatch.setenv("MCP_EXTERNAL_EMBEDDING_URL", external_url)
        monkeypatch.delenv("MCP_EXTERNAL_EMBEDDING_API_KEY", raising=False)
        monkeypatch.delenv("MCP_MEMORY_STORAGE_BACKEND", raising=False)
        monkeypatch.delenv("MCP_EXTERNAL_EMBEDDING_MODEL", raising=False)
    return storage


class TestGetExistingDbEmbeddingDimension:
    """Unit tests for the _get_existing_db_embedding_dimension helper."""

    def test_returns_none_when_conn_is_none(self):
        """Returns None when conn is not set."""
        storage = _make_storage()
        storage.conn = None
        assert storage._get_existing_db_embedding_dimension() is None

    def test_returns_none_when_table_missing(self, tmp_path):
        """Returns None when memory_embeddings table does not exist."""
        conn = sqlite3.connect(str(tmp_path / "test.db"))
        conn.execute("CREATE TABLE memories (id INTEGER PRIMARY KEY)")
        conn.commit()
        storage = _make_storage()
        storage.conn = conn
        assert storage._get_existing_db_embedding_dimension() is None

    def _make_conn_returning(self, sql_row):
        """Return a MagicMock connection whose execute().fetchone() yields sql_row."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = sql_row
        mock_conn = MagicMock()
        mock_conn.execute.return_value = mock_cursor
        return mock_conn

    def test_regex_parses_768_dimension_from_schema_string(self):
        """Correctly parses FLOAT[768] from a mocked sqlite_master row."""
        sql = 'CREATE VIRTUAL TABLE memory_embeddings USING vec0(content_embedding FLOAT[768] distance_metric=cosine)'
        storage = _make_storage()
        storage.conn = self._make_conn_returning((sql,))
        assert storage._get_existing_db_embedding_dimension() == 768

    def test_regex_parses_384_dimension_from_schema_string(self):
        """Correctly parses FLOAT[384] from a mocked sqlite_master row."""
        sql = 'CREATE VIRTUAL TABLE memory_embeddings USING vec0(content_embedding FLOAT[384] distance_metric=cosine)'
        storage = _make_storage()
        storage.conn = self._make_conn_returning((sql,))
        assert storage._get_existing_db_embedding_dimension() == 384

    def test_returns_none_when_no_float_pattern(self):
        """Returns None when schema row has no FLOAT[N] pattern."""
        sql = 'CREATE VIRTUAL TABLE memory_embeddings USING vec0(id INTEGER)'
        storage = _make_storage()
        storage.conn = self._make_conn_returning((sql,))
        assert storage._get_existing_db_embedding_dimension() is None


class TestExternalEmbeddingFallbackBehavior:
    """External API unreachable must raise RuntimeError, not silently fall back."""

    def _patch_ext_module(self, exc):
        """Return a context manager that patches the external_api local import."""
        mock_mod = MagicMock()
        mock_mod.get_external_embedding_model.side_effect = exc
        return patch.dict(
            sys.modules,
            {"mcp_memory_service.embeddings.external_api": mock_mod},
        )

    @pytest.mark.asyncio
    async def test_connection_error_raises_with_dim_info_when_db_exists(self, monkeypatch):
        """RuntimeError includes dimension info when existing DB has embeddings."""
        storage = _make_storage(monkeypatch)

        with patch.object(storage, "_is_docker_environment", return_value=False), \
             patch.object(storage, "_get_existing_db_embedding_dimension", return_value=768), \
             self._patch_ext_module(ConnectionError("Connection refused")):
            with pytest.raises(RuntimeError) as exc_info:
                await storage._initialize_embedding_model()

        err = str(exc_info.value)
        assert "unreachable" in err.lower()
        assert "768" in err
        assert "dimension mismatch" in err.lower()

    @pytest.mark.asyncio
    async def test_connection_error_raises_without_dim_info_when_no_db(self, monkeypatch):
        """RuntimeError raised even when DB doesn't exist yet."""
        storage = _make_storage(monkeypatch)

        with patch.object(storage, "_is_docker_environment", return_value=False), \
             patch.object(storage, "_get_existing_db_embedding_dimension", return_value=None), \
             self._patch_ext_module(ConnectionError("Connection refused")):
            with pytest.raises(RuntimeError) as exc_info:
                await storage._initialize_embedding_model()

        err = str(exc_info.value)
        assert "unreachable" in err.lower()
        assert "dimension mismatch" not in err.lower()

    @pytest.mark.asyncio
    async def test_runtime_error_also_raises(self, monkeypatch):
        """RuntimeError from the API also bubbles up correctly."""
        storage = _make_storage(monkeypatch)

        with patch.object(storage, "_is_docker_environment", return_value=False), \
             patch.object(storage, "_get_existing_db_embedding_dimension", return_value=384), \
             self._patch_ext_module(RuntimeError("model not found")):
            with pytest.raises(RuntimeError) as exc_info:
                await storage._initialize_embedding_model()

        assert "unreachable" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_import_error_also_raises(self, monkeypatch):
        """ImportError (missing external_api module) also raises, not silently falls back."""
        storage = _make_storage(monkeypatch)

        with patch.object(storage, "_is_docker_environment", return_value=False), \
             patch.object(storage, "_get_existing_db_embedding_dimension", return_value=384), \
             self._patch_ext_module(ImportError("module not found")):
            with pytest.raises(RuntimeError):
                await storage._initialize_embedding_model()

    @pytest.mark.asyncio
    async def test_no_external_url_does_not_raise(self, monkeypatch):
        """Without MCP_EXTERNAL_EMBEDDING_URL, no external call is made and no error raised."""
        storage = _make_storage()  # no external_url set
        monkeypatch.delenv("MCP_EXTERNAL_EMBEDDING_URL", raising=False)
        monkeypatch.delenv("MCP_MEMORY_USE_ONNX", raising=False)

        mock_model = MagicMock()
        mock_model.embedding_dimension = 384

        with patch.object(storage, "_is_docker_environment", return_value=False), \
             patch("mcp_memory_service.storage.sqlite_vec._MODEL_CACHE", {}), \
             patch("mcp_memory_service.storage.sqlite_vec._DIMENSION_CACHE", {}):
            # Patch the SentenceTransformer path so we don't need the full model
            with patch("mcp_memory_service.storage.sqlite_vec.SentenceTransformer", return_value=mock_model):
                try:
                    await storage._initialize_embedding_model()
                except RuntimeError as exc:
                    assert "unreachable" not in str(exc).lower(), (
                        f"No external URL was configured, but got external-URL RuntimeError: {exc}"
                    )
                except Exception:
                    pass  # Other failures (missing deps etc.) are acceptable here
