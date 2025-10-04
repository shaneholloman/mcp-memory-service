#!/usr/bin/env python3
"""
Unit tests for Semtools document loader.
"""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import shutil

from mcp_memory_service.ingestion.semtools_loader import SemtoolsLoader
from mcp_memory_service.ingestion.base import DocumentChunk


class TestSemtoolsLoader:
    """Test suite for SemtoolsLoader class."""

    def test_initialization(self):
        """Test basic initialization of SemtoolsLoader."""
        loader = SemtoolsLoader(chunk_size=500, chunk_overlap=50)

        assert loader.chunk_size == 500
        assert loader.chunk_overlap == 50
        assert 'pdf' in loader.supported_extensions
        assert 'docx' in loader.supported_extensions
        assert 'pptx' in loader.supported_extensions

    @patch('shutil.which')
    def test_semtools_availability_check(self, mock_which):
        """Test detection of semtools availability."""
        # Test when semtools is available
        mock_which.return_value = '/usr/local/bin/semtools'
        loader = SemtoolsLoader()
        assert loader._semtools_available is True

        # Test when semtools is not available
        mock_which.return_value = None
        loader = SemtoolsLoader()
        assert loader._semtools_available is False

    @patch('shutil.which')
    def test_can_handle_file(self, mock_which):
        """Test file format detection."""
        mock_which.return_value = '/usr/local/bin/semtools'
        loader = SemtoolsLoader()

        # Create temporary test files
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_file = Path(tmpdir) / "test.pdf"
            pdf_file.touch()

            docx_file = Path(tmpdir) / "test.docx"
            docx_file.touch()

            txt_file = Path(tmpdir) / "test.txt"
            txt_file.touch()

            # Test supported formats
            assert loader.can_handle(pdf_file) is True
            assert loader.can_handle(docx_file) is True

            # Test unsupported formats
            assert loader.can_handle(txt_file) is False

    @patch('shutil.which')
    def test_can_handle_returns_false_when_semtools_unavailable(self, mock_which):
        """Test that can_handle returns False when semtools is not installed."""
        mock_which.return_value = None
        loader = SemtoolsLoader()

        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_file = Path(tmpdir) / "test.pdf"
            pdf_file.touch()

            # Should return False even for supported format when semtools unavailable
            assert loader.can_handle(pdf_file) is False

    @pytest.mark.asyncio
    @patch('shutil.which')
    async def test_extract_chunks_semtools_unavailable(self, mock_which):
        """Test that extract_chunks raises error when semtools is unavailable."""
        mock_which.return_value = None
        loader = SemtoolsLoader()

        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_file = Path(tmpdir) / "test.pdf"
            pdf_file.write_text("dummy content")

            # When semtools is unavailable, validate_file will fail first
            with pytest.raises(ValueError, match="File format not supported"):
                async for chunk in loader.extract_chunks(pdf_file):
                    pass

    @pytest.mark.asyncio
    @patch('mcp_memory_service.ingestion.semtools_loader.SemtoolsLoader._check_semtools_availability')
    @patch('asyncio.create_subprocess_exec')
    async def test_extract_chunks_success(self, mock_subprocess, mock_check_semtools):
        """Test successful document extraction with semtools."""
        # Force semtools to be "available"
        mock_check_semtools.return_value = True

        # Mock successful semtools execution with sufficient content to create chunks
        mock_content = b"# Document Title\n\n" + b"This is a test document with enough content to create chunks. " * 10
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(
            return_value=(mock_content, b"")
        )
        mock_subprocess.return_value = mock_process

        loader = SemtoolsLoader(chunk_size=200, chunk_overlap=50)
        loader._semtools_available = True  # Override

        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_file = Path(tmpdir) / "test.pdf"
            pdf_file.write_text("dummy content")

            chunks = []
            async for chunk in loader.extract_chunks(pdf_file):
                chunks.append(chunk)

            # Verify chunks were created
            assert len(chunks) > 0

            # Verify chunk structure
            first_chunk = chunks[0]
            assert isinstance(first_chunk, DocumentChunk)
            assert isinstance(first_chunk.content, str)
            assert first_chunk.metadata['extraction_method'] == 'semtools'
            assert first_chunk.metadata['parser_backend'] == 'llamaparse'
            assert first_chunk.source_file == pdf_file

    @pytest.mark.asyncio
    @patch('mcp_memory_service.ingestion.semtools_loader.SemtoolsLoader._check_semtools_availability')
    @patch('asyncio.create_subprocess_exec')
    @patch.dict('os.environ', {'LLAMAPARSE_API_KEY': 'test-api-key'})
    async def test_extract_chunks_with_api_key(self, mock_subprocess, mock_check_semtools):
        """Test that API key is passed to semtools when available."""
        mock_check_semtools.return_value = True

        # Mock with sufficient content to create chunks
        mock_content = b"# Content\n\n" + b"This document has enough content to create chunks. " * 10
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(
            return_value=(mock_content, b"")
        )
        mock_subprocess.return_value = mock_process

        # Create loader with API key
        loader = SemtoolsLoader()
        loader._semtools_available = True  # Override

        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_file = Path(tmpdir) / "test.pdf"
            pdf_file.write_text("dummy content")

            chunks = []
            async for chunk in loader.extract_chunks(pdf_file):
                chunks.append(chunk)

            # Verify chunks were created and API key was recognized
            assert len(chunks) > 0
            assert chunks[0].metadata['has_api_key'] is True

    @pytest.mark.asyncio
    @patch('shutil.which')
    @patch('asyncio.create_subprocess_exec')
    async def test_extract_chunks_semtools_error(self, mock_subprocess, mock_which):
        """Test handling of semtools execution errors."""
        mock_which.return_value = '/usr/local/bin/semtools'

        # Mock failed semtools execution
        mock_process = AsyncMock()
        mock_process.returncode = 1
        mock_process.communicate = AsyncMock(
            return_value=(b"", b"Error: Failed to parse document")
        )
        mock_subprocess.return_value = mock_process

        loader = SemtoolsLoader()

        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_file = Path(tmpdir) / "test.pdf"
            pdf_file.write_text("dummy content")

            with pytest.raises(ValueError, match="Failed to parse document"):
                async for chunk in loader.extract_chunks(pdf_file):
                    pass

    @pytest.mark.asyncio
    @patch('shutil.which')
    @patch('asyncio.create_subprocess_exec')
    @patch('asyncio.wait_for')
    async def test_extract_chunks_timeout(self, mock_wait_for, mock_subprocess, mock_which):
        """Test handling of semtools timeout."""
        mock_which.return_value = '/usr/local/bin/semtools'

        # Mock timeout scenario
        mock_wait_for.side_effect = asyncio.TimeoutError()

        loader = SemtoolsLoader()

        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_file = Path(tmpdir) / "test.pdf"
            pdf_file.write_text("dummy content")

            with pytest.raises(ValueError, match="timed out|Failed to parse"):
                async for chunk in loader.extract_chunks(pdf_file):
                    pass

    @pytest.mark.asyncio
    @patch('shutil.which')
    @patch('asyncio.create_subprocess_exec')
    async def test_extract_chunks_empty_content(self, mock_subprocess, mock_which):
        """Test handling of empty content from semtools."""
        mock_which.return_value = '/usr/local/bin/semtools'

        # Mock empty output
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(
            return_value=(b"", b"")  # Empty stdout
        )
        mock_subprocess.return_value = mock_process

        loader = SemtoolsLoader()

        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_file = Path(tmpdir) / "test.pdf"
            pdf_file.write_text("dummy content")

            with pytest.raises(ValueError, match="empty content|Failed to parse"):
                async for chunk in loader.extract_chunks(pdf_file):
                    pass


class TestSemtoolsLoaderRegistry:
    """Test semtools loader registration."""

    @patch('shutil.which')
    def test_loader_registration_with_semtools(self, mock_which):
        """Test that semtools loader is registered when available."""
        mock_which.return_value = '/usr/local/bin/semtools'

        from mcp_memory_service.ingestion.registry import get_loader_for_file

        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            # Test DOCX file (semtools-only format)
            docx_file = Path(tmpdir) / "test.docx"
            docx_file.touch()

            loader = get_loader_for_file(docx_file)

            # Should get SemtoolsLoader when semtools is available
            assert loader is not None
            assert isinstance(loader, SemtoolsLoader)

    @patch('shutil.which')
    def test_loader_registration_without_semtools(self, mock_which):
        """Test that docx files return None when semtools unavailable."""
        mock_which.return_value = None

        from mcp_memory_service.ingestion.registry import get_loader_for_file

        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            # Test DOCX file (semtools-only format)
            docx_file = Path(tmpdir) / "test.docx"
            docx_file.touch()

            loader = get_loader_for_file(docx_file)

            # Should return None when semtools is not available
            assert loader is None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
