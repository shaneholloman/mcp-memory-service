#!/usr/bin/env python3
"""
Debug script to check what distance values SQLite-vec returns.
"""

import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from mcp_memory_service.storage.sqlite_vec import SqliteVecMemoryStorage

async def debug_similarity_scores():
    """Debug what distance values SQLite-vec returns."""
    print("🔍 Debugging SQLite-vec similarity scores...")
    
    storage = SqliteVecMemoryStorage("/home/hkr/.local/share/mcp-memory/sqlite_vec.db")
    await storage.initialize()
    
    # Test with a simple query
    print("\n1. Testing with query: 'embedding'")
    results = await storage.retrieve("embedding", n_results=3)
    
    for i, result in enumerate(results, 1):
        print(f"\nResult {i}:")
        print(f"  Content: {result.memory.content[:60]}...")
        print(f"  Relevance Score: {result.relevance_score}")
        print(f"  Debug Info: {result.debug_info}")
        
        # Calculate what the distance was
        if result.relevance_score is not None:
            distance = 1.0 - result.relevance_score
            print(f"  Calculated Distance: {distance}")
    
    # Test with exact match
    print("\n2. Testing with exact content match...")
    results = await storage.retrieve("Final test memory to trigger embedding model loading", n_results=1)
    
    if results:
        result = results[0]
        print(f"  Content: {result.memory.content[:60]}...")
        print(f"  Relevance Score: {result.relevance_score}")
        print(f"  Debug Info: {result.debug_info}")
        
        if result.relevance_score is not None:
            distance = 1.0 - result.relevance_score  
            print(f"  Calculated Distance: {distance}")
    
    await storage.close()

if __name__ == "__main__":
    asyncio.run(debug_similarity_scores())