#!/usr/bin/env python3
"""
MCP compatibility test - try to work around TaskGroup issue
"""

import asyncio
import sys

# Add TaskGroup compatibility for Python < 3.11
if sys.version_info < (3, 11):
    print("🔧 Adding TaskGroup compatibility for Python 3.10", file=sys.stderr)
    
    # Simple TaskGroup implementation for compatibility
    class TaskGroup:
        def __init__(self):
            self._tasks = []
            self._errors = []
        
        async def __aenter__(self):
            return self
        
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            if self._tasks:
                await asyncio.gather(*self._tasks, return_exceptions=True)
            return False
        
        def create_task(self, coro):
            task = asyncio.create_task(coro)
            self._tasks.append(task)
            return task
    
    # Monkey patch asyncio
    asyncio.TaskGroup = TaskGroup
    print("✅ TaskGroup compatibility added", file=sys.stderr)

# Now import MCP
import json
import logging
from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
import mcp.server.stdio

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

class CompatibilityTestServer:
    def __init__(self):
        self.server = Server("compatibility-test")
        self.register_handlers()
        print("✅ Compatibility test server initialized", file=sys.stderr, flush=True)

    def register_handlers(self):
        print("🔧 Registering handlers with compatibility...", file=sys.stderr, flush=True)
        
        @self.server.list_tools()
        async def handle_list_tools():
            print("📋 LIST_TOOLS called", file=sys.stderr, flush=True)
            tools = [
                types.Tool(
                    name="compatibility_test",
                    description="Test with TaskGroup compatibility",
                    inputSchema={"type": "object", "properties": {}}
                )
            ]
            return tools
        
        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: dict | None):
            print(f"🎯🎯🎯 COMPATIBILITY TOOL CALL: {name} 🎯🎯🎯", file=sys.stderr, flush=True)
            
            if name == "compatibility_test":
                print("✅ EXECUTING compatibility_test", file=sys.stderr, flush=True)
                result = {"status": "SUCCESS", "message": "TaskGroup compatibility works!"}
                response_text = json.dumps(result)
                print(f"✅ RETURNING: {response_text}", file=sys.stderr, flush=True)
                return [types.TextContent(type="text", text=response_text)]
            else:
                return [types.TextContent(type="text", text=f"Unknown tool: {name}")]
        
        print("✅ Handlers registered with compatibility", file=sys.stderr, flush=True)

async def main():
    print("🚀 Starting compatibility test server...", file=sys.stderr, flush=True)
    
    server = CompatibilityTestServer()
    
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        print("🚀 Compatibility server ready", file=sys.stderr, flush=True)
        await server.server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="compatibility-test",
                server_version="0.1.0",
                capabilities=server.server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={}
                ),
            ),
        )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 Shutting down...", file=sys.stderr, flush=True)
    except Exception as e:
        print(f"💥 Fatal error: {str(e)}", file=sys.stderr, flush=True)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
