# Awareness hooks should detect and use existing Claude Code MCP configuration instead of duplicating server setup

## 🎯 **Problem Description**

The awareness hooks installer (`claude-hooks/install_hooks.py`) currently violates the DRY principle by maintaining a separate MCP server configuration instead of leveraging the existing Claude Code MCP setup. This creates several issues:

### **Current Issues:**

1. **Configuration Duplication**: Hooks maintain separate `serverCommand` config in `~/.claude/hooks/config.json` while Claude Code already has the memory server configured via `claude mcp add memory`

2. **No MCP Awareness**: The installer doesn't detect or validate existing Claude Code MCP configurations, leading to:
   - Duplicate server processes
   - Configuration drift between Claude Code and hooks
   - Inconsistent backend configurations (Cloudflare vs SQLite vs ChromaDB)

3. **Complex Maintenance**: Updates require changing multiple configuration files instead of maintaining a single source of truth

4. **Poor User Experience**: Users must manually ensure hooks configuration matches their Claude Code MCP setup

### **Example of Current Problem:**

**Claude Code MCP Configuration:**
```bash
$ claude mcp get memory
memory:
  Scope: Local config (private to you in this project)
  Status: ✓ Connected
  Type: stdio
  Command: uv run python -m mcp_memory_service.server
  Environment: [Cloudflare backend configuration]
```

**Hooks Configuration (Separate):**
```json
{
  "memoryService": {
    "mcp": {
      "serverCommand": ["uv", "run", "python", "-m", "mcp_memory_service.server"],
      "serverWorkingDir": "C:\\REPOSITORIES\\mcp-memory-service"
    }
  }
}
```

This results in **two separate memory service processes** with potentially different backend configurations.

## 🚀 **Proposed Solution**

### **Phase 1: Smart MCP Detection**

Enhance `install_hooks.py` to detect existing Claude Code MCP configurations:

```python
def detect_claude_mcp_configuration(self) -> Optional[Dict]:
    """Detect existing Claude Code MCP memory server configuration."""
    try:
        # Parse `claude mcp get memory` output
        result = subprocess.run(['claude', 'mcp', 'get', 'memory'],
                               capture_output=True, text=True)
        if result.returncode == 0:
            return self.parse_mcp_output(result.stdout)
    except Exception:
        pass
    return None

def validate_mcp_prerequisites(self) -> Tuple[bool, List[str]]:
    """Validate that MCP memory service is properly configured."""
    issues = []

    # Check if memory server exists in Claude Code
    # Verify server responds to health checks
    # Validate backend configuration consistency

    return len(issues) == 0, issues
```

### **Phase 2: DRY Configuration Generation**

Generate hooks configuration based on detected MCP setup:

```python
def generate_hooks_config(self, detected_mcp: Optional[Dict]) -> Dict:
    """Generate hooks config based on detected MCP setup."""
    if detected_mcp:
        # Use existing MCP server reference (DRY approach)
        return {
            "memoryService": {
                "protocol": "mcp",
                "preferredProtocol": "mcp",
                "mcp": {
                    "useExistingServer": True,
                    "serverName": "memory",  # Reference existing Claude Code server
                    "fallbackToHttp": True
                }
            }
        }
    else:
        # Fallback to independent setup
        return self.generate_legacy_config()
```

### **Phase 3: Enhanced Memory Client**

Update `utilities/memory-client.js` to support existing server connections:

```javascript
class MemoryClient {
    async connectToExistingMCP(serverName) {
        // Connect to existing Claude Code MCP server
        // Avoid spawning duplicate processes
        // Use shared connection mechanism
    }
}
```

### **Phase 4: Improved Installation UX**

```bash
🔍 Detecting existing MCP configuration...
✅ Found memory server: uv run python -m mcp_memory_service.server
✅ Backend: Cloudflare (healthy)
✅ Connection: Local stdio

📋 Installation Options:
  [1] Use existing MCP setup (recommended) - DRY principle ✨
  [2] Create independent hooks setup - legacy fallback

Choose option [1]:
```

## 🎯 **Expected Benefits**

1. **DRY Principle**: Single source of truth for MCP configuration
2. **Reduced Complexity**: No duplicate server processes
3. **Better Performance**: Single memory service instance
4. **Easier Maintenance**: Updates only require changing Claude Code MCP config
5. **Better UX**: Automatic detection and configuration
6. **Fewer Bugs**: Eliminates configuration drift issues

## 🧪 **Testing Requirements**

- [ ] Fresh installation with no existing MCP
- [ ] Installation with existing Cloudflare backend
- [ ] Installation with existing SQLite backend
- [ ] Installation with existing ChromaDB backend
- [ ] Configuration migration from legacy setup
- [ ] Fallback when MCP detection fails

## 🔧 **Implementation Notes**

### **Backward Compatibility**
- Support existing hooks configurations
- Provide migration path from `serverCommand` to `serverName` approach
- Graceful fallback when detection fails

### **Prerequisites Detection**
The installer should validate:
1. Claude Code CLI availability (`claude --help`)
2. Memory server existence (`claude mcp get memory`)
3. Server health and backend configuration
4. Environment consistency

## 📚 **Related Documentation**

- Update README.md with MCP prerequisites section
- Create wiki page: "MCP Configuration Best Practices"
- Add troubleshooting guide for configuration conflicts

---

## 🏷️ **Labels**
- `enhancement`
- `architecture`
- `DRY-principle`
- `configuration`
- `claude-code-integration`

## 🎯 **Priority**
**High** - This affects user experience, system architecture, and maintenance overhead.