#!/usr/bin/env python3
"""
Ultimate MCP debugging server with complete protocol logging
"""

import sys
import os
import asyncio
import json
import logging
from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
import mcp.server.stdio

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

class ProtocolDebuggingServer:
    def __init__(self):
        self.server = Server("protocol-debug")
        self.register_handlers()
        print("✅ Protocol debugging server initialized", file=sys.stderr, flush=True)

    def register_handlers(self):
        print("🔧 Registering handlers with complete protocol debugging...", file=sys.stderr, flush=True)
        
        # Log all method calls for debugging
        original_call_method = self.server._call_method if hasattr(self.server, '_call_method') else None
        
        @self.server.list_tools()
        async def handle_list_tools():
            print("📋 LIST_TOOLS called", file=sys.stderr, flush=True)
            logger.info("LIST_TOOLS handler executed")
            tools = [
                types.Tool(
                    name="protocol_test",
                    description="Protocol debugging test tool",
                    inputSchema={"type": "object", "properties": {}}
                )
            ]
            print(f"📋 Returning {len(tools)} tools", file=sys.stderr, flush=True)
            return tools
        
        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: dict | None):
            print(f"🎯🎯🎯 PROTOCOL DEBUG TOOL CALL: {name} 🎯🎯🎯", file=sys.stderr, flush=True)
            logger.info(f"CALL_TOOL handler executed: {name}")
            print(f"Arguments received: {arguments}", file=sys.stderr, flush=True)
            
            if name == "protocol_test":
                print("✅ EXECUTING protocol_test", file=sys.stderr, flush=True)
                result = {
                    "status": "SUCCESS", 
                    "message": "Protocol debugging successful!",
                    "handler_reached": True,
                    "python_version": sys.version,
                    "arguments_received": arguments
                }
                response_text = json.dumps(result, indent=2)
                print(f"✅ RETURNING: {response_text}", file=sys.stderr, flush=True)
                return [types.TextContent(type="text", text=response_text)]
            else:
                print(f"❌ Unknown tool: {name}", file=sys.stderr, flush=True)
                return [types.TextContent(type="text", text=f"Unknown tool: {name}")]
        
        print("✅ All handlers registered for protocol debugging", file=sys.stderr, flush=True)

async def main():
    print("🚀 Starting ULTIMATE protocol debugging server...", file=sys.stderr, flush=True)
    
    # Add protocol-level debugging
    original_stdio_server = mcp.server.stdio.stdio_server
    
    async def debug_stdio_server():
        print("🔍 STDIO server context starting...", file=sys.stderr, flush=True)
        async with original_stdio_server() as (read_stream, write_stream):
            print("🔍 STDIO streams established", file=sys.stderr, flush=True)
            
            # Wrap streams for debugging
            class DebugReadStream:
                def __init__(self, stream):
                    self._stream = stream
                
                async def read(self, size=-1):
                    data = await self._stream.read(size)
                    if data:
                        try:
                            decoded = data.decode('utf-8', errors='ignore').strip()
                            if decoded and not decoded.isspace():
                                print(f"📥 INCOMING: {decoded}", file=sys.stderr, flush=True)
                                
                                # Check for tool calls specifically
                                if 'tools/call' in decoded:
                                    print(f"🎯 TOOL CALL DETECTED IN STREAM!", file=sys.stderr, flush=True)
                                    try:
                                        msg = json.loads(decoded)
                                        if msg.get('method') == 'tools/call':
                                            print(f"🔍 Tool call details: {msg.get('params', {})}", file=sys.stderr, flush=True)
                                    except:
                                        pass
                        except:
                            print(f"📥 BINARY DATA: {len(data)} bytes", file=sys.stderr, flush=True)
                    return data
                
                def __getattr__(self, name):
                    return getattr(self._stream, name)
            
            class DebugWriteStream:
                def __init__(self, stream):
                    self._stream = stream
                
                def write(self, data):
                    if data:
                        try:
                            decoded = data.decode('utf-8', errors='ignore').strip()
                            if decoded and not decoded.isspace():
                                print(f"📤 OUTGOING: {decoded}", file=sys.stderr, flush=True)
                        except:
                            print(f"📤 BINARY DATA: {len(data)} bytes", file=sys.stderr, flush=True)
                    return self._stream.write(data)
                
                def __getattr__(self, name):
                    return getattr(self._stream, name)
            
            debug_read = DebugReadStream(read_stream)
            debug_write = DebugWriteStream(write_stream)
            
            yield debug_read, debug_write
    
    server = ProtocolDebuggingServer()
    
    async with debug_stdio_server() as (read_stream, write_stream):
        print("🚀 Protocol debugging server ready", file=sys.stderr, flush=True)
        await server.server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="protocol-debug",
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
