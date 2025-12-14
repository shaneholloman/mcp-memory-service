#!/usr/bin/env python3
"""
Retroactive Project Tag Addition Script

Adds 'mcp-memory-service' tag to memories that are about the project but lack the tag.
This fixes historical data where project tagging was inconsistent.

Usage:
    python scripts/maintenance/add_project_tags.py --dry-run  # Preview changes
    python scripts/maintenance/add_project_tags.py            # Apply changes
"""

import argparse
import asyncio
import sys
from pathlib import Path
from typing import List, Dict

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from mcp_memory_service.storage.factory import create_storage_instance
from mcp_memory_service import config
from mcp_memory_service.config import SQLITE_VEC_PATH


PROJECT_TAG = "mcp-memory-service"

# Keywords that indicate memory is about this project
# More specific to avoid false positives
PROJECT_KEYWORDS = [
    "mcp-memory-service",
    "session-start hook",
    "session-end hook",
    "memory awareness hook",
    "hybrid backend",
    "sqlite-vec",
    "memory consolidation",
    "quality system",
    "onnx ranker",
    "memory scorer",
    "session consolidation",
    "mcp memory",
    "mcp_memory_service",
]


async def find_memories_needing_tags(storage) -> List[Dict]:
    """Find memories that need project tag added."""
    print(f"🔍 Scanning for memories missing '{PROJECT_TAG}' tag...")

    # Get all memories
    all_memories = await storage.get_all_memories()

    needs_tag = []
    already_tagged = []

    for memory in all_memories:
        # Check if already has project tag
        tags = memory.tags if hasattr(memory, 'tags') else []
        if PROJECT_TAG in tags:
            already_tagged.append(memory)
            continue

        # Check if memory content references the project
        content_lower = memory.content.lower() if memory.content else ""

        # Check for project keywords
        has_keyword = any(keyword in content_lower for keyword in PROJECT_KEYWORDS)

        if has_keyword:
            needs_tag.append({
                'memory': memory,
                'content_hash': memory.content_hash,
                'current_tags': tags,
                'reason': 'Contains project keywords'
            })

    print(f"✅ Already tagged: {len(already_tagged)} memories")
    print(f"⚠️  Missing tag: {len(needs_tag)} memories")

    return needs_tag


async def update_memory_tags(storage, memories_to_update: List[Dict], dry_run: bool = True):
    """Update memories to add project tag."""

    if dry_run:
        print("\n📋 DRY RUN - No changes will be made\n")
    else:
        print("\n✏️  APPLYING CHANGES\n")

    updated_count = 0
    failed_count = 0

    for item in memories_to_update:
        memory = item['memory']
        content_hash = item['content_hash']
        current_tags = item['current_tags']

        # Prepend project tag (most important goes first)
        new_tags = [PROJECT_TAG] + [tag for tag in current_tags if tag != PROJECT_TAG]

        # Show what would change
        print(f"Memory: {content_hash[:12]}...")
        print(f"  Current tags: {', '.join(current_tags) if current_tags else '(none)'}")
        print(f"  New tags: {', '.join(new_tags)}")
        print(f"  Reason: {item['reason']}")
        print()

        if not dry_run:
            try:
                # Update metadata while preserving everything else
                success, message = await storage.update_memory_metadata(
                    content_hash=content_hash,
                    updates={'tags': new_tags},
                    preserve_timestamps=True
                )
                if success:
                    updated_count += 1
                else:
                    print(f"❌ Failed to update {content_hash[:12]}: {message}")
                    failed_count += 1
            except Exception as e:
                print(f"❌ Failed to update {content_hash[:12]}: {e}")
                failed_count += 1
        else:
            updated_count += 1

    return updated_count, failed_count


async def main():
    parser = argparse.ArgumentParser(
        description="Add project tags to memories that are missing them"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without applying them (default)"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually apply the changes (use with caution)"
    )

    args = parser.parse_args()

    # Default to dry-run unless --apply is specified
    dry_run = not args.apply

    # Load configuration and storage
    print("🔧 Loading configuration...")
    storage = await create_storage_instance(SQLITE_VEC_PATH, server_type='script')

    print(f"📦 Storage backend: {config.STORAGE_BACKEND}")
    print()

    # Find memories needing tags
    memories_to_update = await find_memories_needing_tags(storage)

    if not memories_to_update:
        print("✅ All project-related memories already have the correct tag!")
        return

    print(f"\n📊 Found {len(memories_to_update)} memories to update\n")

    # Show sample of first 5
    print("Sample memories (first 5):")
    for item in memories_to_update[:5]:
        content_preview = item['memory'].content[:100] if item['memory'].content else ""
        print(f"  - {item['content_hash'][:12]}: {content_preview}...")

    if len(memories_to_update) > 5:
        print(f"  ... and {len(memories_to_update) - 5} more")

    print()

    # Confirm if not dry-run
    if not dry_run:
        confirm = input(f"⚠️  Update {len(memories_to_update)} memories? (yes/no): ")
        if confirm.lower() != 'yes':
            print("❌ Cancelled by user")
            return

    # Update tags
    updated, failed = await update_memory_tags(storage, memories_to_update, dry_run)

    # Summary
    print("\n" + "="*60)
    if dry_run:
        print(f"📋 DRY RUN COMPLETE")
        print(f"Would update: {updated} memories")
        print("\nTo apply changes, run with --apply flag:")
        print("  python scripts/maintenance/add_project_tags.py --apply")
    else:
        print(f"✅ UPDATE COMPLETE")
        print(f"Updated: {updated} memories")
        if failed > 0:
            print(f"Failed: {failed} memories")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
