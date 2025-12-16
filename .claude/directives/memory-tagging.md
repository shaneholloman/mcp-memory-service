# Memory Tagging Directive

## CRITICAL: Always Tag Memories with Project Name

When storing memories manually for this project, **ALWAYS** include `mcp-memory-service` as the **first tag**.

### Why This Matters
- Session-end hooks automatically add `projectContext.name` (line 222 in session-end.js)
- Manual storage has NO hook context - you must add the tag explicitly
- Without the tag, memories are excluded from:
  - SessionStart hook project context retrieval
  - Tag-based searches
  - Git-aware context integration
  - Cross-PC sync queries

### Correct Usage

```bash
# ✅ CORRECT - Always include project tag first
claude /memory-store "architecture decision..." \
  --tags "mcp-memory-service,architecture,graph-database"

# ✅ CORRECT - MCP tool with project tag
store_memory(
    content="configuration baseline...",
    metadata={"tags": "mcp-memory-service,configuration,hybrid-backend"}
)

# ❌ WRONG - Missing project tag
claude /memory-store "bug fix..." --tags "bug-fix,troubleshooting"
```

### Tag Priority Order (v8.48.2+)

1. **Project identifier** - `mcp-memory-service` (REQUIRED)
2. **Content category** - `architecture`, `configuration`, `bug-fix`, `release`, etc.
3. **Specifics** - `graph-database`, `hybrid-backend`, `v8.51.0`, etc.

### Standard Categories

| Category | Use Case | Example |
|----------|----------|---------|
| `architecture` | Design decisions, system structure | `mcp-memory-service,architecture,graph-database` |
| `configuration` | Setup, environment, settings | `mcp-memory-service,configuration,multi-pc` |
| `performance` | Optimization, benchmarks | `mcp-memory-service,performance,30x-improvement` |
| `bug-fix` | Issue resolution | `mcp-memory-service,bug-fix,database-lock` |
| `release` | Version management | `mcp-memory-service,release,v8.51.0` |
| `documentation` | Guides, references | `mcp-memory-service,documentation,setup-guide` |

## Enforcement

This directive is **mandatory** for all manual memory storage operations in this project.
