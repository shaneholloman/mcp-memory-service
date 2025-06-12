#!/usr/bin/env python3
"""
Minimal server using UV environment (which has MCP) to test call_tool decorator
"""

import asyncio
import json
import sys
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

class MinimalWithUV:
    def __init__(self):
        self.server = Server("minimal-uv")
        self.register_handlers()
        print("✅ Minimal UV server initialized", file=sys.stderr, flush=True)

    def register_handlers(self):
        print("🔧 Registering handlers...", file=sys.stderr, flush=True)
        
        @self.server.list_tools()
        async def handle_list_tools():
            print("📋 LIST_TOOLS called", file=sys.stderr, flush=True)
            tools = [
                types.Tool(
                    name="minimal_test",
                    description="Minimal test with UV environment",
                    inputSchema={"type": "object", "properties": {}}
                )
            ]
            print(f"📋 Returning {len(tools)} tools", file=sys.stderr, flush=True)
            return tools
        
        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: dict | None):
            print(f"🎯🎯🎯 TOOL CALL INTERCEPTED: {name} 🎯🎯🎯", file=sys.stderr, flush=True)
            logger.info(f"TOOL CALL INTERCEPTED: {name}")
            
            if name == "minimal_test":
                print("✅ EXECUTING minimal_test", file=sys.stderr, flush=True)
                result = {"status": "SUCCESS", "message": "Minimal UV test worked!"}
                response_text = json.dumps(result)
                print(f"✅ RETURNING: {response_text}", file=sys.stderr, flush=True)
                return [types.TextContent(type="text", text=response_text)]
            else:
                print(f"❌ Unknown tool: {name}", file=sys.stderr, flush=True)
                return [types.TextContent(type="text", text=f"Unknown tool: {name}")]
        
        print("✅ Handlers registered", file=sys.stderr, flush=True)

async def main():
    print("🚀 Starting minimal UV server...", file=sys.stderr, flush=True)
    
    server = MinimalWithUV()
    
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        print("🚀 Server ready for communication", file=sys.stderr, flush=True)
        await server.server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="minimal-uv",
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
        sys.exit(1)
