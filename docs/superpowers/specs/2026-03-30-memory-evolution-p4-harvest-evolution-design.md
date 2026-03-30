# Memory Evolution P4: Harvest Evolution — Evolve Instead of Duplicate

**Status:** Approved
**Date:** 2026-03-30
**Depends on:** P1 (versioned updates), P2 (staleness scoring), P3 (conflict detection)

---

## Problem

Session harvest (`harvester.py:59`) always calls `store_memory()` for every extracted insight. Over time this creates near-duplicate memories as the same knowledge is re-harvested across sessions with minor variations. The P1 `update_memory_versioned()` infrastructure exists but harvest doesn't use it.

## Solution

Before storing a harvested memory, check if a semantically similar active memory already exists. If so, evolve it (versioned update) instead of creating a duplicate.

## Detection

At `harvester.py:59`, before `store_memory()`:

1. **Semantic search** against existing active memories (cosine similarity threshold)
2. **Hit (similarity > 0.85)**: Call `update_memory_versioned(existing_hash, new_content, reason="Session harvest: {date}")` — new version inherits tags, old version stays in lineage
3. **Miss**: Normal `store_memory()` as today

## Hook Point

```
File: src/mcp_memory_service/harvest/harvester.py
Line: 59 (harvest_and_store method)

Current:
    resp = await self.memory_service.store_memory(content=..., tags=..., ...)

New:
    # Check for similar existing memory
    similar = await self.memory_service.storage.retrieve(
        candidate.content, n_results=1, min_confidence=min_confidence_to_evolve
    )
    if similar and similar[0].relevance_score > similarity_threshold:
        existing_hash = similar[0].memory.content_hash
        ok, msg, new_hash = await self.memory_service.storage.update_memory_versioned(
            existing_hash, candidate.content,
            reason=f"Session harvest: {datetime.now().isoformat()}"
        )
    else:
        resp = await self.memory_service.store_memory(...)
```

## Configuration

Add to harvest config (environment variables):

```bash
# Similarity threshold for evolving vs creating (0.0-1.0, default: 0.85)
MCP_HARVEST_SIMILARITY_THRESHOLD=0.85

# Minimum effective confidence to consider for evolution (default: 0.3)
# Prevents evolving very stale memories — better to create fresh
MCP_HARVEST_MIN_CONFIDENCE_TO_EVOLVE=0.3
```

## CLI Commands (Bonus)

Thin wrappers over existing P1/P3 APIs — not in critical path:

```bash
memory history <hash>      # → get_memory_history() from P1
memory conflicts           # → get_conflicts() from P3
memory resolve <w> <l>     # → resolve_conflict() from P3
```

## Testing

- Harvest with similar existing memory → versioned update (not new row)
- Harvest with novel content → normal store
- Harvest with stale memory below min_confidence → normal store (don't evolve)
- Harvest with superseded memory → normal store (don't evolve dead versions)
- Config thresholds respected

## Not In Scope

- Auto-merge of harvested content (keep it simple: replace, not merge)
- LLM-based quality comparison between old and new version
- Dashboard UI for harvest lineage visualization
