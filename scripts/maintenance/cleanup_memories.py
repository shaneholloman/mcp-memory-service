#!/usr/bin/env python3
"""
MCP Memory Service - Cleanup Script
Separates test memories from valuable ones, retags valuable ones, exports obsolete for deletion.
"""

import requests
import json
import sys
from typing import List, Tuple
from datetime import datetime
from urllib3.exceptions import InsecureRequestWarning

# Suppress SSL warnings for self-signed certificates
import urllib3

urllib3.disable_warnings(InsecureRequestWarning)

# Try HTTP first, then HTTPS
API_BASE_URLS = ["http://127.0.0.1:8000/api", "https://127.0.0.1:8000/api"]
HEADERS = {"Content-Type": "application/json"}


def get_working_api_url() -> str:
    """Find which API URL is accessible (HTTP or HTTPS)."""
    for url in API_BASE_URLS:
        try:
            verify = False if url.startswith("https") else True
            response = requests.get(f"{url}/health", timeout=5, verify=verify)
            if response.status_code == 200:
                print(f"Using API: {url}")
                return url
        except Exception:
            continue
    print("Unable to connect to MCP Memory Service API")
    sys.exit(1)


API_URL = get_working_api_url()

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

    # Check test patterns
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
    """Suggest tags based on content."""
    tags = []
    content_lower = content.lower()

    # Auto-detect tags
    if "release" in content_lower or "v8" in content_lower or "v1" in content_lower:
        tags.append("release")
    if "api" in content_lower:
        tags.append("api")
    if "cloudflare" in content_lower:
        tags.append("cloudflare")
    if "session" in content_lower or "summary" in content_lower:
        tags.append("session-summary")
    if "ketchup" in content_lower or "tcr" in content_lower:
        tags.append("workflow")
    if "sync" in content_lower or "race" in content_lower:
        tags.append("sync")
    if "secondary" in content_lower or "secondbrain" in content_lower.replace("-", ""):
        tags.append("secondbrain")

    # Add cleanup-related tag if none found
    if not tags:
        tags.append("cleanup-needed")

    return tags


def make_request(method, endpoint, **kwargs):
    """Make HTTP request with proper SSL handling."""
    verify = False if API_URL.startswith("https") else True
    url = f"{API_URL}{endpoint}"
    kwargs["verify"] = kwargs.get("verify", verify)
    response = requests.request(method, url, **kwargs)
    response.raise_for_status()
    return response


def get_all_untagged_memories() -> List[dict]:
    """Fetch all untagged memories."""
    untagged = []
    page = 1

    print("Fetching untagged memories...")

    while True:
        response = make_request(
            "GET", "/memories", params={"page": page, "page_size": 100}
        )
        data = response.json()

        if not data.get("memories"):
            break

        for memory in data["memories"]:
            if not memory.get("tags") or len(memory["tags"]) == 0:
                untagged.append(memory)

        print(
            f"  Page {page}: {len(data['memories'])} memories, "
            f"{len([m for m in data['memories'] if not m.get('tags') or len(m['tags']) == 0])} untagged"
        )

        if not data.get("has_more"):
            break

        page += 1

    return untagged


def tag_memory(memory_id: str, tags: List[str]) -> bool:
    """Tag a single memory."""
    try:
        response = make_request(
            "PUT", f"/memories/{memory_id}", json={"tags": tags}, headers=HEADERS
        )
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"Error tagging {memory_id}: {e}")
        return False


def main():
    """Main cleanup workflow."""
    print("=" * 70)
    print("MCP Memory Service - Memory Cleanup")
    print("=" * 70)
    print()

    # Fetch all untagged
    untagged = get_all_untagged_memories()
    print(f"\nTotal untagged memories: {len(untagged)}\n")

    # Classify
    test_memories = []
    valuable_memories = []
    questionable_memories = []

    for memory in untagged:
        content = memory.get("content", "")

        if is_test_memory(content):
            test_memories.append(memory)
        elif should_keep(content):
            valuable_memories.append(memory)
        else:
            questionable_memories.append(memory)

    print(f"Classification:")
    print(f"  ✗ Test memories: {len(test_memories)}")
    print(f"  ✓ Valuable (to retag): {len(valuable_memories)}")
    print(f"  ? Questionable: {len(questionable_memories)}")
    print()

    # Show questionable for manual review
    if questionable_memories:
        print("Questionable memories (manual review needed):")
        for i, mem in enumerate(questionable_memories[:10], 1):
            print(f"  {i}. {mem['content'][:70]}...")
        if len(questionable_memories) > 10:
            print(f"  ... and {len(questionable_memories) - 10} more")
        print()

    # Retag valuable ones
    if valuable_memories:
        print("Retagging valuable memories...")
        retagged = 0
        for memory in valuable_memories:
            content = memory.get("content", "")
            tags = get_suggested_tags(content)

            if tag_memory(memory.get("content_hash"), tags):
                retagged += 1
                print(f"  ✓ Tagged with {tags}")

        print(f"\nRetagged {retagged}/{len(valuable_memories)} memories\n")

    # Export deletion list
    deletion_candidates = test_memories + questionable_memories

    if deletion_candidates:
        # Save to file for manual review
        export_file = "memories_for_deletion.json"
        with open(export_file, "w") as f:
            json.dump(
                {
                    "count": len(deletion_candidates),
                    "generated_at": datetime.now().isoformat(),
                    "memories": [
                        {
                            "content_hash": m.get("content_hash"),
                            "content": m.get("content")[:100],
                            "type": m.get("memory_type"),
                            "created": m.get("created_at_iso"),
                        }
                        for m in deletion_candidates[:20]  # First 20 for preview
                    ],
                },
                f,
                indent=2,
            )

        print(f"Export for deletion: {export_file}")
        print(f"  Memories to delete: {len(deletion_candidates)}")
        print(f"    - Test: {len(test_memories)}")
        print(f"    - Questionable: {len(questionable_memories)}")
        print()
        print("Next steps:")
        print("  1. Review memories_for_deletion.json")
        print("  2. Use Dashboard UI to delete remaining untagged memories")
        print("  3. Or use: DELETE /api/memories/{content_hash}")

    print("\n" + "=" * 70)
    print("Cleanup summary complete!")
    print("=" * 70)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCleanup cancelled")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
