"""
Shared test fixtures and helpers for unit tests.
"""

import tempfile
from pathlib import Path
from typing import List, Any, Optional


async def extract_chunks_from_temp_file(
    loader: Any,
    filename: str,
    content: str,
    encoding: str = 'utf-8',
    **extract_kwargs
) -> List[Any]:
    """
    Helper to extract chunks from a temporary file.

    Args:
        loader: Loader instance (CSVLoader, JSONLoader, etc.)
        filename: Name of the temporary file to create
        content: Content to write to the file
        encoding: File encoding (default: utf-8)
        **extract_kwargs: Additional keyword arguments to pass to extract_chunks()

    Returns:
        List of extracted chunks

    Example:
        >>> loader = CSVLoader(chunk_size=1000, chunk_overlap=200)
        >>> chunks = await extract_chunks_from_temp_file(
        ...     loader,
        ...     "test.csv",
        ...     "name,age\\nJohn,25",
        ...     delimiter=','
        ... )
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = Path(tmpdir) / filename
        file_path.write_text(content, encoding=encoding)

        chunks = []
        async for chunk in loader.extract_chunks(file_path, **extract_kwargs):
            chunks.append(chunk)

        return chunks
