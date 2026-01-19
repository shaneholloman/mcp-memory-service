#!/usr/bin/env python3
"""
Memory Ontology & Tag Improvement Script

Improves memory ontology classification and tag standardization in chunks of 50.
- Re-classifies memory types (moderate strategy, high confidence only)
- Converts legacy tags to namespace format (topic:, proj:, q:)
- Handles bug-fix tags context-based
- Never modifies content, only updates metadata

Usage:
    python scripts/maintenance/improve_memory_ontology.py [--dry-run] [--start-chunk N]
"""

import requests
import json
import sys
import time
import urllib3
from typing import List, Optional, Tuple, Set
from datetime import datetime

# Suppress SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# API Configuration
API_BASE_URLS = ["http://127.0.0.1:8000/api", "https://127.0.0.1:8000/api"]
HEADERS = {"Content-Type": "application/json"}


def get_working_api_url() -> str:
    """Find which API URL is accessible (HTTP or HTTPS)."""
    for url in API_BASE_URLS:
        try:
            verify = False if url.startswith("https") else True
            response = requests.get(f"{url}/health", timeout=5, verify=verify)
            if response.status_code == 200:
                return url
        except Exception:
            continue
    print("Unable to connect to MCP Memory Service API")
    sys.exit(1)


API_URL = get_working_api_url()
VERIFY_SSL = False if API_URL.startswith("https") else True

# Ontology types from ontology.py
ONTOLOGY_TYPES = {
    "observation": ["code_edit", "file_access", "search", "command", "conversation"],
    "decision": ["architecture", "tool_choice", "approach", "configuration"],
    "learning": ["insight", "best_practice", "anti_pattern", "gotcha"],
    "error": ["bug", "failure", "exception", "timeout"],
    "pattern": ["recurring_issue", "code_smell", "design_pattern", "workflow"],
}

# Tag patterns for conversion
TOPIC_TAGS = [
    "azure",
    "terraform",
    "authentication",
    "debugging",
    "performance",
    "release",
    "versioning",
    "dashboard",
    "testing",
    "documentation",
    "troubleshooting",
    "architecture",
    "design",
    "security",
    "api",
    "database",
    "migration",
    "integration",
    "monitoring",
]

PROJECT_TAGS = {
    "mcp-memory-service": "proj:mcp-memory-service",
    "mcp": "proj:mcp",
    "ops-terraform-hosting": "proj:ops-terraform-hosting",
    "outlook-assistant": "proj:outlook-assistant",
    "dmihsdt": "proj:dmihsdt",
}

QUALITY_TAGS = {
    "critical": "q:high",
    "important": "q:high",
    "urgent": "q:high",
    "low-priority": "q:low",
}

# Reserved tags to never merge (user-defined)
USER_DEFINED_PATTERNS = ["custom:", "user:", "personal:"]


def make_request(method, endpoint, **kwargs):
    """Make HTTP request with proper SSL handling."""
    url = f"{API_URL}{endpoint}"
    kwargs["verify"] = kwargs.get("verify", VERIFY_SSL)
    return requests.request(method, url, **kwargs)


def classify_memory_type(mem: dict) -> Optional[str]:
    """
    Classify memory type based on tags and content (moderate strategy).
    Only returns new type if high confidence.
    """
    tags_lower = [t.lower() for t in mem.get("tags", [])]
    content_lower = mem.get("content", "").lower()
    current_type = mem.get("memory_type", "observation")

    # Skip if already properly classified (non-observation)
    if current_type != "observation":
        return None

    # Skip session summaries (mixed content)
    if "session-summary" in tags_lower or "session" in tags_lower:
        return None

    # High confidence patterns - only change these
    # Architecture decision
    if "architecture-decision" in tags_lower:
        return "decision/architecture"

    # Best practice
    if "best-practice" in tags_lower or "best_practice" in tags_lower:
        return "learning/best_practice"

    # Anti-pattern
    if "anti-pattern" in tags_lower or "anti_pattern" in tags_lower:
        return "learning/anti_pattern"

    # Gotcha
    if "gotcha" in tags_lower:
        return "learning/gotcha"

    # Workflow pattern
    if "workflow" in tags_lower:
        return "pattern/workflow"

    # Design pattern
    if "design-pattern" in tags_lower or "design_pattern" in tags_lower:
        return "pattern/design_pattern"

    # Code smell
    if "code-smell" in tags_lower or "code_smell" in tags_lower:
        return "pattern/code_smell"

    # Context-based bug handling
    if "bug-fix" in tags_lower or "bug_fix" in tags_lower:
        # Check context: is it what was learned or error itself?
        success_indicators = [
            "resolved",
            "fixed",
            "solved",
            "success",
            "working",
            "completed",
        ]
        error_indicators = ["error", "exception", "failed", "crashed", "broke"]

        if any(indicator in content_lower for indicator in success_indicators):
            return "learning/insight"  # What was learned from fixing
        elif any(indicator in content_lower for indicator in error_indicators):
            return "error/bug"  # Documenting the error itself

    return None  # No high-confidence classification


def convert_tags_to_namespace(tags: List[str]) -> List[str]:
    """
    Convert legacy tags to namespace format (smart merge).
    - Category tags -> replace with namespace version
    - User-defined tags -> keep both
    """
    new_tags = []
    tag_lower_map = {t.lower(): t for t in tags}

    for tag in tags:
        tag_lower = tag.lower()

        # Skip if already namespaced
        if ":" in tag:
            new_tags.append(tag)
            continue

        # Check if it's a project tag
        if tag_lower in PROJECT_TAGS:
            namespaced = PROJECT_TAGS[tag_lower]
            if namespaced not in new_tags:
                new_tags.append(namespaced)
            continue

        # Check if it's a quality tag
        if tag_lower in QUALITY_TAGS:
            namespaced = QUALITY_TAGS[tag_lower]
            if namespaced not in new_tags:
                new_tags.append(namespaced)
            continue

        # Check if it's a topic tag
        if tag_lower in TOPIC_TAGS:
            namespaced = f"topic:{tag_lower}"
            # Smart merge: replace legacy version
            if namespaced not in new_tags:
                new_tags.append(namespaced)
            continue

        # User-defined tag or unknown - keep as-is
        new_tags.append(tag)

    return new_tags


def should_update_memory(mem: dict) -> Tuple[bool, dict]:
    """
    Determine if memory needs updates and what changes to make.
    Returns (needs_update, updates_dict).
    """
    updates = {}

    # Check memory type
    new_type = classify_memory_type(mem)
    if new_type:
        updates["memory_type"] = new_type

    # Check tags
    current_tags = mem.get("tags", [])
    converted_tags = convert_tags_to_namespace(current_tags)

    if converted_tags != current_tags:
        # Sort tags for consistency
        updates["tags"] = sorted(converted_tags)

    return (bool(updates), updates)


def update_memory(content_hash: str, updates: dict, dry_run: bool = False) -> bool:
    """Update memory metadata via API."""
    if dry_run:
        print(f"  [DRY RUN] Would update: {content_hash[:12]}...")
        return True

    try:
        response = make_request(
            "PUT", f"/memories/{content_hash}", json=updates, headers=HEADERS
        )

        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                return True
            else:
                print(f"  Update failed: {result.get('message', 'Unknown error')}")
                return False
        else:
            print(f"  HTTP {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print(f"  Error: {e}")
        return False


def process_chunk(chunk_number: int, dry_run: bool = False) -> dict:
    """Process a chunk of 50 memories."""
    print(f"\n{'=' * 70}")
    print(f"Processing chunk {chunk_number}")
    print(f"{'=' * 70}\n")

    # Fetch chunk
    page = chunk_number
    page_size = 50

    response = make_request(
        "GET", "/memories", params={"page": page, "page_size": page_size}
    )
    response.raise_for_status()
    data = response.json()

    memories = data.get("memories", [])
    if not memories:
        return {"processed": 0, "updated": 0, "skipped": 0}

    # Process memories
    stats = {
        "processed": 0,
        "updated": 0,
        "type_changed": 0,
        "tags_changed": 0,
        "skipped": 0,
    }

    for mem in memories:
        stats["processed"] += 1

        needs_update, updates = should_update_memory(mem)

        if not needs_update:
            stats["skipped"] += 1
            continue

        # Show what will change
        content_hash = mem.get("content_hash", "")
        content_preview = mem.get("content", "")[:60]

        print(f"Memory {stats['processed']}: {content_preview}...")

        if "memory_type" in updates:
            old_type = mem.get("memory_type", "observation")
            new_type = updates["memory_type"]
            print(f"  Type: {old_type} → {new_type}")
            stats["type_changed"] += 1

        if "tags" in updates:
            old_tags = mem.get("tags", [])
            new_tags = updates["tags"]
            print(f"  Tags: {len(old_tags)} → {len(new_tags)} tags")

            # Show changed tags
            added = set(new_tags) - set(old_tags)
            removed = set(old_tags) - set(new_tags)

            if added:
                print(f"    Added: {', '.join(list(added)[:5])}")
            if removed:
                print(f"    Removed: {', '.join(list(removed)[:5])}")

            stats["tags_changed"] += 1

        # Perform update
        if update_memory(content_hash, updates, dry_run):
            stats["updated"] += 1
            print("  ✓ Updated")
        else:
            print("  ✗ Failed")

        print()

    # Summary for chunk
    print(f"\nChunk {chunk_number} Summary:")
    print(f"  Processed: {stats['processed']}")
    print(f"  Updated: {stats['updated']}")
    print(f"  Type changes: {stats['type_changed']}")
    print(f"  Tag changes: {stats['tags_changed']}")
    print(f"  Skipped: {stats['skipped']}")

    return stats


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Improve memory ontology and tag standardization"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Show changes without applying them"
    )
    parser.add_argument(
        "--start-chunk",
        type=int,
        default=1,
        help="Start from specific chunk (default: 1)",
    )
    args = parser.parse_args()

    # Get total count
    response = make_request("GET", "/memories", params={"page": 1, "page_size": 1})
    total_memories = response.json().get("total", 0)
    total_chunks = (total_memories + 49) // 50

    print("=" * 70)
    print("Memory Ontology & Tag Improvement Script")
    print("=" * 70)
    print(f"Total memories: {total_memories}")
    print(f"Total chunks: {total_chunks}")
    print(f"Starting from chunk: {args.start_chunk}")
    print(f"Dry run: {args.dry_run}")
    print(f"API: {API_URL}")
    print("=" * 70)

    if args.dry_run:
        print("\n⚠️  DRY RUN MODE - No changes will be made\n")

    # Process chunks
    global_stats = {
        "processed": 0,
        "updated": 0,
        "type_changed": 0,
        "tags_changed": 0,
        "skipped": 0,
    }

    start_time = time.time()

    for chunk_num in range(args.start_chunk, total_chunks + 1):
        chunk_stats = process_chunk(chunk_num, args.dry_run)

        for key in global_stats:
            global_stats[key] += chunk_stats[key]

        # Small delay between chunks
        if not args.dry_run and chunk_num < total_chunks:
            time.sleep(0.5)

    # Final summary
    duration = time.time() - start_time

    print("\n" + "=" * 70)
    print("FINAL SUMMARY")
    print("=" * 70)
    print(f"Total processed: {global_stats['processed']}")
    print(f"Total updated: {global_stats['updated']}")
    print(f"Type changes: {global_stats['type_changed']}")
    print(f"Tag changes: {global_stats['tags_changed']}")
    print(f"Skipped: {global_stats['skipped']}")
    print(f"Duration: {duration:.1f}s")
    if global_stats["processed"] > 0:
        print(
            f"Average per memory: {(duration / global_stats['processed']) * 1000:.1f}ms"
        )

    if args.dry_run:
        print("\n⚠️  DRY RUN COMPLETE - Use without --dry-run to apply changes")

    print("=" * 70)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)
