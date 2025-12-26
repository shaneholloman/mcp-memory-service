# AI-Optimized MCP Tool Descriptions
# Ready for integration into src/mcp_memory_service/server.py

STORE_MEMORY_DESC = """Store new information in persistent memory with semantic search capabilities and optional categorization.

USE THIS WHEN:
- User provides information to remember for future sessions (decisions, preferences, facts, code snippets)
- Capturing important context from current conversation ("remember this for later")
- User explicitly says "remember", "save", "store", "keep this", "note that"
- Documenting technical decisions, API patterns, project architecture, user preferences
- Creating knowledge base entries, documentation snippets, troubleshooting notes

THIS IS THE PRIMARY STORAGE TOOL - use it whenever information should persist beyond the current session.

DO NOT USE FOR:
- Temporary conversation context (use native conversation history instead)
- Information already stored (check first with retrieve_memory to avoid duplicates)
- Streaming or real-time data that changes frequently

CONTENT LENGTH LIMITS:
- Cloudflare/Hybrid backends: 800 characters max (auto-splits into chunks if exceeded)
- SQLite-vec backend: No limit
- Auto-chunking preserves context with 50-character overlap at natural boundaries

TAG FORMATS (all supported):
- Array: ["tag1", "tag2"]
- String: "tag1,tag2"
- Single: "single-tag"
- Both tags parameter AND metadata.tags are merged automatically

RETURNS:
- success: Boolean indicating storage status
- message: Status message
- content_hash: Unique identifier for retrieval/deletion (single memory)
- chunks_created: Number of chunks (if content was split)
- chunk_hashes: Array of hashes (if content was split)

Examples:
{
    "content": "User prefers async/await over callbacks in Python projects",
    "metadata": {
        "tags": ["coding-style", "python", "preferences"],
        "type": "preference"
    }
}

{
    "content": "API endpoint /api/v1/users requires JWT token in Authorization header",
    "metadata": {
        "tags": "api-documentation,authentication",
        "type": "reference"
    }
}"""

RETRIEVE_MEMORY_DESC = """Search stored memories using semantic similarity - finds conceptually related content even if exact words differ.

USE THIS WHEN:
- User asks "what do you remember about X", "do we have info on Y", "recall Z"
- Looking for past decisions, preferences, or context from previous sessions
- Need to retrieve related information without exact wording (semantic search)
- General memory lookup where time frame is NOT specified
- User references "last time we discussed", "you should know", "I told you before"

THIS IS THE PRIMARY SEARCH TOOL - use it for most memory lookups.

DO NOT USE FOR:
- Time-based queries ("yesterday", "last week") - use recall_memory instead
- Exact content matching - use exact_match_retrieve instead
- Tag-based filtering - use search_by_tag instead
- Browsing all memories - use list_memories instead (if available in mcp_server.py)

HOW IT WORKS:
- Converts query to vector embedding using the same model as stored memories
- Finds top N most similar memories using cosine similarity
- Returns ranked by relevance score (0.0-1.0, higher is more similar)
- Works across sessions - retrieves memories from any time period

RETURNS:
- Array of matching memories with:
  - content: The stored text
  - content_hash: Unique identifier
  - similarity_score: Relevance score (0.0-1.0)
  - metadata: Tags, type, timestamp, etc.
  - created_at: When memory was stored

Examples:
{
    "query": "python async patterns we discussed",
    "n_results": 5
}

{
    "query": "database connection settings",
    "n_results": 10
}

{
    "query": "user authentication workflow preferences",
    "n_results": 3
}"""

RECALL_MEMORY_DESC = """Retrieve memories using natural language time expressions with optional semantic filtering - combines time-based filtering with semantic search.

USE THIS WHEN:
- User specifies a TIME FRAME in their query ("yesterday", "last week", "in March")
- Looking for memories from a specific period ("what did we discuss last month")
- User says "recently", "a while ago", "during the summer"
- Temporal context is important ("what was decided at our last meeting")
- Need to find when something was discussed or decided

DO NOT USE FOR:
- General memory lookup without time context - use retrieve_memory instead
- Exact content matching - use exact_match_retrieve instead
- Tag-based filtering - use search_by_tag instead

SUPPORTED TIME EXPRESSIONS:
- Relative: "yesterday", "last week", "2 days ago", "3 months ago"
- Seasonal: "last summer", "this winter", "spring 2024"
- Calendar: "last January", "in March", "December 2023"
- Holidays: "Christmas", "Thanksgiving", "New Year"
- Time of day: "yesterday morning", "last Friday evening", "this afternoon"

HOW IT WORKS:
- Parses natural language time expression into date range
- Filters memories by creation timestamp
- Optionally applies semantic search within filtered results
- Returns memories sorted by time (newest first) or relevance (if query includes search terms)

RETURNS:
- Array of matching memories from specified time period with:
  - content: The stored text
  - created_at: When memory was stored (used for time filtering)
  - similarity_score: Relevance score if semantic search applied
  - metadata: Tags, type, etc.

Examples:
{
    "query": "recall what I stored last week"
}

{
    "query": "find information about databases from two months ago",
    "n_results": 5
}

{
    "query": "decisions we made yesterday afternoon",
    "n_results": 10
}

{
    "query": "python code snippets from last March",
    "n_results": 3
}"""

SEARCH_BY_TAG_DESC = """Search memories by exact tag matching - retrieves all memories categorized with specific tags (OR logic by default).

USE THIS WHEN:
- User asks to filter by category ("show me all 'api-docs' memories", "find 'important' notes")
- Need to retrieve memories of a specific type without semantic search
- User wants to browse a category ("what do we have tagged 'python'")
- Looking for all memories with a particular classification
- User says "show me everything about X" where X is a known tag

DO NOT USE FOR:
- Semantic search - use retrieve_memory instead
- Time-based queries - use recall_memory instead
- Finding specific content - use exact_match_retrieve instead

HOW IT WORKS:
- Exact string matching on memory tags (case-sensitive)
- Returns memories matching ANY of the specified tags (OR logic)
- No semantic search - purely categorical filtering
- No similarity scoring - all results are equally relevant

TAG FORMATS (all supported):
- Array: ["tag1", "tag2"]
- String: "tag1,tag2"

RETURNS:
- Array of all memories with matching tags:
  - content: The stored text
  - tags: Array of tags (will include at least one from search)
  - content_hash: Unique identifier
  - metadata: Additional memory metadata
  - No similarity score (categorical match, not semantic)

Examples:
{
    "tags": ["important", "reference"]
}

{
    "tags": "python,async,best-practices"
}

{
    "tags": ["api-documentation"]
}"""

DELETE_MEMORY_DESC = """Delete a specific memory by its unique content hash identifier - permanent removal of a single memory entry.

USE THIS WHEN:
- User explicitly requests deletion of a specific memory ("delete that", "remove the memory about X")
- After showing user a memory and they want it removed
- Correcting mistakenly stored information
- User says "forget about X", "delete the note about Y", "remove that memory"
- Have the content_hash from a previous retrieve/search operation

DO NOT USE FOR:
- Deleting multiple memories - use delete_by_tag, delete_by_tags, or delete_by_all_tags instead
- Deleting by content without hash - search first with retrieve_memory to get the hash
- Bulk cleanup - use cleanup_duplicates or delete_by_tag instead
- Time-based deletion - use delete_by_timeframe or delete_before_date instead

IMPORTANT:
- This is a PERMANENT operation - memory cannot be recovered after deletion
- You must have the exact content_hash (obtained from search/retrieve operations)
- Only deletes the single memory matching the hash

HOW TO GET content_hash:
1. First search for the memory using retrieve_memory, recall_memory, or search_by_tag
2. Memory results include "content_hash" field
3. Use that hash in this delete operation

RETURNS:
- success: Boolean indicating if deletion succeeded
- message: Status message (e.g., "Memory deleted successfully" or error details)

Examples:
# Step 1: Find the memory
retrieve_memory(query: "outdated API documentation")
# Returns: [{content_hash: "a1b2c3d4e5f6...", content: "...", ...}]

# Step 2: Delete it
{
    "content_hash": "a1b2c3d4e5f6..."
}"""

CHECK_DATABASE_HEALTH_DESC = """Check database health, storage backend status, and retrieve comprehensive memory service statistics.

USE THIS WHEN:
- User asks "how many memories are stored", "is the database working", "memory service status"
- Diagnosing performance issues or connection problems
- User wants to know storage backend configuration (SQLite/Cloudflare/Hybrid)
- Checking if memory service is functioning correctly
- Need to verify successful initialization or troubleshoot errors
- User asks "what storage backend are we using"

DO NOT USE FOR:
- Searching or retrieving specific memories - use retrieve_memory instead
- Getting cache performance stats - use get_cache_stats instead (if available)
- Listing actual memory content - this only returns counts and status

WHAT IT CHECKS:
- Database connectivity and responsiveness
- Storage backend type (sqlite_vec, cloudflare, hybrid)
- Total memory count in database
- Database file size and location (for SQLite backends)
- Sync status (for hybrid backend)
- Configuration details (embedding model, index names, etc.)

RETURNS:
- status: "healthy" or error status
- backend: Storage backend type (sqlite_vec/cloudflare/hybrid)
- total_memories: Count of stored memories
- database_info: Path, size, configuration details
- timestamp: When health check was performed
- Any error messages or warnings

Examples:
No parameters required - just call it:
{}

Common use cases:
- User: "How many memories do I have?" → check_database_health()
- User: "Is the memory service working?" → check_database_health()
- User: "What backend are we using?" → check_database_health()"""

EXACT_MATCH_RETRIEVE_DESC = """Retrieve memories using exact substring matching - finds memories containing the EXACT text string (case-sensitive).

USE THIS WHEN:
- Looking for a specific phrase, code snippet, or exact wording
- User says "find the exact text", "search for this specific phrase"
- Need to verify if exact content was stored (duplicate checking)
- Debugging or troubleshooting memory storage issues
- Looking for specific error messages, commands, or technical terms that must match exactly

DO NOT USE FOR:
- Semantic search or related concepts - use retrieve_memory instead
- Time-based queries - use recall_memory instead
- Tag-based filtering - use search_by_tag instead
- General information retrieval - this is too strict for normal use

HOW IT WORKS:
- Case-sensitive exact substring matching
- No semantic understanding - purely text matching
- Returns memories where content contains the exact search string
- Much faster than semantic search but requires exact wording

RETURNS:
- Array of memories containing the exact search string:
  - content: The stored text (will contain search string)
  - content_hash: Unique identifier
  - metadata: Tags, type, timestamp
  - No similarity score (exact match, not semantic similarity)

Examples:
{
    "content": "async def process_request"
}

{
    "content": "ERROR: Connection refused on port 5432"
}

{
    "content": "User preference: dark mode enabled"
}

Note: If no exact matches found, returns empty array. Consider using retrieve_memory for fuzzy/semantic matching."""

LIST_MEMORIES_DESC = """List stored memories with pagination and optional filtering - browse all memories in pages rather than searching.

USE THIS WHEN:
- User wants to browse/explore all memories ("show me my memories", "list everything")
- Need to paginate through large result sets
- Filtering by tag OR memory type for categorical browsing
- User asks "what do I have stored", "show me all notes", "browse my memories"
- Want to see memories without searching for specific content

DO NOT USE FOR:
- Searching for specific content - use retrieve_memory instead
- Time-based queries - use recall_memory instead
- Finding exact text - use exact_match_retrieve instead

HOW IT WORKS:
- Returns memories in pages (default 10 per page)
- Optional filtering by single tag or memory type
- Sorted by creation time (newest first)
- Supports pagination through large datasets

PAGINATION:
- page: 1-based page number (default 1)
- page_size: Number of results per page (default 10, max usually 100)
- Returns total count and page info for navigation

RETURNS:
- memories: Array of memory objects for current page
- total: Total count of matching memories
- page: Current page number
- page_size: Results per page
- total_pages: Total pages available

Examples:
{
    "page": 1,
    "page_size": 10
}

{
    "page": 2,
    "page_size": 20,
    "tag": "python"
}

{
    "page": 1,
    "page_size": 50,
    "memory_type": "decision"
}"""


# INTEGRATION GUIDE
# =================
#
# For server.py (lines ~1517-1906):
# Replace the existing description= strings with these variables:
#
# Line 1517: description=STORE_MEMORY_DESC
# Line 1582: description=RECALL_MEMORY_DESC
# Line 1618: description=RETRIEVE_MEMORY_DESC
# Line 1691: description=SEARCH_BY_TAG_DESC
# Line 1721: description=DELETE_MEMORY_DESC
# Line 1867: description=EXACT_MATCH_RETRIEVE_DESC
# Line 1906: description=CHECK_DATABASE_HEALTH_DESC
#
# For mcp_server.py (if list_memories exists):
# Add: description=LIST_MEMORIES_DESC
