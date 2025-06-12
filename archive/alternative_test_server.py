#!/usr/bin/env python3
"""
Alternative MCP test with different protocol variations
"""

import sys
import asyncio
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

class AlternativeTestServer:
    def __init__(self):
        self.server = Server("alternative-test")
        self.register_handlers()
        print("✅ Alternative test server initialized", file=sys.stderr, flush=True)

    def register_handlers(self):
        print("🔧 Registering alternative handlers...", file=sys.stderr, flush=True)
        
        @self.server.list_tools()
        async def handle_list_tools():
            print("📋 Alternative LIST_TOOLS called", file=sys.stderr, flush=True)
            tools = [
                types.Tool(
                    name="simple_test",
                    description="Simple alternative test",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                )
            ]
            print(f"📋 Alternative returning {len(tools)} tools", file=sys.stderr, flush=True)
            return tools
        
        # Try different decorator approach
        async def handle_call_tool_alternative(name: str, arguments: dict | None):
            print(f"🎯 ALTERNATIVE TOOL CALL HANDLER: {name}", file=sys.stderr, flush=True)
            logger.info(f"Alternative handler called: {name}")
            
            if name == "simple_test":
                print("✅ Alternative handler executing simple_test", file=sys.stderr, flush=True)
                result = {"status": "SUCCESS", "message": "Alternative handler works!"}
                response_text = json.dumps(result)
                print(f"✅ Alternative returning: {response_text}", file=sys.stderr, flush=True)
                return [types.TextContent(type="text", text=response_text)]
            else:
                return [types.TextContent(type="text", text=f"Unknown tool: {name}")]
        
        # Register with explicit method
        self.server.call_tool()(handle_call_tool_alternative)
        
        print("✅ Alternative handlers registered", file=sys.stderr, flush=True)

async def main():
    print("🚀 Starting alternative MCP test server...", file=sys.stderr, flush=True)
    
    server = AlternativeTestServer()
    
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        print("🚀 Alternative server ready", file=sys.stderr, flush=True)
        
        # Try different protocol version
        await server.server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="alternative-test",
                server_version="0.1.0",
                protocol_version="2024-11-05",  # Explicit protocol version
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
        print("🛑 Alternative server shutting down...", file=sys.stderr, flush=True)
    except Exception as e:
        print(f"💥 Alternative server error: {str(e)}", file=sys.stderr, flush=True)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
