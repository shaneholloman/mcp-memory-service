# macOS Memory Hooks Investigation

## Issue
Memory awareness hooks may work differently on macOS vs Linux when using MCP protocol.

## Current Linux Behavior (Manjaro)
- **Problem**: Hooks try to spawn duplicate MCP server via `MCPClient(serverCommand)`
- **Symptom**: Connection timeout when hooks execute
- **Root Cause**: Claude Code already has MCP server on stdio, can't have two servers on same streams
- **Current Workaround**: HTTP fallback (requires separate HTTP server on port 8443)

## Hypothesis: macOS May Work Differently
User reports hooks work on macOS without HTTP fallback. Possible reasons:
1. macOS Claude Code may provide hooks access to existing MCP connection
2. Different process/stdio handling on macOS vs Linux
3. `useExistingServer: true` config may actually work on macOS

## Investigation Needed (On MacBook)

### Test 1: MCP-Only Configuration
```json
{
  "memoryService": {
    "protocol": "mcp",
    "preferredProtocol": "mcp",
    "mcp": {
      "useExistingServer": true,
      "serverName": "memory"
    }
  }
}
```

**Expected on macOS (if hypothesis correct):**
- ✅ Hooks connect successfully
- ✅ No duplicate server spawned
- ✅ Memory context injected on session start

**Expected on Linux (current behavior):**
- ❌ Connection timeout
- ❌ Multiple server processes spawn
- ❌ Fallback to HTTP needed

### Test 2: Check Memory Client Behavior
1. Run hook manually: `node ~/.claude/hooks/core/session-start.js`
2. Check process list: Does it spawn new `memory server` process?
3. Monitor connection: Does it timeout or succeed?

### Test 3: Platform Comparison
```bash
# On macOS
ps aux | grep "memory server"  # How many instances?
node ~/.claude/hooks/core/session-start.js  # Does it work?

# On Linux (current)
ps aux | grep "memory server"  # Multiple instances!
node ~/.claude/hooks/core/session-start.js  # Times out!
```

## Files to Check
- `claude-hooks/utilities/memory-client.js` - MCP connection logic
- `claude-hooks/utilities/mcp-client.js` - Server spawning code
- `claude-hooks/install_hooks.py` - Config generation (line 268-273: useExistingServer)

## Next Steps
1. Test on MacBook with MCP-only config
2. If works on macOS: investigate platform-specific differences
3. Document proper cross-platform solution
4. Update hooks to work consistently on both platforms

## Current Status
- **Linux**: Requires HTTP fallback (confirmed working)
- **macOS**: TBD - needs verification
- **Goal**: Understand why different, achieve consistent behavior

---
Created: 2025-09-30
Platform: Linux (Manjaro)
Issue: Hooks/MCP connection conflict
