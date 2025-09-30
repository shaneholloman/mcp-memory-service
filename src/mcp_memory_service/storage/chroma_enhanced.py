# Copyright 2024 Heinrich Krupp
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Enhanced delete_by_tag methods to fix Issue 5: Delete Tag Function Ambiguity

import json
from typing import List, Dict, Any

def _parse_tags_from_meta(meta: Dict[str, Any]) -> List[str]:
    """
    Helper function to parse tags from metadata consistently.

    Handles both comma-separated (standard) and JSON formats (legacy).

    Args:
        meta: Metadata dictionary containing tags

    Returns:
        List of parsed tags
    """
    tags_string = meta.get("tags", "")
    if tags_string:
        # Handle both comma-separated (standard) and JSON formats (legacy)
        if tags_string.startswith("[") and tags_string.endswith("]"):
            try:
                return json.loads(tags_string)
            except json.JSONDecodeError:
                return []
        else:
            # Standard comma-separated format
            return [tag.strip() for tag in tags_string.split(",") if tag.strip()]
    else:
        return []

async def delete_by_tag(self, tag_or_tags) -> Tuple[int, str]:
    """
    Enhanced delete_by_tag that accepts both single tag (string) and multiple tags (list).
    
    Args:
        tag_or_tags: Either a single tag (string) or multiple tags (list of strings)
        
    Returns:
        Tuple of (count_deleted, message)
    """
    try:
        # Normalize input to list of tags
        if isinstance(tag_or_tags, str):
            tags_to_delete = [tag_or_tags.strip()]
        elif isinstance(tag_or_tags, list):
            tags_to_delete = [str(tag).strip() for tag in tag_or_tags if str(tag).strip()]
        else:
            return 0, f"Invalid tag format. Expected string or list, got {type(tag_or_tags)}"
        
        if not tags_to_delete:
            return 0, "No valid tags provided"
        
        # Get all documents from ChromaDB
        results = self.collection.get(include=["metadatas"])
        
        ids_to_delete = []
        matched_tags = set()
        
        if results["ids"]:
            for i, meta in enumerate(results["metadatas"]):
                retrieved_tags = _parse_tags_from_meta(meta)

                # Check if any of the tags to delete are in this memory's tags
                for tag_to_delete in tags_to_delete:
                    if tag_to_delete in retrieved_tags:
                        ids_to_delete.append(results["ids"][i])
                        matched_tags.add(tag_to_delete)
                        break  # No need to check other tags for this memory
        
        if not ids_to_delete:
            tags_str = ", ".join(tags_to_delete)
            return 0, f"No memories found with tag(s): {tags_str}"
        
        # Delete memories
        self.collection.delete(ids=ids_to_delete)
        
        # Create informative message
        matched_tags_str = ", ".join(sorted(matched_tags))
        if len(tags_to_delete) == 1:
            message = f"Successfully deleted {len(ids_to_delete)} memories with tag: {matched_tags_str}"
        else:
            message = f"Successfully deleted {len(ids_to_delete)} memories with tag(s): {matched_tags_str}"
        
        return len(ids_to_delete), message
        
    except Exception as e:
        logger.error(f"Error deleting memories by tag(s): {e}")
        return 0, f"Error deleting memories by tag(s): {e}"

async def delete_by_tags(self, tags: List[str]) -> Tuple[int, str]:
    """
    Explicitly delete memories by multiple tags (for clarity).
    
    Args:
        tags: List of tag strings to delete
        
    Returns:
        Tuple of (count_deleted, message)
    """
    return await self.delete_by_tag(tags)

# Alternative implementation: delete memories that match ALL specified tags
async def delete_by_all_tags(self, tags: List[str]) -> Tuple[int, str]:
    """
    Delete memories that contain ALL of the specified tags.
    
    Args:
        tags: List of tags - memories must contain ALL of these tags to be deleted
        
    Returns:
        Tuple of (count_deleted, message)
    """
    try:
        if not tags:
            return 0, "No tags provided"
        
        # Normalize tags
        tags_to_match = [str(tag).strip() for tag in tags if str(tag).strip()]
        if not tags_to_match:
            return 0, "No valid tags provided"
        
        # Get all documents from ChromaDB
        results = self.collection.get(include=["metadatas"])
        
        ids_to_delete = []
        
        if results["ids"]:
            for i, meta in enumerate(results["metadatas"]):
                retrieved_tags = _parse_tags_from_meta(meta)

                # Check if ALL tags are present in this memory
                if all(tag in retrieved_tags for tag in tags_to_match):
                    ids_to_delete.append(results["ids"][i])
        
        if not ids_to_delete:
            tags_str = ", ".join(tags_to_match)
            return 0, f"No memories found containing ALL tags: {tags_str}"
        
        # Delete memories
        self.collection.delete(ids=ids_to_delete)
        
        tags_str = ", ".join(tags_to_match)
        message = f"Successfully deleted {len(ids_to_delete)} memories containing ALL tags: {tags_str}"
        
        return len(ids_to_delete), message
        
    except Exception as e:
        logger.error(f"Error deleting memories by all tags: {e}")
        return 0, f"Error deleting memories by all tags: {e}"
