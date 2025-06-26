# MCP Memory Service Scripts

This directory contains utility scripts for maintaining and managing the MCP Memory Service.

## Directory Structure

- **`migrations/`** - Database migration scripts for schema changes and data cleanup
  - `cleanup_mcp_timestamps.py` - Fixes timestamp field proliferation issue
  - `verify_mcp_timestamps.py` - Verifies database timestamp consistency
  - `TIMESTAMP_CLEANUP_README.md` - Documentation for timestamp cleanup

## Usage

All scripts should be run from the repository root or with appropriate path adjustments.

## Adding New Scripts

When adding new maintenance scripts:
1. Create appropriate subdirectories for organization
2. Include clear documentation
3. Always implement backup/safety mechanisms for data-modifying scripts
4. Add verification scripts where appropriate
