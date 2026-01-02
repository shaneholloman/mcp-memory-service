#!/usr/bin/env python3
"""
MCP Memory Service - Auto-Retag Single Memory (Merge Mode)
Automatically generates tags and MERGES them with existing tags.
Preserves manual/specific tags while adding generated ones.
"""

import requests
import sys
from typing import List, Set

API_URL = "http://127.0.0.1:8000/api"
HEADERS = {"Content-Type": "application/json"}

# Tags that should never be auto-removed (specific version/component tags)
PRESERVE_PATTERNS = [
    "v8.", "v1.", "v2.",  # Version tags
    "secondbrain", "shodh", "mcp-memory",  # Project tags
    "vectorize", "cloudflare-", "ketchup", "tcr",  # Technology-specific
]


def should_preserve_tag(tag: str) -> bool:
    """Check if tag should be preserved (not removed by auto-tagging)."""
    for pattern in PRESERVE_PATTERNS:
        if pattern in tag.lower():
            return True
    return False


def get_suggested_tags(content: str) -> List[str]:
    """Generate tags based on content."""
    tags = set()
    content_lower = content.lower()
    
    # Version/Release detection
    if any(x in content_lower for x in ["release", "v8", "v1", "version"]):
        tags.add("release")
    
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
    
    # Project detection
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
            return data["results"][0]["memory"]
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


def merge_tags(old_tags: List[str], suggested_tags: List[str]) -> tuple:
    """
    Merge suggested tags with existing tags.
    
    Returns:
        (merged_tags, added_tags, removed_tags)
    """
    old_set = set(old_tags)
    suggested_set = set(suggested_tags)
    
    # Keep all existing tags that match preserve patterns
    preserved = {tag for tag in old_set if should_preserve_tag(tag)}
    
    # Add all suggested tags except those with preserve patterns
    # (to avoid duplicating tech-specific tags)
    merged = preserved | suggested_set
    
    added = merged - old_set
    removed = old_set - merged
    
    return sorted(list(merged)), sorted(list(added)), sorted(list(removed))


def main():
    """Auto-retag a single memory (merge mode)."""
    print("=" * 80)
    print("MCP Memory Service - Auto-Retag Single Memory (Merge Mode)")
    print("=" * 80)
    print()
    
    if len(sys.argv) < 2:
        print("Usage:")
        print(f"  By content hash: {sys.argv[0]} <content_hash>")
        print(f"  By search query: {sys.argv[0]} --search 'query text'")
        print()
        print("Examples:")
        print(f"  {sys.argv[0]} abc123def456...")
        print(f"  {sys.argv[0]} --search 'cloudflare vectorize'")
        print()
        print("Mode: MERGE - Preserves existing version/project tags")
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
    print(f"Current tags ({len(old_tags)}): {old_tags if old_tags else '(none)'}")
    print()
    
    # Generate new tags
    print("Analyzing content...")
    suggested_tags = get_suggested_tags(content)
    
    # Merge
    merged_tags, added_tags, removed_tags = merge_tags(old_tags, suggested_tags)
    
    print()
    print(f"Suggested tags ({len(suggested_tags)}): {', '.join(suggested_tags)}")
    print()
    print(f"Merged result ({len(merged_tags)} total):")
    print(f"  {', '.join(merged_tags)}")
    print()
    
    # Show diff
    if added_tags or removed_tags:
        print("Changes:")
        if added_tags:
            print(f"  + Add ({len(added_tags)}): {', '.join(added_tags)}")
        if removed_tags:
            print(f"  - Remove ({len(removed_tags)}): {', '.join(removed_tags)}")
    else:
        print("No tag changes needed.")
    
    print()
    
    # Confirm
    if merged_tags == old_tags:
        print("Tags are already optimal. No changes needed.")
        return
    
    response = input("Apply merged tags? (yes/no): ").strip().lower()
    
    if response != "yes":
        print("Cancelled.")
        return
    
    # Update
    print()
    print("Updating memory...", end=" ", flush=True)
    
    if update_memory_tags(content_hash, merged_tags):
        print("✓ Success!")
        print()
        print(f"Updated tags ({len(merged_tags)}): {', '.join(merged_tags)}")
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
