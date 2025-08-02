# Claude Code Commands - Complete Wiki Guide

*This content is designed for the GitHub Wiki. Copy and paste sections as needed.*

---

## Home Page Content

### MCP Memory Service - Claude Code Commands

**Transform your Claude Code experience with persistent memory capabilities!**

The MCP Memory Service now offers **conversational Claude Code commands** that provide direct access to powerful memory operations without any MCP server configuration.

#### 🚀 Quick Start
```bash
git clone https://github.com/doobidoo/mcp-memory-service.git
cd mcp-memory-service
python install.py --install-claude-commands
claude /memory-health  # Test it works!
```

#### 📚 Wiki Contents
- **[Installation Guide](#installation-guide)** - Complete setup instructions
- **[Command Reference](#command-reference)** - All 5 commands with examples
- **[Usage Examples](#usage-examples)** - Real-world workflows
- **[Commands vs MCP Server](#commands-vs-mcp-server)** - Which approach to choose
- **[Troubleshooting](#troubleshooting)** - Common issues and solutions
- **[Advanced Features](#advanced-features)** - Power user capabilities

---

## Installation Guide

### Prerequisites
- ✅ Claude Code CLI installed and working (`claude --version`)
- ✅ Python 3.10+ with pip
- ✅ Git for cloning the repository

### Method 1: Integrated Installation (Recommended)
```bash
# Clone the repository
git clone https://github.com/doobidoo/mcp-memory-service.git
cd mcp-memory-service

# Install with Claude Code commands
python install.py --install-claude-commands
```

**What this does:**
- Detects your system and optimizes installation
- Installs MCP Memory Service with best backend for your hardware
- Automatically detects Claude Code CLI
- Installs 5 conversational memory commands
- Creates backup of existing commands
- Tests everything to ensure it works

### Method 2: Commands Only
```bash
# If you already have MCP Memory Service installed
python scripts/claude_commands_utils.py

# Test installation
python scripts/claude_commands_utils.py --test
```

### Method 3: Manual Installation
```bash
# Install commands to specific location
cp claude_commands/*.md ~/.claude/commands/

# Verify installation
ls ~/.claude/commands/memory-*.md
```

### Installation Options
- `--skip-claude-commands-prompt` - Skip interactive prompts
- `--install-claude-commands` - Force install commands
- See [Installation Master Guide](../installation/master-guide.md) for all options

---

## Command Reference

### `/memory-store` - Store Information with Context

**Purpose**: Store information in your memory service with automatic context detection and smart tagging.

**Basic Usage**:
```bash
claude /memory-store "Important architectural decision about database backend"
```

**Advanced Usage**:
```bash
claude /memory-store --tags "decision,architecture" "We chose SQLite-vec for performance reasons"
claude /memory-store --type "note" --project "my-app" "Remember to update Docker config"
claude /memory-store --private "Sensitive information about deployment"
```

**Arguments**:
- `content` - The information to store (required)
- `--tags "tag1,tag2"` - Explicit tags to add
- `--type "note|decision|task|reference"` - Memory type classification
- `--project "name"` - Override automatic project detection
- `--private` - Mark as private/sensitive content

**Automatic Features**:
- ✅ Project context detection from current directory
- ✅ Git repository information capture
- ✅ Smart tag generation based on file types and patterns
- ✅ Timestamp and session metadata

---

### `/memory-recall` - Time-based Memory Retrieval

**Purpose**: Retrieve memories using natural language time expressions and contextual queries.

**Basic Usage**:
```bash
claude /memory-recall "what did we decide about the database last week?"
```

**Time Expression Examples**:
```bash
claude /memory-recall "yesterday's architectural decisions"
claude /memory-recall "memories from when we were working on authentication"
claude /memory-recall "what happened two months ago?"
claude /memory-recall "decisions made last Tuesday morning"
```

**Advanced Usage**:
```bash
claude /memory-recall --project "mcp-memory-service" "last month's progress"
claude /memory-recall --limit 20 "recent development decisions"
claude /memory-recall --tags "architecture" "planning from last week"
```

**Arguments**:
- `query` - Time-based or contextual query (required)
- `--limit N` - Maximum memories to retrieve (default: 10)
- `--project "name"` - Filter by specific project
- `--tags "tag1,tag2"` - Additional tag filtering
- `--type "note|decision|task"` - Filter by memory type
- `--include-context` - Show full session context

**Supported Time Expressions**:
- **Relative**: "yesterday", "last week", "two days ago", "this month"
- **Seasonal**: "last summer", "this winter", "spring 2024"
- **Event-based**: "before the refactor", "since we switched databases"
- **Specific**: "January 15th", "last Tuesday morning"

---

### `/memory-search` - Tag and Content Search

**Purpose**: Search through stored memories using tags, content keywords, and semantic similarity.

**Basic Usage**:
```bash
claude /memory-search --tags "architecture,database"
claude /memory-search "SQLite performance optimization"
```

**Search Types**:
```bash
# Tag-based search
claude /memory-search --tags "decision"
claude /memory-search --tags "architecture,performance,database"

# Content-based semantic search
claude /memory-search "database performance issues"
claude /memory-search "authentication implementation details"

# Combined search
claude /memory-search --tags "decision" --content "database backend"
claude /memory-search --project "my-app" --type "note" "configuration"
```

**Advanced Usage**:
```bash
claude /memory-search --limit 50 --min-score 0.8 "database optimization"
claude /memory-search --include-metadata --export "architecture decisions"
```

**Arguments**:
- `query` - Search query (content or primary terms)
- `--tags "tag1,tag2"` - Search by specific tags
- `--content "text"` - Explicit content search terms
- `--project "name"` - Filter by project name
- `--type "note|decision|task|reference"` - Filter by memory type
- `--limit N` - Maximum results (default: 20)
- `--min-score 0.X` - Minimum relevance threshold
- `--include-metadata` - Show full metadata
- `--export` - Export results to file

**Search Features**:
- ✅ Semantic similarity using embeddings
- ✅ Fuzzy matching for typos
- ✅ Tag-based filtering with partial matching
- ✅ Relevance scoring and ranking
- ✅ Context highlighting

---

### `/memory-context` - Session Context Integration

**Purpose**: Capture the current conversation and project context as a memory for future reference.

**Basic Usage**:
```bash
claude /memory-context
```

**With Custom Summary**:
```bash
claude /memory-context --summary "Architecture planning session for OAuth integration"
claude /memory-context --tags "planning,oauth" --type "session"
```

**Advanced Usage**:
```bash
claude /memory-context --include-files --include-commits
claude /memory-context --private --project "secret-project"
```

**Arguments**:
- `--summary "text"` - Custom session summary
- `--tags "tag1,tag2"` - Additional tags to apply
- `--type "session|meeting|planning|development"` - Context type
- `--include-files` - Include detailed file change information
- `--include-commits` - Include recent commit messages
- `--include-code` - Include code change snippets
- `--private` - Mark as private/sensitive content
- `--project "name"` - Override project detection

**Automatic Capture**:
- ✅ Conversation analysis and key topic extraction
- ✅ Git repository state and recent commits
- ✅ Current directory and project context
- ✅ Development session insights and decisions
- ✅ Action items and next steps identification

---

### `/memory-health` - Service Health and Diagnostics

**Purpose**: Check the health and status of your MCP Memory Service with comprehensive diagnostics.

**Basic Usage**:
```bash
claude /memory-health
```

**Detailed Diagnostics**:
```bash
claude /memory-health --detailed
claude /memory-health --test-operations
claude /memory-health --performance-test
```

**Advanced Features**:
```bash
claude /memory-health --check-backups
claude /memory-health --export-report
claude /memory-health --fix-issues
```

**Arguments**:
- `--detailed` - Show comprehensive diagnostics
- `--test-operations` - Test store/retrieve functionality
- `--check-backups` - Verify backup system health
- `--performance-test` - Run performance benchmarks
- `--export-report` - Save health report to file
- `--fix-issues` - Attempt automatic fixes
- `--quiet` - Show only critical issues

**Health Report Includes**:
- ✅ Service connectivity and response times
- ✅ Database health and statistics
- ✅ Storage backend configuration
- ✅ Memory count and usage patterns
- ✅ Performance metrics and bottlenecks
- ✅ Common issue detection and fixes

---

## Usage Examples

### Individual Developer Workflow
```bash
# Start your development day
claude /memory-context --summary "Starting work on user authentication feature"

# Store important decisions as you work
claude /memory-store --tags "auth,security" "Decided to use JWT tokens with 24h expiry"
claude /memory-store --tags "database,schema" "Added user_sessions table with token_hash column"

# Store configuration details
claude /memory-store --type "reference" "Auth0 client ID: app_123xyz (dev environment)"

# Later, recall what you decided
claude /memory-recall "what did we decide about authentication yesterday?"
claude /memory-search --tags "auth,jwt" 

# End of day - capture the session
claude /memory-context --summary "Completed JWT authentication implementation"
```

### Team Collaboration
```bash
# Before team meeting
claude /memory-recall "what architecture decisions did we make last week?"

# After team meeting
claude /memory-store --tags "team,decision" "Team agreed to migrate to microservices architecture by Q2"

# Reference team decisions
claude /memory-search --tags "team,decision" --limit 10
```

### Project Management
```bash
# Track project milestones
claude /memory-store --tags "milestone,completed" "Authentication module completed on schedule"

# Review project progress
claude /memory-recall "what milestones did we complete this month?"
claude /memory-search --tags "milestone" --type "note"

# Plan next sprint
claude /memory-recall "what blockers did we identify last week?"
```

### Learning and Documentation
```bash
# Store learning insights
claude /memory-store --tags "learning,react" "React useEffect cleanup prevents memory leaks"

# Build knowledge base
claude /memory-store --type "reference" --tags "cheatsheet,docker" "docker-compose up -d starts services in background"

# Recall knowledge
claude /memory-search "React hooks best practices"
claude /memory-recall "what did I learn about Docker last month?"
```

---

## Commands vs MCP Server

### When to Choose Commands

**✅ Perfect For**:
- Individual developers
- Quick setup (2 minutes to working)
- Direct command-line interface preference
- Automatic context detection needs
- Zero configuration requirements

**✅ Benefits**:
- Immediate access to memory operations
- Built-in help and guidance
- Context-aware project detection
- Auto-discovery of memory service
- Professional conversational interface

### When to Choose MCP Server

**✅ Perfect For**:
- Team environments with shared memory service
- Complex multi-server MCP workflows
- Integration with other MCP tools
- Maximum configuration flexibility
- Traditional MCP tool interactions

**✅ Benefits**:
- Full MCP protocol compliance
- Works alongside other MCP servers
- Conversational natural language interface
- Advanced server configuration options
- Standard MCP debugging and monitoring

### Can I Use Both?
**✅ Yes!** Commands and MCP Server are fully compatible:
- Same underlying memory service and database
- Switch between methods as needed
- Commands for quick operations, MCP server for deep integration
- No conflicts or data compatibility issues

See the complete [Commands vs MCP Server Guide](../guides/commands-vs-mcp-server.md) for detailed comparison.

---

## Troubleshooting

### Commands Not Working

**Issue**: Commands not found or not executing
```bash
# Check Claude Code CLI
claude --version  # Should show version info

# Check if commands are installed
ls ~/.claude/commands/memory-*.md

# Reinstall commands
python scripts/claude_commands_utils.py

# Test installation prerequisites
python scripts/claude_commands_utils.py --test
```

### Memory Service Connection Issues

**Issue**: Commands can't connect to memory service
```bash
# Check if memory service is running
memory --help

# Test service health
claude /memory-health

# Start memory service manually
memory  # Starts interactive service

# Check service auto-discovery
# Commands use mDNS to find running services automatically
```

### Permission Issues

**Issue**: Cannot install or access commands
```bash
# Check commands directory permissions
ls -la ~/.claude/commands/

# Ensure write access to commands directory
chmod 755 ~/.claude/commands/

# Try installation with explicit permissions
sudo python scripts/claude_commands_utils.py  # Not recommended, troubleshoot first
```

### Performance Issues

**Issue**: Commands are slow or unresponsive
```bash
# Check service health and performance
claude /memory-health --detailed --performance-test

# Check memory service resources
# Commands automatically discover and connect to optimal endpoints

# Clear any cached data
claude /memory-health --fix-issues
```

### Installation Issues

**Issue**: Installation fails or incomplete
```bash
# Check prerequisites
python --version  # Should be 3.10+
claude --version  # Should show Claude Code version

# Clean installation
python scripts/claude_commands_utils.py --uninstall
python install.py --install-claude-commands

# Manual installation
cp claude_commands/*.md ~/.claude/commands/
```

### Getting Help

- 📖 [Full Documentation](../README.md)
- 🐛 [Report Issues](https://github.com/doobidoo/mcp-memory-service/issues)
- 💬 [Discussions](https://github.com/doobidoo/mcp-memory-service/discussions)
- 🔍 [Search Existing Issues](https://github.com/doobidoo/mcp-memory-service/issues?q=is%3Aissue)

---

## Advanced Features

### Context-Aware Operations

Commands automatically detect and use:
- **Current Project**: Working directory and git repository information
- **Session Context**: Current conversation topics and development focus  
- **File Context**: Recent file changes and modifications
- **Temporal Context**: Time-based relevance and recency

### Smart Tagging

Automatic tag generation based on:
- Project directory name and structure
- Programming languages detected in current directory
- File types and patterns (`.js`, `.py`, `.md`, etc.)
- Git repository name and branch information
- Development context and session topics

### Service Auto-Discovery

Commands use multiple methods to find your memory service:
1. **mDNS Discovery**: Automatic service discovery on local network
2. **Default Endpoints**: Localhost ports and standard configurations
3. **Environment Variables**: Custom endpoint configuration
4. **Fallback Methods**: Graceful degradation when service unavailable

### Professional Features

- **Health Monitoring**: Comprehensive service diagnostics
- **Performance Testing**: Benchmark and optimization tools
- **Backup Verification**: Automatic backup system checking
- **Error Recovery**: Intelligent error handling and recovery suggestions
- **Export Capabilities**: Save reports and search results to files

### Integration with MCP Memory Service Features

Commands provide full access to:
- **Semantic Search**: Using sentence transformers and embeddings
- **Time-based Recall**: Natural language time expression parsing
- **Tag Management**: Flexible tagging and organization system
- **Multiple Storage Backends**: ChromaDB and SQLite-vec support
- **Cross-platform Compatibility**: Windows, macOS, and Linux support

---

## Developer Information

### Command Architecture

Commands are implemented as:
- **Markdown Files**: Conversational interfaces in `~/.claude/commands/`
- **Python Utilities**: Installation and management in `scripts/claude_commands_utils.py`
- **Integration Logic**: Seamless installation via main `install.py`
- **Cross-platform Support**: Windows, macOS, and Linux compatibility

### Contributing

- Commands follow the CCPlugins conversational pattern
- Each command is a markdown file with structured sections
- Installation utilities provide comprehensive error handling
- Integration testing ensures cross-platform compatibility

### Customization

- Command behavior can be modified by editing markdown files
- Installation options can be customized via CLI arguments
- Service discovery can be configured via environment variables
- Advanced users can extend commands with custom functionality

---

**Enjoy your enhanced Claude Code experience with persistent memory capabilities!** 🎉