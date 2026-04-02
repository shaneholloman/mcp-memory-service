# /release — Full Release Cycle

Execute the complete release workflow for mcp-memory-service by delegating to the `github-release-manager` agent.

## What This Command Does

Spawn the `github-release-manager` agent to handle the entire release lifecycle:

1. **Pre-Release**: List open PRs, merge approved ones, verify CI green on main
2. **Version Bump**: Determine bump type (MAJOR/MINOR/PATCH) from PR labels, update `_version.py`, `pyproject.toml`, `README.md`, `uv.lock`
3. **Documentation**: Update CHANGELOG.md (move [Unreleased] → version entry), README.md ("Latest Release"), CLAUDE.md (version callout)
4. **Landing Page**: Update `docs/index.html` for MINOR/MAJOR releases only — version badge, test count, re-publish to here.now
5. **Release Creation**: Git tag on main, GitHub Release with notes + contributor recognition
6. **Post-Release**: Clean up branches, close resolved issues, verify CI/CD workflows (PyPI auto-publishes via tag push)

## Rules

- **NEVER manually edit version files** — the agent synchronizes all files atomically
- **CI must be green** before any merge or release — stop if red
- **All review comments resolved** before merge — no `--admin` bypass for unresolved feedback
- **Landing page**: MINOR/MAJOR only, skip for PATCH
- **Save release summary** to MCP Memory with tags: `mcp-memory-service`, `release`, `v<VERSION>`

## Invocation

Spawn `github-release-manager` agent with context about what triggered the release (merged PRs, completed features, fixed issues).
