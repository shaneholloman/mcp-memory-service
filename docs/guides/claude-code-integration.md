# Using MCP Memory Service with Claude Code

This guide explains how to integrate the MCP Memory Service with Claude Code, allowing you to use persistent memory capabilities in the Claude CLI environment.

## Prerequisites

Before you begin, ensure you have:

1. Installed [Claude Code](https://www.anthropic.com/news/introducing-claude-code) CLI tool
2. Set up the MCP Memory Service on your machine
3. Basic familiarity with command-line interfaces

## Registering the Memory Service with Claude Code

You can register the MCP Memory Service to work with Claude Code using the `claude mcp add` command.

### Check Existing MCP Servers

To see which MCP servers are already registered with Claude:

```bash
claude mcp list
```

### Add the Memory Service

To add the memory service that's running on your local machine:

```bash
claude mcp add memory-service spawn -- /path/to/your/command
```

For example, if you've installed the memory service using UV (recommended):

```bash
claude mcp add memory-service spawn -- /opt/homebrew/bin/uv --directory /Users/yourusername/path/to/mcp-memory-service run memory
```

Replace the path elements with the actual paths on your system.

## Example Configuration

Here's a real-world example of adding the memory service to Claude Code:

```bash
claude mcp add memory-service spawn -- /opt/homebrew/bin/uv --directory /Users/yourusername/Documents/GitHub/mcp-memory-service run memory
```

This command:
1. Registers a new MCP server named "memory-service"
2. Uses the "spawn" transport method, which runs the command when needed
3. Specifies the full path to the UV command
4. Sets the working directory to your mcp-memory-service location
5. Runs the "memory" module

After running this command, you should see a confirmation message like:

```
Added stdio MCP server memory-service with command: spawn /opt/homebrew/bin/uv --directory /Users/yourusername/Documents/GitHub/mcp-memory-service run memory to local config
```

## Using Memory Functions in Claude Code

Once registered, you can use the memory service directly in your conversations with Claude Code. The memory functions available include:

- Storing memories
- Retrieving memories based on semantic search
- Recalling information from specific time periods
- Searching by tags
- And many more

## Troubleshooting

If you encounter issues:

1. Verify the memory service is running properly as a standalone application
2. Check that the paths in your `claude mcp add` command are correct
3. Ensure you have the necessary permissions to execute the specified commands
4. Try running `claude mcp list` to verify the server was added correctly

## Additional Information

For more detailed information about the memory service's capabilities and configuration options, refer to the main README and other documentation sections.

## Benefits of Using Claude Code with MCP Memory Service

Integrating the MCP Memory Service with Claude Code provides several advantages:

1. **Persistent Memory**: Your conversations and stored information persist across sessions
2. **Semantic Search**: Claude can retrieve relevant information even when not phrased exactly the same way
3. **Temporal Recall**: Ask about information from specific time periods (e.g., "last week", "yesterday")
4. **Organized Knowledge**: Use tags to categorize and later retrieve information by category

This integration helps create a more powerful and versatile CLI experience with Claude, turning it into a knowledge management system with long-term memory capabilities.
