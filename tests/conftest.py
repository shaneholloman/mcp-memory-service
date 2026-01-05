import pytest
import os
import sys
import tempfile
import shutil
import uuid
from typing import Callable, Optional, List

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src'))

# Reserved tag for test memories - enables automatic cleanup
TEST_MEMORY_TAG = "__test__"

@pytest.fixture
def temp_db_path():
    '''Create a temporary directory for database testing.'''
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Clean up after test
    shutil.rmtree(temp_dir)

@pytest.fixture
def unique_content() -> Callable[[str], str]:
    """
    Generate unique test content to avoid duplicate content errors.

    Usage:
        def test_example(unique_content):
            content = unique_content("Test memory about authentication")
            hash1 = store(content, tags=["test"])

    Returns:
        A function that takes a base string and returns a unique version.
    """
    def _generator(base: str = "test") -> str:
        return f"{base} [{uuid.uuid4()}]"
    return _generator


@pytest.fixture
def test_store():
    """
    Store function that auto-tags memories with TEST_MEMORY_TAG for cleanup.

    All memories created with this fixture will be automatically deleted
    at the end of the test session via pytest_sessionfinish hook.

    Usage:
        def test_example(test_store, unique_content):
            hash1 = test_store(unique_content("Test memory"), tags=["auth"])
            # Memory will have tags: ["__test__", "auth"]
    """
    from mcp_memory_service.api import store

    def _store(content: str, tags: Optional[List[str]] = None, **kwargs):
        all_tags = [TEST_MEMORY_TAG] + (tags or [])
        return store(content, tags=all_tags, **kwargs)

    return _store


def pytest_sessionfinish(session, exitstatus):
    """
    Cleanup all test memories at end of test session.

    Deletes all memories tagged with TEST_MEMORY_TAG to prevent
    test data from polluting the production database.
    """
    try:
        from mcp_memory_service.api import delete_by_tag
        result = delete_by_tag([TEST_MEMORY_TAG])
        deleted = result.get('deleted', 0) if isinstance(result, dict) else 0
        if deleted > 0:
            print(f"\n[Test Cleanup] Deleted {deleted} test memories tagged with '{TEST_MEMORY_TAG}'")
    except Exception as e:
        # Don't fail the test session if cleanup fails
        print(f"\n[Test Cleanup] Warning: Could not cleanup test memories: {e}")
