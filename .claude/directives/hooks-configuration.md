# Claude Code Hooks Configuration - Complete Guide

## Natural Memory Triggers v7.1.3

**Intelligent automatic memory retrieval** with advanced semantic analysis and multi-tier performance optimization.

### Installation

```bash
# Zero-restart required
cd claude-hooks && python install_hooks.py --natural-triggers

# CLI Management
node ~/.claude/hooks/memory-mode-controller.js status
node ~/.claude/hooks/memory-mode-controller.js profile balanced
node ~/.claude/hooks/memory-mode-controller.js sensitivity 0.6
```

### Key Features

- ✅ **85%+ trigger accuracy** for memory-seeking pattern detection
- ✅ **Multi-tier processing**: 50ms instant → 150ms fast → 500ms intensive
- ✅ **CLI management system** for real-time configuration without restart
- ✅ **Git-aware context** integration for enhanced memory relevance
- ✅ **Adaptive learning** based on user preferences and usage patterns

### Configuration File

**Location**: `~/.claude/hooks/config.json`

```json
{
  "naturalTriggers": {
    "enabled": true,
    "triggerThreshold": 0.6,
    "cooldownPeriod": 30000,
    "maxMemoriesPerTrigger": 5
  },
  "performance": {
    "defaultProfile": "balanced",
    "enableMonitoring": true,
    "autoAdjust": true
  }
}
```

### Performance Profiles

| Profile | Latency | Tiers Active | Use Case |
|---------|---------|-------------|----------|
| **speed_focused** | <100ms | Instant only | Minimal memory awareness for speed |
| **balanced** | <200ms | Instant + Fast | Optimal for general development (recommended) |
| **memory_aware** | <500ms | All tiers | Maximum context awareness for complex work |
| **adaptive** | Dynamic | Auto-adjusts | Based on usage patterns and feedback |

### Context-Provider Integration 🆕

**Rule-based context management** that complements Natural Memory Triggers with structured, project-specific patterns.

#### Commands
```bash
mcp context list                    # List available contexts
mcp context status                  # Check session initialization status
mcp context optimize                # Get optimization suggestions
```

#### Available Contexts

**1. Python MCP Memory Service Context** (`python_mcp_memory`)
- Project-specific patterns for FastAPI, MCP protocol, storage backends
- Auto-store: MCP protocol changes, backend configs, performance optimizations
- Auto-retrieve: Troubleshooting, setup queries, implementation examples
- Smart tagging: Auto-detects tools (fastapi, cloudflare, sqlite-vec, hybrid)

**2. Release Workflow Context** (`mcp_memory_release_workflow`)
- PR Review Cycle: Iterative Gemini Code Assist workflow
- Version Management: Four-file procedure
- CHANGELOG Management: Format guidelines, conflict resolution
- Issue Tracking: Auto-detection, post-release workflow, smart closing comments

### Auto-Store Patterns

- **Technical**: `MCP protocol`, `tool handler`, `storage backend switch`
- **Configuration**: `cloudflare configuration`, `hybrid backend setup`
- **Release Workflow**: `merged PR`, `gemini review`, `created tag`, `version bump`
- **Documentation**: `updated CHANGELOG`, `wiki page created`
- **Issue Tracking**: `fixes #`, `closes #`, `resolves #`

### Auto-Retrieve Patterns

- **Troubleshooting**: `cloudflare backend error`, `MCP client connection`
- **Setup**: `backend configuration`, `environment setup`
- **Development**: `MCP handler example`, `API endpoint pattern`
- **Release Workflow**: `how to release`, `PR workflow`, `version bump procedure`
- **Issue Management**: `review open issues`, `what issues fixed`, `can we close`

### Windows SessionStart Hook ✅

**FIXED** (Claude Code 2.0.76+, December 2025): SessionStart hooks now work correctly on Windows.

The subprocess lifecycle bug ([Issue #160](https://github.com/doobidoo/mcp-memory-service/issues/160) - CLOSED) was fixed in Claude Code core.

**No workaround needed** - SessionStart hooks can be enabled normally on Windows.

### Hook Configuration

**Session-end hooks:**
- Trigger on `/exit`, terminal close (NOT Ctrl+C)
- Require 100+ characters, confidence > 0.1
- Memory creation: topics, decisions, insights, code changes

**SessionStart hooks:**
- Project detection and memory injection
- Git-aware context analysis
- Recent work prioritization

See [docs/troubleshooting/hooks-quick-reference.md](../../docs/troubleshooting/hooks-quick-reference.md) for troubleshooting.

### Legacy Hook Configuration

**Dual Protocol Configuration** (v7.0.0 - superseded by Natural Memory Triggers):
See [docs/legacy/dual-protocol-hooks.md](../../docs/legacy/dual-protocol-hooks.md) for historical reference.
