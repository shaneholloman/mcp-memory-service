# Store Memory with Context

I'll help you store information in your MCP Memory Service with proper context and tagging. This command captures the current session context and stores it as a persistent memory that can be recalled later.

## What I'll do:

1. **Detect Current Context**: I'll analyze the current working directory, recent files, and conversation context to understand what we're working on.

2. **Capture Memory Content**: I'll take the provided information or current session summary and prepare it for storage.

3. **Add Smart Tags**: I'll automatically generate relevant tags based on:
   - Machine hostname (source identifier)
   - Current project directory name
   - Programming languages detected
   - File types and patterns
   - Any explicit tags you provide

4. **Store with Metadata**: I'll include useful metadata like:
   - Machine hostname for source tracking
   - Timestamp and session context
   - Project path and git repository info
   - File associations and dependencies

## Usage Examples:

```bash
claude /memory-store "We decided to use SQLite-vec instead of ChromaDB for better performance"
claude /memory-store --tags "decision,architecture" "Database backend choice rationale"
claude /memory-store --type "note" "Remember to update the Docker configuration after the database change"
```

## Implementation:

I'll store the memory directly to your MCP Memory Service at `https://memory.local:8443/`. The memory will be saved automatically without confirmation prompts.

The content will be stored with automatic context detection:
- **Machine Context**: Hostname automatically added as tag (e.g., "source:your-machine-name")
- **Project Context**: Current directory, git repository, recent commits
- **Session Context**: Current conversation topics and decisions
- **Technical Context**: Programming language, frameworks, and tools in use
- **Temporal Context**: Date, time, and relationship to recent activities

The service endpoint is configured at:
- **Main endpoint**: `https://memory.local:8443/`
- **API endpoint**: `https://memory.local:8443/api/memories`

I'll use the correct curl syntax with `-k` flag for HTTPS, proper JSON payload formatting, and automatic client hostname detection using the `X-Client-Hostname` header.

## Arguments:

- `$ARGUMENTS` - The content to store as memory, or additional flags:
  - `--tags "tag1,tag2"` - Explicit tags to add
  - `--type "note|decision|task|reference"` - Memory type classification
  - `--project "name"` - Override project name detection
  - `--private` - Mark as private/sensitive content

I'll store the memory automatically without asking for confirmation. The memory will be saved immediately using proper JSON formatting with the curl command. You'll receive a brief confirmation showing the content hash and applied tags after successful storage.