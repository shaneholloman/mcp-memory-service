# HTTP Generic Integration Guide

Connect any agent framework or HTTP client to mcp-memory-service using the REST API.

## Server Setup

```bash
pip install mcp-memory-service
MCP_ALLOW_ANONYMOUS_ACCESS=true memory server --http
# Running at http://localhost:8000
```

With API key authentication:
```bash
MCP_API_KEY=your-secret-key memory server --http
# Include header: Authorization: Bearer your-secret-key
```

## All REST Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/memories` | Store a new memory |
| `GET` | `/api/memories` | List memories (paginated) |
| `GET` | `/api/memories/{hash}` | Get memory by hash |
| `PATCH` | `/api/memories/{hash}` | Update memory tags/type/metadata |
| `DELETE` | `/api/memories/{hash}` | Delete a memory |
| `POST` | `/api/memories/search` | Semantic + keyword search |
| `GET` | `/api/memories/tags` | List all tags with counts |
| `GET` | `/api/health` | Health check |
| `GET` | `/api/stats` | Storage statistics |
| `POST` | `/api/consolidation/run` | Trigger memory consolidation |
| `GET` | `/api/consolidation/status` | Consolidation status |
| `GET` | `/api/graph/associations/{hash}` | Get memory associations |
| `POST` | `/api/graph/associations` | Store association between memories |
| `GET` | `/api/analytics/relationship-types` | Graph relationship type stats |
| `GET` | `/sse/events` | Server-Sent Events stream |

## Authentication Patterns

```bash
# Anonymous (MCP_ALLOW_ANONYMOUS_ACCESS=true)
curl http://localhost:8000/api/memories

# API key
curl -H "Authorization: Bearer $MCP_API_KEY" http://localhost:8000/api/memories

# OAuth (see docs/oauth/)
curl -H "Authorization: Bearer $ACCESS_TOKEN" http://localhost:8000/api/memories
```

## Python (httpx) Examples

### Store a memory

```python
import httpx

BASE_URL = "http://localhost:8000"

async def store_memory(content: str, tags: list[str], agent_id: str | None = None) -> dict:
    headers = {"Content-Type": "application/json"}
    if agent_id:
        headers["X-Agent-ID"] = agent_id

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/api/memories",
            json={"content": content, "tags": tags},
            headers=headers,
        )
        response.raise_for_status()
        return response.json()

# Usage
result = await store_memory(
    content="API rate limit is 100 req/min for the Acme service",
    tags=["api", "rate-limit", "acme"],
    agent_id="researcher",
)
print(result["memory"]["content_hash"])
```

### Semantic search

```python
async def search_memory(query: str, limit: int = 5, tags: list[str] | None = None) -> list[dict]:
    payload = {"query": query, "limit": limit}
    if tags:
        payload["tags"] = tags

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/api/memories/search",
            json=payload,
        )
        response.raise_for_status()
        return response.json()["memories"]

# Usage — retrieve only memories from the researcher agent
results = await search_memory(
    query="API rate limits",
    tags=["agent:researcher"],
)
for mem in results:
    print(mem["content"], mem["tags"])
```

### Store with deduplication bypass (conversation_id)

```python
async def store_incremental(content: str, conversation_id: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/api/memories",
            json={
                "content": content,
                "tags": ["conversation"],
                "conversation_id": conversation_id,
            },
        )
        response.raise_for_status()
        return response.json()
```

### List memories by tag

```python
async def list_by_tag(tag: str, page: int = 1) -> list[dict]:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/api/memories",
            params={"tags": tag, "page": page, "page_size": 20},
        )
        response.raise_for_status()
        return response.json()["memories"]
```

### Query knowledge graph

```python
async def get_associations(content_hash: str) -> list[dict]:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/api/graph/associations/{content_hash}",
        )
        response.raise_for_status()
        return response.json()["associations"]
```

## cURL Examples

```bash
# Store
curl -X POST http://localhost:8000/api/memories \
  -H "Content-Type: application/json" \
  -H "X-Agent-ID: researcher" \
  -d '{"content": "Deadline is March 15", "tags": ["project", "deadline"]}'

# Search
curl -X POST http://localhost:8000/api/memories/search \
  -H "Content-Type: application/json" \
  -d '{"query": "project deadlines", "limit": 5}'

# Search within agent scope
curl -X POST http://localhost:8000/api/memories/search \
  -H "Content-Type: application/json" \
  -d '{"query": "API limits", "tags": ["agent:researcher"]}'

# Health check
curl http://localhost:8000/api/health
```

## SSE (Server-Sent Events) — Real-time Updates

Subscribe to memory events for reactive agent coordination:

```python
import httpx

async def subscribe_to_memory_events():
    async with httpx.AsyncClient() as client:
        async with client.stream("GET", f"{BASE_URL}/sse/events") as response:
            async for line in response.aiter_lines():
                if line.startswith("data:"):
                    import json
                    event_data = json.loads(line[5:].strip())
                    event_type = event_data.get("event_type")

                    if event_type == "memory_stored":
                        print(f"New memory: {event_data['content_hash']}")
                    elif event_type == "memory_deleted":
                        print(f"Deleted: {event_data['content_hash']}")

# Run in background task
import asyncio
asyncio.create_task(subscribe_to_memory_events())
```

## X-Agent-ID Header

Any store request can include `X-Agent-ID: <identifier>` to automatically tag the memory:

```python
# These two calls produce identical results:

# Explicit tag
await store_memory(content="...", tags=["agent:researcher", "api"])

# Header auto-tagging
await store_memory(content="...", tags=["api"], agent_id="researcher")
# Server appends "agent:researcher" automatically
```
