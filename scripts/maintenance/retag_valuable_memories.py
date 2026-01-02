#!/usr/bin/env python3
"""
MCP Memory Service - Retag Valuable Memories Script
Automatically retags valuable untagged memories based on content analysis.
"""

import requests
import json
import sys
from typing import List
from datetime import datetime

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

VALUABLE_KEYWORDS = [
    "release",
    "api",
    "feature",
    "documentation",
    "guide",
    "tutorial",
    "implementation",
    "architecture",
    "fix",
    "session",
]


def is_test_memory(content: str) -> bool:
    """Determine if memory is test data."""
    content_lower = content.lower()
    
    for pattern in TEST_PATTERNS:
        if pattern.lower() in content_lower:
            return True
    
    return False


def should_keep(content: str) -> bool:
    """Determine if memory should be kept and retagged."""
    content_lower = content.lower()
    
    # Check valuable keywords
    for keyword in VALUABLE_KEYWORDS:
        if keyword in content_lower:
            return True
    
    # Check content length - likely valuable if substantial
    if len(content) > 500:
        return True
    
    return False


def get_suggested_tags(content: str) -> List[str]:
    """Suggest tags based on content - aggressively tag everything."""
    tags = set()
    content_lower = content.lower()
    
    # Version/Release detection
    if any(x in content_lower for x in ["release", "v8", "v1", "version"]):
        tags.add("release")
    if "v8.64" in content_lower:
        tags.add("v8.64")
    
    # Technology detection
    if "cloudflare" in content_lower:
        tags.add("cloudflare")
    if "api" in content_lower or "endpoint" in content_lower:
        tags.add("api")
    if "hybrid" in content_lower or "sync" in content_lower:
        tags.add("sync")
    if "race condition" in content_lower or "tombstone" in content_lower:
        tags.add("bug-fix")
    
    # Session/Documentation
    if any(x in content_lower for x in ["session", "summary", "captured"]):
        tags.add("session-summary")
    if "documentation" in content_lower or "guide" in content_lower:
        tags.add("documentation")
    
    # Tools/Workflows
    if "ketchup" in content_lower or "tcr" in content_lower:
        tags.add("workflow")
    if "secondbrain" in content_lower.replace("-", ""):
        tags.add("secondbrain")
    
    # Project/Component detection
    if "shodh" in content_lower:
        tags.add("shodh")
    if "mcp-memory" in content_lower or "mcp_memory" in content_lower:
        tags.add("mcp-memory-service")
    if "secondbrain" in content_lower:
        tags.add("secondbrain")
    
    # General categorization
    if len(content) > 500:
        tags.add("important")
    if any(x in content_lower for x in ["template", "setup", "install"]):
        tags.add("setup-guide")
    
    # Fallback to generic tag if nothing matched
    if not tags:
        tags.add("needs-categorization")
    
    return sorted(list(tags))


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


def retag_memory(content_hash: str, tags: List[str]) -> bool:
    """Retag a single memory using PUT endpoint."""
    try:
        response = requests.put(
            f"{API_URL}/memories/{content_hash}",
            json={"tags": tags},
            headers=HEADERS
        )
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"  Error retagging {content_hash}: {e}")
        return False


def main():
    """Main retag workflow."""
    print("=" * 80)
    print("MCP Memory Service - Retag Valuable Memories")
    print("=" * 80)
    print()
    
    # Fetch all untagged
    untagged = get_all_untagged_memories()
    print(f"Total untagged memories: {len(untagged)}\n")
    
    # Classify
    test_memories = []
    valuable_memories = []
    
    for memory in untagged:
        content = memory.get("content", "")
        
        if is_test_memory(content):
            test_memories.append(memory)
        elif should_keep(content):
            valuable_memories.append(memory)
    
    print(f"Classification:")
    print(f"  ✗ Test memories: {len(test_memories)}")
    print(f"  ✓ Valuable (to retag): {len(valuable_memories)}")
    print()
    
    # Retag valuable ones
    if not valuable_memories:
        print("No valuable memories found to retag.")
        return
    
    print(f"Retagging {len(valuable_memories)} valuable memories...")
    print("-" * 80)
    
    retagged_count = 0
    failed_count = 0
    
    for i, memory in enumerate(valuable_memories, 1):
        content = memory.get("content", "")
        content_hash = memory.get("content_hash")
        tags = get_suggested_tags(content)
        
        # Show progress
        print(f"[{i}/{len(valuable_memories)}] ", end="", flush=True)
        
        if retag_memory(content_hash, tags):
            retagged_count += 1
            print(f"✓ {content_hash[:12]}... → {', '.join(tags[:3])}")
            if len(tags) > 3:
                print(f"       {', '.join(tags[3:])}")
        else:
            failed_count += 1
            print(f"✗ {content_hash[:12]}... → FAILED")
    
    print()
    print("-" * 80)
    print(f"\nResults:")
    print(f"  ✓ Successfully retagged: {retagged_count}/{len(valuable_memories)}")
    print(f"  ✗ Failed: {failed_count}/{len(valuable_memories)}")
    print(f"  Remaining untagged (test data): {len(test_memories)}")
    print()
    
    # Summary stats
    if retagged_count > 0:
        print("Next steps:")
        print("  1. Review retagged memories in Dashboard: http://127.0.0.1:8000")
        print(f"  2. Delete remaining {len(test_memories)} test memories")
        print("     - Filter: untagged memories")
        print("     - Use Dashboard delete button or: DELETE /api/memories/{{content_hash}}")
    
    print("\n" + "=" * 80)
    print("Retagging complete!")
    print("=" * 80)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nRetagging cancelled")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
