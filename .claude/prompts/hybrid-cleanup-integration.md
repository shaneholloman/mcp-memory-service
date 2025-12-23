# Claude Code Task: Hybrid Association Cleanup Script Integration

## Context

We just solved a critical issue with multi-PC sync in the MCP Memory Service hybrid backend. The problem was:

1. Association memories were only deleted locally on one PC
2. Cloudflare D1 still had them
3. Drift-sync mechanism (`hybrid.py:632-750`) synced them back to all PCs

The solution is a new script `cleanup_association_memories_hybrid.py` that cleans BOTH Cloudflare AND local SQLite in the correct order.

## Current State

- Script already exists at: `scripts/maintenance/cleanup_association_memories_hybrid.py`
- It was created during a troubleshooting session and works correctly
- Tested successfully: Deleted 1,441 association memories from both Cloudflare D1 and local SQLite

## Tasks

### 1. Review and Polish the Script

Check `scripts/maintenance/cleanup_association_memories_hybrid.py`:
- Add proper docstrings and comments
- Ensure error handling is robust (especially for Vectorize API - it failed with JSON decode error)
- Add `--skip-vectorize` flag option since Vectorize cleanup is optional (orphaned vectors are harmless)
- Make sure it follows project coding standards

### 2. Update Documentation

Update `scripts/maintenance/README.md`:
- Add section for `cleanup_association_memories_hybrid.py`
- Explain when to use it vs the original `cleanup_association_memories.py`
- Document the multi-PC sync issue and why Cloudflare must be cleaned first

### 3. Update Migration Guide

Check/update `docs/migration/graph-migration-guide.md`:
- Add note about hybrid backend requiring the hybrid cleanup script
- Document the correct cleanup order for multi-PC setups

### 4. Add to CHANGELOG

Add entry for the new script under "Unreleased" or prepare for next version:

```markdown
### Added
- `cleanup_association_memories_hybrid.py` - Cleanup script for hybrid backend that removes association memories from both Cloudflare D1 and local SQLite, preventing multi-PC sync from restoring deleted associations
```

### 5. Consider Version Bump

If this is significant enough for a release:
- Current version check: `grep -r "__version__" src/mcp_memory_service/__init__.py`
- Determine if patch bump is warranted (e.g., v8.51.1 or v8.52.0)
- Use the GitHub Release Manager agent if releasing

## Key Technical Details

### The Problem (for documentation)

```
┌─────────────┐     sync      ┌─────────────┐     sync      ┌─────────────┐
│  Windows PC │ ◄──────────► │  Cloudflare │ ◄──────────► │  Linux PC   │
│ 1441 assocs │              │  D1 + Vec   │              │  0 assocs   │
└─────────────┘              └─────────────┘              └─────────────┘
       ↑                            ↑                            ↑
       └────────────────────────────┴────────────────────────────┘
                    Drift-sync brings them back!
```

### The Solution

1. Delete from Cloudflare D1 FIRST (prevents sync from restoring)
2. Delete from Cloudflare Vectorize (optional, orphaned vectors are harmless)
3. Delete from local SQLite
4. Run VACUUM to reclaim space
5. Other PCs auto-sync the deletion

### Script Usage

```bash
# Preview (dry-run)
python scripts/maintenance/cleanup_association_memories_hybrid.py --dry-run

# Execute cleanup
python scripts/maintenance/cleanup_association_memories_hybrid.py --apply

# Only clean Cloudflare (useful if running from any PC)
python scripts/maintenance/cleanup_association_memories_hybrid.py --apply --cloudflare-only

# Only clean local (if Cloudflare already cleaned)
python scripts/maintenance/cleanup_association_memories_hybrid.py --apply --local-only
```

### Prerequisites

- `MCP_GRAPH_STORAGE_MODE=graph_only` should be set (v8.51.0+)
- Graph table must exist (run `backfill_graph_table.py` first if needed)
- Cloudflare credentials in environment

## Files to Check/Modify

1. `scripts/maintenance/cleanup_association_memories_hybrid.py` - Polish the script
2. `scripts/maintenance/README.md` - Add documentation
3. `docs/migration/graph-migration-guide.md` - Update migration docs
4. `CHANGELOG.md` - Add entry
5. `src/mcp_memory_service/__init__.py` - Version bump if releasing

## Memory Reference

This issue and solution was documented in memory with tags:
- `mcp-memory-service`
- `hybrid-backend`
- `multi-pc-sync`
- `cloudflare`
- `cleanup`
- `graph-migration`

Search memory for "Hybrid Association Memory Cleanup" for full context.
