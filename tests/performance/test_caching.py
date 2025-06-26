#!/usr/bin/env python3
"""
Performance test script for MCP Memory Service optimizations
"""

import asyncio
import time
import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from mcp_memory_service.storage.chroma import ChromaMemoryStorage
from mcp_memory_service.models.memory import Memory
from mcp_memory_service.utils.hashing import generate_content_hash

async def run_performance_tests():
    """Run comprehensive performance tests."""
    print("🚀 Starting Performance Tests for MCP Memory Service")
    print("=" * 60)
    
    # Test database path
    test_db_path = os.path.join(os.path.dirname(__file__), "test_performance_db")
    
    try:
        # Test 1: Storage Initialization Performance
        print("\n📊 Test 1: Storage Initialization Performance")
        start_time = time.time()
        storage = ChromaMemoryStorage(test_db_path, preload_model=True)
        init_time = time.time() - start_time
        print(f"✅ Initialization time: {init_time:.2f} seconds")
        
        # Test 2: Model Caching Performance
        print("\n📊 Test 2: Model Caching Performance")
        start_time = time.time()
        storage2 = ChromaMemoryStorage(test_db_path + "_cache_test", preload_model=True)
        cache_init_time = time.time() - start_time
        print(f"✅ Second initialization (cached): {cache_init_time:.2f} seconds")
        print(f"⚡ Speedup: {(init_time / cache_init_time):.1f}x faster")
        
        # Test 3: Store Performance
        print("\n📊 Test 3: Store Performance")
        test_memories = []
        for i in range(10):
            content = f"Test memory content number {i} for performance testing"
            memory = Memory(
                content=content,
                content_hash=generate_content_hash(content, {}),
                tags=[f"test", f"performance", f"batch_{i//5}"],
                memory_type="test"
            )
            test_memories.append(memory)
        
        # Test individual stores
        start_time = time.time()
        for memory in test_memories[:5]:
            await storage.store(memory)
        individual_time = time.time() - start_time
        print(f"✅ Individual stores (5 memories): {individual_time:.3f} seconds")
        
        # Test batch store if available
        if hasattr(storage, 'store_batch'):
            start_time = time.time()
            await storage.store_batch(test_memories[5:])
            batch_time = time.time() - start_time
            print(f"✅ Batch store (5 memories): {batch_time:.3f} seconds")
            if batch_time > 0:
                print(f"⚡ Batch speedup: {(individual_time / batch_time):.1f}x faster")
        
        # Test 4: Query Performance with Caching
        print("\n📊 Test 4: Query Performance with Caching")
        test_query = "test memory performance"
        
        # First query (cache miss)
        start_time = time.time()
        results1 = await storage.retrieve(test_query, n_results=5)
        first_query_time = time.time() - start_time
        print(f"✅ First query (cache miss): {first_query_time:.3f} seconds")
        
        # Second identical query (cache hit)
        start_time = time.time()
        results2 = await storage.retrieve(test_query, n_results=5)
        second_query_time = time.time() - start_time
        print(f"✅ Second query (cache hit): {second_query_time:.3f} seconds")
        
        if second_query_time > 0:
            speedup = first_query_time / second_query_time
            print(f"⚡ Query caching speedup: {speedup:.1f}x faster")
        
        # Test 5: Tag Search Performance
        print("\n📊 Test 5: Tag Search Performance")
        start_time = time.time()
        tag_results = await storage.search_by_tag(["test", "performance"])
        tag_search_time = time.time() - start_time
        print(f"✅ Tag search: {tag_search_time:.3f} seconds")
        print(f"✅ Found {len(tag_results)} memories with tags")
        
        # Test 6: Performance Statistics
        print("\n📊 Test 6: Performance Statistics")
        if hasattr(storage, 'get_performance_stats'):
            stats = storage.get_performance_stats()
            print(f"✅ Model cache size: {stats.get('model_cache_size', 0)}")
            print(f"✅ Cache hits: {stats.get('cache_hits', 0)}")
            print(f"✅ Cache misses: {stats.get('cache_misses', 0)}")
            print(f"✅ Cache hit ratio: {stats.get('cache_hit_ratio', 0):.2%}")
            print(f"✅ Average query time: {stats.get('avg_query_time', 0):.3f}s")
        
        print("\n🎉 Performance Tests Complete!")
        print("=" * 60)
        
        # Performance Summary
        print("\n📈 Performance Summary:")
        print(f"• Initialization: {init_time:.2f}s")
        print(f"• Cached init: {cache_init_time:.2f}s ({(init_time/cache_init_time):.1f}x speedup)")
        print(f"• Query performance: {first_query_time:.3f}s → {second_query_time:.3f}s")
        print(f"• Tag search: {tag_search_time:.3f}s")
        print(f"• Total memories tested: {len(test_memories)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during performance tests: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Cleanup test databases
        import shutil
        for path in [test_db_path, test_db_path + "_cache_test"]:
            if os.path.exists(path):
                try:
                    shutil.rmtree(path)
                    print(f"🧹 Cleaned up test database: {path}")
                except Exception as e:
                    print(f"⚠️ Could not clean up {path}: {e}")

if __name__ == "__main__":
    print("MCP Memory Service - Performance Optimization Test")
    success = asyncio.run(run_performance_tests())
    sys.exit(0 if success else 1)
