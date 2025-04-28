# MCP Memory Service Integrations

This document catalogs tools, utilities, and integrations that extend the functionality of the MCP Memory Service.

## Official Integrations

### [MCP Memory Dashboard](https://github.com/doobidoo/mcp-memory-dashboard)(This is still wip!)

A web-based dashboard for viewing, searching, and managing your MCP Memory Service data. The dashboard allows you to:
- Browse and search memories
- View memory metadata and tags
- Delete unwanted memories
- Perform semantic searches
- Monitor system health

## Community Integrations

### [Claude Memory Context](https://github.com/doobidoo/claude-memory-context)

A utility that enables Claude to start each conversation with awareness of the topics and important memories stored in your MCP Memory Service.

This tool:
- Queries your MCP memory service for recent and important memories
- Extracts topics and content summaries
- Formats this information into a structured context section
- Updates Claude project instructions automatically

The utility leverages Claude's project instructions feature without requiring any modifications to the MCP protocol. It can be automated to run periodically, ensuring Claude always has access to your latest memories.

See the [Claude Memory Context repository](https://github.com/doobidoo/claude-memory-context) for installation and usage instructions.

---

## Adding Your Integration

If you've built a tool or integration for the MCP Memory Service, we'd love to include it here. Please submit a pull request that adds your project to this document with:

1. The name of your integration (with link to repository)
2. A brief description (2-3 sentences)
3. A list of key features
4. Any installation notes or special requirements

All listed integrations should be functional, documented, and actively maintained.
