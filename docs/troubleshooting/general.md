# MCP Memory Service Troubleshooting Guide

This guide covers common issues and their solutions when working with the MCP Memory Service.

## Common Installation Issues

[Content from installation.md's troubleshooting section - already well documented]

## MCP Protocol Issues

### Method Not Found Errors

If you're seeing "Method not found" errors or JSON error popups in Claude Desktop:

#### Symptoms
- "Method not found" errors in logs
- JSON error popups in Claude Desktop
- Connection issues between Claude Desktop and the memory service

#### Solution
1. Ensure you have the latest version of the MCP Memory Service
2. Verify your server implements all required MCP protocol methods:
   - resources/list
   - resources/read
   - resource_templates/list
3. Update your Claude Desktop configuration using the provided template

[Additional content from MCP_PROTOCOL_FIX.md]

## Windows-Specific Issues

[Content from WINDOWS_JSON_FIX.md and windows-specific sections]

## Performance Optimization

### Memory Issues
[Content from installation.md's performance section]

### Acceleration Issues
[Content from installation.md's acceleration section]

## Debugging Tools

[Content from installation.md's debugging section]

## Getting Help

[Content from installation.md's help section]
