# MCP-MEMORY-SERVICE Tests

This directory contains tests for the MCP-MEMORY-SERVICE project.

## ⚠️  CRITICAL: Test Safety Guidelines

**NEVER use production paths in test files!** This can cause production data loss.

### ❌ WRONG - Causes Production Data Loss

```python
# NEVER hardcode production paths in tests!
os.environ["MCP_MEMORY_SQLITE_PATH"] = os.path.expanduser(
    "~/Library/Application Support/mcp-memory/sqlite_vec.db"
)
```

### ✅ CORRECT - Uses Isolated Temp Database

```python
def test_something(temp_db_path):
    """Test using isolated temporary database."""
    os.environ["MCP_MEMORY_SQLITE_PATH"] = str(temp_db_path / "test.db")
    # ... test code (automatically cleaned up)
```

## Directory Structure

- `api/` - API layer tests (compact types, operations)
- `storage/` - Backend-specific tests (sqlite_vec, cloudflare, hybrid)
- `server/` - MCP server handler tests
- `consolidation/` - Memory maintenance tests
- `quality/` - Quality scoring tests
- `web/` - HTTP API and OAuth tests
- `conftest.py` - Shared fixtures and test configuration
- `pytest.ini` - Pytest configuration and markers

## Test Fixtures

### `temp_db_path`
Creates isolated temporary database directory (auto-cleanup).

```python
def test_memory(temp_db_path):
    os.environ["MCP_MEMORY_SQLITE_PATH"] = str(temp_db_path / "test.db")
    # Uses temp database, safe from production
```

### `test_store`
Auto-tags memories with `__test__` for cleanup.

```python
async def test_create(test_store):
    memory = await test_store("Test content", tags=["example"])
    # Automatically cleaned up after test session
```

### `unique_content`
Generates unique content to avoid duplicates.

```python
def test_unique(unique_content):
    content1 = unique_content()  # "test content abc123..."
    content2 = unique_content()  # "test content def456..." (different)
```

## Reserved Test Tag

**`__test__`** - Reserved for test isolation
- Auto-added by `test_store` fixture
- Used by cleanup hooks
- **NEVER use in production code**

## Running Tests

### Run All Tests (968 tests total)
```bash
pytest
```

### Run by Category
```bash
pytest -m unit           # Fast unit tests only
pytest -m integration    # Integration tests (require storage)
pytest -m performance    # Performance benchmarks
```

### Run Specific Test File
```bash
pytest tests/storage/test_sqlite_vec.py
```

### Run with Verbose Output
```bash
pytest -v -s
```

### Check Coverage
```bash
pytest --cov=src/mcp_memory_service --cov-report=html
```

## Test Markers

Available markers (defined in `pytest.ini`):

```python
@pytest.mark.unit         # Fast unit tests
@pytest.mark.integration  # Integration tests
@pytest.mark.performance  # Performance benchmarks
```

## Safety Features

The test suite has three layers of protection against production data loss:

### Layer 1: Path Validation in conftest.py
Cleanup hook verifies database is in temp directory before deleting test memories.

### Layer 2: API-Level Protection
`delete_by_tag()` requires `allow_production=True` flag for non-temp databases.

### Layer 3: Visible Error Messages
Errors are displayed with ❌ emoji, showing exactly which database is being used.

## Manual Testing Scripts

Manual test scripts that use production paths are in `scripts/testing/`:
- `manual_memory_test.py` - Basic operations (production DB)
- `manual_integration_test.py` - Integration testing (production DB)

These are **NOT** run by pytest and should **NEVER** be moved to `tests/` directory.

## Safety Checklist

Before committing:
- [ ] No hardcoded production paths
- [ ] Tests use `temp_db_path` or `test_store` fixtures
- [ ] Manual scripts in `scripts/testing/`, not `tests/`
- [ ] All tests pass: `pytest tests/`
- [ ] Cleanup shows temp path: `pytest -v -s`

## What If Production Data Is Lost?

Production memories use soft-delete. Check for recoverable memories:

```bash
# Check soft-deleted count
python3 -c "
import sqlite3, os
db = sqlite3.connect(os.path.expanduser('~/Library/Application Support/mcp-memory/sqlite_vec.db'))
print(f'Soft-deleted: {db.execute(\"SELECT COUNT(*) FROM memories WHERE deleted_at IS NOT NULL\").fetchone()[0]}')
"
```

To restore recent deletions, see `tests/README.md` detailed recovery section or contact maintainers.

## Additional Resources

- **CLAUDE.md** - Development guidelines for Claude Code
- **scripts/README.md** - Available scripts and tools
- **.claude/directives/** - Topic-specific development guides

## Summary

**Golden Rule:** Always use `temp_db_path` fixture. Never hardcode production paths in tests.

The multi-layer safety system protects production data, but correct test implementation is the first line of defense.
