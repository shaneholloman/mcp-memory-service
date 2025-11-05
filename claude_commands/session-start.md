# Display Session Memory Context

Run the session-start memory awareness hook manually to display relevant memories, project context, and git analysis.

## What this does:

Executes the session-start.js hook to:
1. **Load Project Context**: Detect current project and framework
2. **Analyze Git History**: Review recent commits and changes
3. **Retrieve Relevant Memories**: Find memories related to current project
4. **Display Memory Context**: Show categorized memories:
   - 🔥 Recent Work
   - ⚠️ Current Problems
   - 📋 Additional Context

## Usage:

```bash
claude /session-start
```

## Windows Compatibility:

This command is specifically designed as a **Windows workaround** for the SessionStart hook bug (#160).

On Windows, SessionStart hooks cause Claude Code to hang indefinitely. This slash command provides the same functionality but can be triggered manually when you start a new session.

**Works on all platforms**: Windows, macOS, Linux

## When to use:

- At the start of each coding session
- When switching projects or contexts
- After compacting conversations to refresh memory context
- When you need to see what memories are available

## What you'll see:

```
🧠 Memory Hook → Initializing session awareness...
📂 Project: mcp-memory-service
💾 Storage: sqlite-vec (Connected) • 1968 memories • 15.37MB
📊 Git Context → 10 commits, 3 changelog entries

📚 Memory Search → Found 4 relevant memories (2 recent)

┌─ 🧠 Injected Memory Context → mcp-memory-service, FastAPI, Python
│
├─ 🔥 Recent Work:
│  ├─ MCP Memory Service v8.6... 📅 6d ago
│  └─ Session Summary - mcp-memory-service... 📅 6d ago
│
├─ ⚠️ Current Problems:
│  └─ Dream-Inspired Memory Consolidation... 📅 Oct 22
│
└─ 📋 Additional Context:
   └─ MCP Memory Service v8.5... 📅 Oct 22
```

## Alternative: Automatic Mid-Conversation Hook

Your UserPromptSubmit hook already runs automatically and retrieves memories when appropriate patterns are detected. This command is for when you want to **explicitly see** the memory context at session start.

## Technical Details:

- Runs: `node ~/.claude/hooks/core/session-start.js`
- HTTP endpoint: http://127.0.0.1:8000
- Protocol: HTTP (MCP fallback if HTTP unavailable)
- Performance: <2 seconds typical execution time

## Troubleshooting:

### Command not found
- Ensure hooks are installed: `ls ~/.claude/hooks/core/session-start.js`
- Reinstall: `cd claude-hooks && python install_hooks.py --basic`

### No memories displayed
- Check HTTP server is running: `curl http://127.0.0.1:8000/api/health`
- Verify hooks config: `cat ~/.claude/hooks/config.json`
- Check endpoint matches: Should be `http://127.0.0.1:8000`

### Error: Cannot find module
- **Windows**: Ensure path is quoted properly in hooks config
- Check Node.js installed: `node --version`
- Verify hook file exists at expected location

## Related:

- **GitHub Issue**: [#160 - Windows SessionStart hook bug](https://github.com/doobidoo/mcp-memory-service/issues/160)
- **Technical Analysis**: `claude-hooks/WINDOWS-SESSIONSTART-BUG.md`
- **Hook Documentation**: `claude-hooks/README.md`

---

**For Windows Users**: This is the **recommended workaround** for session initialization until the SessionStart hook bug is fixed in Claude Code core.
