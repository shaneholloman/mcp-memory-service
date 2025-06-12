import asyncio
import mcp

async def test_memory_service():
    # Connect to memory service
    memory = mcp.Peer(name="test_client", service="memory")
    print("Connected to MCP memory service")

    # Store a test memory
    test_memory = "This is a test memory from our test client"
    store_result = await memory.request("store", args={"content": test_memory, "tags": ["test"]})
    print(f"\nStored memory with ID: {store_result}")

    # Retrieve the memory back
    retrieve_result = await memory.request("retrieve", args={"query": "test memory", "n_results": 1})
    print("\nRetrieved memory:")
    print(f"Content: {retrieve_result[0]['content']}")
    print(f"Similarity: {retrieve_result[0]['similarity']:.2f}")

if __name__ == "__main__":
    print("Starting MCP memory service test...")
    asyncio.run(test_memory_service())

