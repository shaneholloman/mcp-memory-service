#!/usr/bin/env python3
"""
MCP Memory Service - Auto-Retag Single Memory
Automatically generates and applies tags for a specific memory by content hash.
"""

import requests
import sys
from typing import List

API_URL = "http://127.0.0.1:8000/api"
HEADERS = {"Content-Type": "application/json"}


def get_suggested_tags(content: str) -> List[str]:
    """Generate tags based on content - same logic as bulk script."""
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
    
    # General categorization
    if len(content) > 500:
        tags.add("important")
    if any(x in content_lower for x in ["template", "setup", "install"]):
        tags.add("setup-guide")
    
    # Fallback
    if not tags:
        tags.add("needs-categorization")
    
    return sorted(list(tags))


def get_memory_by_hash(content_hash: str) -> dict:
    """Fetch a specific memory by content hash."""
    try:
        response = requests.get(f"{API_URL}/memories/{content_hash}")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching memory: {e}", file=sys.stderr)
        return None


def search_memory(query: str) -> dict:
    """Search for a memory by content using semantic search."""
    try:
        response = requests.post(
            f"{API_URL}/search",
            json={"query": query, "n_results": 1},
            headers=HEADERS
        )
        response.raise_for_status()
        data = response.json()
        
        if data.get("results"):
            return data["results"][0]["memory"]  # Return first result
        return None
    except Exception as e:
        print(f"Error searching memory: {e}", file=sys.stderr)
        return None


def update_memory_tags(content_hash: str, tags: List[str]) -> bool:
    """Update memory tags."""
    try:
        response = requests.put(
            f"{API_URL}/memories/{content_hash}",
            json={"tags": tags},
            headers=HEADERS
        )
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"Error updating memory: {e}", file=sys.stderr)
        return False


def main():
    """Auto-retag a single memory."""
    print("=" * 80)
    print("MCP Memory Service - Auto-Retag Single Memory")
    print("=" * 80)
    print()
    
    if len(sys.argv) < 2:
        print("Usage:")
        print(f"  By content hash: {sys.argv[0]} <content_hash>")
        print(f"  By search query: {sys.argv[0]} --search 'query text'")
        print()
        print("Examples:")
        print(f"  {sys.argv[0]} abc123def456...")
        print(f"  {sys.argv[0]} --search 'cloudflare release'")
        sys.exit(1)
    
    # Determine input type
    if sys.argv[1] == "--search":
        if len(sys.argv) < 3:
            print("Error: Please provide search query")
            sys.exit(1)
        search_query = " ".join(sys.argv[2:])
        print(f"Searching for: {search_query}")
        memory = search_memory(search_query)
        if not memory:
            print(f"Memory not found for query: {search_query}")
            sys.exit(1)
    else:
        content_hash = sys.argv[1]
        print(f"Fetching memory: {content_hash[:20]}...")
        memory = get_memory_by_hash(content_hash)
        if not memory:
            print(f"Memory not found: {content_hash}")
            sys.exit(1)
    
    # Show memory details
    content_hash = memory.get("content_hash")
    content = memory.get("content", "")
    old_tags = memory.get("tags", [])
    
    print()
    print(f"Memory ID: {content_hash}")
    print(f"Content ({len(content)} chars): {content[:100]}...")
    print(f"Current tags: {old_tags if old_tags else '(none)'}")
    print()
    
    # Generate new tags
    print("Analyzing content...")
    new_tags = get_suggested_tags(content)
    
    print()
    print("Suggested tags:")
    print(f"  {', '.join(new_tags)}")
    print()
    
    # Show diff
    if old_tags:
        added = set(new_tags) - set(old_tags)
        removed = set(old_tags) - set(new_tags)
        
        if added or removed:
            print("Changes:")
            if added:
                print(f"  + Add: {', '.join(added)}")
            if removed:
                print(f"  - Remove: {', '.join(removed)}")
        else:
            print("No tag changes.")
    
    print()
    
    # Confirm
    if old_tags == new_tags:
        print("Tags are already optimal. No changes needed.")
        return
    
    response = input("Apply new tags? (yes/no): ").strip().lower()
    
    if response != "yes":
        print("Cancelled.")
        return
    
    # Update
    print()
    print("Updating memory...", end=" ", flush=True)
    
    if update_memory_tags(content_hash, new_tags):
        print("✓ Success!")
        print()
        print(f"Updated tags: {', '.join(new_tags)}")
    else:
        print("✗ Failed!")
        sys.exit(1)
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCancelled")
        sys.exit(1)
