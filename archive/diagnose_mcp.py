#!/usr/bin/env python3
"""
Diagnostic script to check MCP library and asyncio compatibility
"""

import sys
import asyncio
import platform

print("🔍 MCP Library and Asyncio Diagnostics")
print("=" * 50)

# Check Python and asyncio version
print(f"Python Version: {platform.python_version()}")
print(f"Platform: {platform.system()} {platform.machine()}")

# Check asyncio features
print(f"AsyncIO Debug Mode: {asyncio.get_event_loop().get_debug()}")

# Check if TaskGroup is available (Python 3.11+ feature)
try:
    from asyncio import TaskGroup
    print("✅ TaskGroup available (Python 3.11+ feature)")
except ImportError:
    print("❌ TaskGroup not available (requires Python 3.11+)")

# Check MCP library
try:
    import mcp
    print(f"✅ MCP library imported successfully")
    if hasattr(mcp, '__version__'):
        print(f"MCP Version: {mcp.__version__}")
    else:
        print("MCP Version: Not available")
        
    # Check MCP components
    from mcp.server import Server
    from mcp.server.models import InitializationOptions
    import mcp.server.stdio
    print("✅ MCP server components available")
    
except ImportError as e:
    print(f"❌ MCP library import failed: {e}")

# Check if this is the TaskGroup compatibility issue
python_version = tuple(map(int, platform.python_version().split('.')[:2]))
if python_version < (3, 11):
    print("⚠️  WARNING: Python < 3.11 but MCP might expect TaskGroup")
    print("   This could be the source of the TaskGroup error")
else:
    print("✅ Python version supports TaskGroup")

print("\n🎯 Diagnostic Complete")
