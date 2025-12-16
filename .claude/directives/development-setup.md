# Development Setup - Critical Guidelines

## Editable Install (MANDATORY)

**⚠️ ALWAYS use editable install** to avoid stale package issues:

```bash
# REQUIRED for development
pip install -e .  # or: uv pip install -e .

# Verify
pip show mcp-memory-service | grep Location
# Should show: .../mcp-memory-service/src
# NOT: .../site-packages
```

**Why:** MCP servers load from `site-packages`, not source files. Without `-e`, source changes won't be reflected until reinstall.

**Common symptom**: Code shows v8.23.0 but server reports v8.5.3

## Development Workflow

1. Clone repo: `git clone https://github.com/doobidoo/mcp-memory-service.git`
2. Create venv: `python -m venv venv && source venv/bin/activate`
3. **Editable install**: `pip install -e .` ← CRITICAL STEP
4. Verify: `python -c "import mcp_memory_service; print(mcp_memory_service.__version__)"`
5. Start coding - changes take effect after server restart (no reinstall needed)

## Version Mismatch Detection

```bash
# Quick check script
python scripts/validation/check_dev_setup.py

# Manual verification (both should match)
grep '__version__' src/mcp_memory_service/__init__.py
python -c "import mcp_memory_service; print(mcp_memory_service.__version__)"
```

## Fix Stale Installation

```bash
pip uninstall mcp-memory-service
pip install -e .

# Restart MCP servers in Claude Code
# Run: /mcp
```
