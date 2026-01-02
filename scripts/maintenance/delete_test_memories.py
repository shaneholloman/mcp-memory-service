#!/usr/bin/env python3
"""
MCP Memory Service - Delete Test Memories Script
Bulk deletes remaining untagged test memories.
"""

import requests
import sys
from typing import List

API_URL = "http://127.0.0.1:8000/api"
HEADERS = {"Content-Type": "application/json"}

# Patterns that indicate test data
TEST_PATTERNS = [
    "test content",
    "test memory",
    "test for",
    "test hash",
    "backup test",
    "[",  # UUID patterns in brackets
]


def is_test_memory(content: str) -> bool:
    """Determine if memory is test data."""
    content_lower = content.lower()
    
    for pattern in TEST_PATTERNS:
        if pattern.lower() in content_lower:
            return True
    
    return False


def get_all_untagged_memories() -> List[dict]:
    """Fetch all untagged memories."""
    untagged = []
    page = 1
    
    print("Fetching untagged memories...")
    
    while True:
        response = requests.get(
            f"{API_URL}/memories",
            params={"page": page, "page_size": 100}
        )
        response.raise_for_status()
        data = response.json()
        
        if not data.get("memories"):
            break
        
        for memory in data["memories"]:
            if not memory.get("tags") or len(memory["tags"]) == 0:
                untagged.append(memory)
        
        if not data.get("has_more"):
            break
        
        page += 1
    
    return untagged


def delete_memory(content_hash: str) -> bool:
    """Delete a single memory."""
    try:
        response = requests.delete(
            f"{API_URL}/memories/{content_hash}",
            headers=HEADERS
        )
        # Accept 200 and 204 as success
        return response.status_code in [200, 204, 404]
    except Exception as e:
        print(f"  Error deleting {content_hash}: {e}")
        return False


def main():
    """Main deletion workflow."""
    print("=" * 80)
    print("MCP Memory Service - Delete Test Memories")
    print("=" * 80)
    print()
    
    # Fetch all untagged
    untagged = get_all_untagged_memories()
    print(f"Total untagged memories: {len(untagged)}\n")
    
    # Identify test memories
    test_memories = [m for m in untagged if is_test_memory(m.get("content", ""))]
    
    if not test_memories:
        print("No test memories found to delete.")
        return
    
    print(f"Found {len(test_memories)} test memories to delete")
    print()
    print("Sample test memories:")
    for mem in test_memories[:5]:
        print(f"  - {mem['content'][:70]}...")
    
    print()
    response = input(f"Delete {len(test_memories)} test memories? (yes/no): ").strip().lower()
    
    if response != "yes":
        print("Deletion cancelled.")
        return
    
    print()
    print(f"Deleting {len(test_memories)} test memories...")
    print("-" * 80)
    
    deleted_count = 0
    failed_count = 0
    
    for i, memory in enumerate(test_memories, 1):
        content_hash = memory.get("content_hash")
        content = memory.get("content", "")[:50]
        
        # Show progress
        print(f"[{i}/{len(test_memories)}] ", end="", flush=True)
        
        if delete_memory(content_hash):
            deleted_count += 1
            print(f"✓ {content_hash[:12]}...")
        else:
            failed_count += 1
            print(f"✗ {content_hash[:12]}... → FAILED")
    
    print()
    print("-" * 80)
    print(f"\nResults:")
    print(f"  ✓ Successfully deleted: {deleted_count}/{len(test_memories)}")
    print(f"  ✗ Failed: {failed_count}/{len(test_memories)}")
    print()
    
    print("Next steps:")
    print("  1. Review Dashboard: http://127.0.0.1:8000")
    print("  2. Verify all valuable memories are properly tagged")
    print("  3. Check database statistics in Dashboard/Analytics")
    
    print("\n" + "=" * 80)
    print("Deletion complete!")
    print("=" * 80)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nDeletion cancelled")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
