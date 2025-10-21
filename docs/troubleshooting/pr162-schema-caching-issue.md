# PR #162 Fix Troubleshooting - Comma-Separated Tags Issue

## Issue
After PR #162 was merged (fixing support for comma-separated tags), users still saw error:
```
Input validation error: 'tag1,tag2,tag3' is not of type 'array'
```

## Root Cause Analysis

### What PR #162 Fixed
- **File**: `src/mcp_memory_service/server.py` lines 1320-1337
- **Fix**: Changed `tags` schema from requiring array to accepting `oneOf`:
  ```json
  "tags": {
    "oneOf": [
      {"type": "array", "items": {"type": "string"}},
      {"type": "string", "description": "Tags as comma-separated string"}
    ]
  }
  ```
- **Server Code**: Lines 2076-2081 normalize tags from string to array

### Why Error Persisted

1. **MCP Client Schema Caching**: Claude Code's MCP client caches tool schemas when it first connects
2. **Stale Server Processes**: MCP server processes continued running with old code:
   - Old process started at 10:43 (before git pull/merge)
   - New code pulled but server not restarted
3. **HTTP vs MCP Servers**: HTTP server restart doesn't affect MCP server processes
4. **Validation Layer**: JSONSchema validation happens **client-side** before request reaches server

## Evidence

### Server Processes Found
```
PID 68270: Started 10:43 (OLD - before PR merge)
PID 70013: Started 10:44 (OLD - before PR merge)
PID 117228: HTTP server restarted 11:51 (NEW - has fix)
```

### Error Source
- Error message format: `'value' is not of type 'array'`
- Source: `jsonschema` library (Python package)
- Layer: **Client-side validation** in Claude Code's MCP client

### Timeline
- **Oct 20, 2025 17:22**: PR #162 merged
- **Oct 21, 2025 10:48**: HTTP server started (unknown which version)
- **Oct 21, 2025 11:51**: HTTP server restarted with latest code
- **Oct 21, 2025 11:5x**: MCP reconnection in Claude Code

## Solution

### Immediate Fix
```bash
# In Claude Code, run:
/mcp

# This forces reconnection and:
# 1. Terminates old MCP server process
# 2. Starts new MCP server with latest code
# 3. Re-fetches tool schemas (including updated tags schema)
# 4. Clears client-side schema cache
```

### Verification Steps
After reconnection:
1. Check MCP server process started after git pull/merge time
2. Test with comma-separated tags: `{"tags": "tag1,tag2,tag3"}`
3. Test with array tags: `{"tags": ["tag1", "tag2", "tag3"]}`
4. Both should work without validation errors

## Prevention for Future PRs

### When Schema Changes are Merged
1. **Restart HTTP Server** (if using HTTP protocol):
   ```bash
   systemctl --user restart mcp-memory-http.service
   ```

2. **Reconnect MCP in Claude Code** (if using MCP protocol):
   ```
   /mcp
   ```
   Or fully restart Claude Code application

3. **Check Process Age**:
   ```bash
   ps aux | grep "memory.*server" | grep -v grep
   # Ensure start time is AFTER the git pull
   ```

### For Contributors
When merging PRs that change tool schemas:
1. Add note in PR description: "Requires MCP reconnection after deployment"
2. Update CHANGELOG with reconnection instructions
3. Consider automated server restart in deployment scripts

## Key Learnings

1. **Client-side validation**: MCP clients validate against cached schemas
2. **Multiple server processes**: HTTP and MCP servers are separate
3. **Schema propagation**: New schemas only available after reconnection
4. **Git pull != Code reload**: Running processes don't auto-reload
5. **Troubleshooting order**:
   - Check PR merge time
   - Check server process start time
   - Check git log on running server's code
   - Restart/reconnect if process predates code change

## Related Files
- Server schema: `src/mcp_memory_service/server.py:1320-1337`
- Server handler: `src/mcp_memory_service/server.py:2076-2081`
- PR: https://github.com/doobidoo/mcp-memory-service/pull/162
- Issue: (original issue that reported comma-separated tags not working)

## Quick Reference Card

### Symptom
✗ Error after merged PR: "Input validation error: 'X' is not of type 'Y'"

### Diagnosis
```bash
# 1. Check when PR was merged
gh pr view <PR_NUMBER> --json mergedAt

# 2. Check when server process started
ps aux | grep "memory.*server" | grep -v grep

# 3. Compare times - if server started BEFORE merge, that's the issue
```

### Fix
```bash
# In Claude Code:
/mcp

# Or restart systemd service:
systemctl --user restart mcp-memory-http.service
```

### Verify
```bash
# Check new server process exists with recent start time
ps aux | grep "memory.*server" | grep -v grep

# Test the fixed functionality
```

## Date
- Analyzed: October 21, 2025
- PR Merged: October 20, 2025 17:22 UTC
- Issue: Schema caching in MCP client after schema update
