#!/usr/bin/env python3
"""
Test script to store a memory in the MCP Memory Service.
"""
import asyncio
import json
import os
import sys

# Import MCP client
try:
    from mcp import ClientSession
    from mcp.client.stdio import stdio_client, StdioServerParameters
except ImportError as e:
    print(f"MCP client not found: {e}")
    print("Install with: pip install mcp")
    sys.exit(1)

async def store_memory():
    """Store a test memory."""
    try:
        # Configure MCP server connection
        server_params = StdioServerParameters(
            command="uv",
            args=["run", "memory", "server"],
            env=None
        )

        # Connect to memory service using stdio_client
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                # Initialize the session
                await session.initialize()
                print("Connected to memory service!")

                # List available tools
                tools_response = await session.list_tools()
                print(f"Found {len(tools_response.tools)} tools")

                # Check if store_memory tool exists
                if not any(tool.name == "store_memory" for tool in tools_response.tools):
                    print("ERROR: store_memory tool not found")
                    return

                # Create a test memory
                memory_data = {
                    "content": "This is a test memory created by the test_store_memory.py script.",
                    "metadata": {
                        "tags": "test,example,python",  # Comma-separated string format
                        "type": "note"
                    }
                }

                # Store the memory
                print(f"\nStoring test memory: {memory_data['content']}")
                result = await session.call_tool("store_memory", memory_data)

                # Print result
                if result:
                    print("\nResult:")
                    for content_item in result.content:
                        if hasattr(content_item, 'text'):
                            print(content_item.text)
                else:
                    print("No result returned")

                # Try to retrieve the memory
                print("\nRetrieving memory...")
                retrieve_result = await session.call_tool("retrieve_memory", {"query": "test memory", "n_results": 5})

                # Print result
                if retrieve_result:
                    print("\nRetrieve Result:")
                    for content_item in retrieve_result.content:
                        if hasattr(content_item, 'text'):
                            print(content_item.text)
                else:
                    print("No retrieve result returned")

                # Check database health
                print("\nChecking database health...")
                health_result = await session.call_tool("check_database_health", {})

                # Print result
                if health_result:
                    print("\nHealth Check Result:")
                    for content_item in health_result.content:
                        if hasattr(content_item, 'text'):
                            print(content_item.text)
                else:
                    print("No health check result returned")

    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

async def main():
    """Main function."""
    print("=== MCP Memory Service Test: Store Memory ===\n")
    await store_memory()

if __name__ == "__main__":
    asyncio.run(main())
