# Obsolete Workflows Archive

This directory contains historical documentation of workflows that have been superseded by better, automated solutions.

## Contents

### `load_memory_context.md` (August 2025)

**Original Purpose**: Manual prompt with curl commands to load memory context at Claude Code session start.

**Why Obsolete**: Completely superseded by Natural Memory Triggers v7.1.3+ (September 2025).

#### Evolution Timeline

**Phase 1: Manual Loading (Aug 2025)** ❌ OBSOLETE
```bash
# Users had to manually run curl commands and paste output
curl -k -s -X POST https://server:8443/mcp \
  -H "Authorization: Bearer token" \
  -d '{"method": "tools/call", "params": {...}}'
```
**Problems**: Manual, error-prone, required copy-paste, network configuration complexity

**Phase 2: SessionStart Hooks (Aug-Sept 2025)** ✅ IMPROVED
- Automatic memory retrieval at session start
- Project detection and intelligent scoring
- Git-aware context integration

**Phase 3: Natural Memory Triggers (Sept 2025+)** ✅ PRODUCTION
- 85%+ trigger accuracy with semantic pattern detection
- Multi-tier performance optimization (50ms → 500ms tiers)
- CLI management system for real-time configuration
- Adaptive learning based on usage patterns

**Phase 4: Team Collaboration (v7.0.0+)** ✅ NETWORK DISTRIBUTION
- OAuth 2.1 Dynamic Client Registration
- Claude Code HTTP transport
- Zero-configuration team collaboration
- Better than manual network sharing

#### Current Solution

Instead of manual prompts, users now get:

```bash
# One-time installation
cd claude-hooks && python install_hooks.py --natural-triggers

# That's it! Automatic context injection from now on
```

**Benefits**:
- ✅ Zero manual steps per session
- ✅ 85%+ trigger accuracy
- ✅ Intelligent pattern detection
- ✅ Multi-tier performance
- ✅ Team collaboration via OAuth

#### Historical Value

This archive demonstrates:
1. **UX Evolution**: Manual → Semi-automatic → Fully automatic
2. **Problem Recognition**: Identifying pain points (manual commands)
3. **Iterative Improvement**: Each phase solved previous limitations
4. **User-Centric Design**: Continuously reducing friction

#### Migration

If you're still using manual prompts:

**Old Approach** (manual):
```bash
curl -k -s -X POST https://server:8443/mcp ... | jq -r '.result.content[0].text'
```

**New Approach** (automatic):
```bash
# Install once
python claude-hooks/install_hooks.py --natural-triggers

# Enjoy automatic context injection forever
```

See: [Natural Memory Triggers Guide](https://github.com/doobidoo/mcp-memory-service/wiki/Natural-Memory-Triggers-v7.1.0)

---

**Last Updated**: October 25, 2025
**Status**: Archived for historical reference only
