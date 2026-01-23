# Manual Testing Scripts

This directory contains **manual test scripts** that are NOT run by pytest.

## Important Notes

⚠️  **These scripts use production database paths intentionally for manual testing.**

- They are kept separate from the `tests/` directory to prevent pytest discovery
- They are useful for manual verification and debugging
- DO NOT move these back to `tests/` directory

## Scripts

### Production Path Scripts (Moved from tests/)

- **manual_memory_test.py** - Basic memory operations test (uses production DB)
- **manual_integration_test.py** - Integration testing (uses production DB)

### Other Manual Tests

- Various test scripts for specific features and scenarios
- See individual files for documentation

## Usage

Run these scripts directly with Python, not via pytest:

```bash
# Example
python scripts/testing/manual_memory_test.py
```

## Why These Are Separate

These scripts were moved from `tests/` to `scripts/testing/` because:

1. They hardcode production database paths (`~/Library/Application Support/mcp-memory/`)
2. They are standalone scripts with `async def main()`, not pytest tests
3. Having them in `tests/` could cause pytest cleanup hooks to delete production data
4. They are intended for manual verification, not automated testing

## For Automated Testing

If you need automated tests, use the fixtures in `tests/conftest.py`:

```python
def test_something(temp_db_path):
    """Uses isolated temporary database."""
    os.environ["MCP_MEMORY_SQLITE_PATH"] = str(temp_db_path / "test.db")
    # ... test code
```

See `tests/README.md` for complete testing guidelines.
