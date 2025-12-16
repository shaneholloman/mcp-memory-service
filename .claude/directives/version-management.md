# Version Management - Release Workflow

## ⚠️ CRITICAL: Always Use github-release-manager Agent

**NEVER do manual releases** (major, minor, patch, or hotfixes). Manual workflows miss steps and are error-prone.

## Four-File Version Bump Procedure

1. Update `src/mcp_memory_service/__init__.py` (line 50: `__version__ = "X.Y.Z"`)
2. Update `pyproject.toml` (line 7: `version = "X.Y.Z"`)
3. Update `README.md` (line 19: Latest Release section)
4. Run `uv lock` to update dependency lock file
5. Commit all four files together

## Release Workflow

```bash
# ALWAYS use the agent
@agent github-release-manager "Check if we need a release"
@agent github-release-manager "Create release for v8.20.0"
```

**Agent ensures:**
- README.md updates
- GitHub Release creation
- Proper issue tracking
- CHANGELOG.md formatting
- Workflow verification (Docker Publish, HTTP-MCP Bridge)

## Hotfix Workflow (Critical Bugs)

- **Speed target**: 8-10 minutes from bug report to release (achievable with AI assistance)
- **Process**: Fix → Test → Four-file bump → Commit → github-release-manager agent
- **Issue management**: Post detailed root cause analysis, don't close until user confirms fix works
- **Example**: v8.20.1 (8 minutes: bug report → fix → release → user notification)

## Why Agent-First?

**Manual v8.20.1** (❌):
- Forgot README.md update
- Incomplete GitHub Release
- Missed workflow verification

**With agent v8.20.1** (✅):
- All files updated
- Proper release created
- Complete documentation

**Lesson**: Always use agents, even for "simple" hotfixes
