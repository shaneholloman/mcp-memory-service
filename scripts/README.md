# MCP Memory Service Scripts

This directory contains utility scripts for maintaining and managing the MCP Memory Service.

## Directory Structure

- **`migrations/`** - Database migration scripts for schema changes and data cleanup
  - `cleanup_mcp_timestamps.py` - Fixes timestamp field proliferation issue
  - `verify_mcp_timestamps.py` - Verifies database timestamp consistency
  - `TIMESTAMP_CLEANUP_README.md` - Documentation for timestamp cleanup

## Maintenance Scripts

### Documentation Link Checker

**`check_documentation_links.py`** - Comprehensive tool for validating internal documentation links

```bash
# Basic usage - check all links
python scripts/check_documentation_links.py

# Verbose mode - show all links (working and broken)
python scripts/check_documentation_links.py --verbose

# With fix suggestions for broken links
python scripts/check_documentation_links.py --fix-suggestions

# Different output formats
python scripts/check_documentation_links.py --format json
```

**Features:**
- ✅ Scans all markdown files in the repository
- ✅ Validates internal relative links only (skips external URLs)
- ✅ Provides detailed error reporting with target paths
- ✅ Suggests fixes for broken links based on similar filenames
- ✅ Multiple output formats (text, markdown, json)
- ✅ Exit codes for CI/CD integration (0 = success, 1 = broken links found)

**Use Cases:**
- Pre-commit validation
- Documentation maintenance
- CI/CD pipeline integration
- After repository restructuring

## Usage

All scripts should be run from the repository root or with appropriate path adjustments.

## Adding New Scripts

When adding new maintenance scripts:
1. Create appropriate subdirectories for organization
2. Include clear documentation
3. Always implement backup/safety mechanisms for data-modifying scripts
4. Add verification scripts where appropriate
