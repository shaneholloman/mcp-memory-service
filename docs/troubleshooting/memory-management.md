# Memory Management Guide

This guide explains memory usage in mcp-memory-service and provides solutions for memory-related issues.

## Overview

The MCP Memory Service uses several memory-intensive components:

| Component | Typical Size | Notes |
|-----------|--------------|-------|
| ONNX Embedding Model | 70-100 MB | all-MiniLM-L6-v2 |
| Quality Ranker Model | 100-150 MB | nvidia-quality-classifier-deberta |
| PyTorch (if loaded) | 500 MB - 2 GB | Only when sentence-transformers used |
| Storage Instances | 10-50 MB | SQLite/Cloudflare connections |
| MemoryService Cache | 5-20 MB | Per-backend instances |
| Consolidation Buffers | Variable | Active during consolidation |

**Total per process: 685 MB - 2.3 GB** depending on configuration.

## Common Issues

### Multiple Orphaned Processes (Discussion #331)

**Symptom:** Multiple MCP processes running, each consuming ~1 GB RAM.

**Cause:** Claude Code may not properly terminate MCP server processes when sessions end.

**Solutions:**

1. **Kill orphaned processes manually:**
   ```bash
   # Find memory service processes
   ps aux | grep -E "memory.*server|mcp-memory" | grep -v grep

   # Kill all orphaned processes
   pkill -f "mcp-memory-service"

   # Or more targeted (find PIDs first, then kill)
   ps aux | grep -E "memory.*server" | grep -v grep | awk '{print $2}' | xargs kill
   ```

2. **Add resource limits (Linux systemd):**
   ```bash
   systemctl --user edit mcp-memory-http.service
   ```
   Add:
   ```ini
   [Service]
   MemoryMax=2G
   ```

3. **Reduce memory footprint:**
   ```bash
   # Disable quality system (saves 150MB+)
   export MCP_QUALITY_SYSTEM_ENABLED=false

   # Use hash-based embeddings (minimal memory, lower quality)
   export MCP_EMBEDDING_FALLBACK=hash
   ```

### High Memory Usage

**Symptom:** Single process using more memory than expected.

**Solutions:**

1. **Check current memory usage:**
   ```bash
   curl http://127.0.0.1:8000/api/memory-stats
   ```

2. **Clear caches to free memory:**
   ```bash
   curl -X POST http://127.0.0.1:8000/api/clear-caches
   ```

3. **Monitor cache statistics:**
   ```bash
   curl http://127.0.0.1:8000/api/health/detailed | jq '.storage'
   ```

## API Endpoints

### GET /api/memory-stats

Returns detailed memory usage statistics:

```json
{
  "process_memory_mb": 512.5,
  "process_memory_virtual_mb": 1024.3,
  "system_memory_total_gb": 16.0,
  "system_memory_available_gb": 8.5,
  "system_memory_percent": 47.0,
  "cached_storage_count": 1,
  "cached_service_count": 1,
  "model_cache_count": 1,
  "embedding_cache_count": 50,
  "cache_stats": {
    "storage": {"hits": 100, "misses": 1, "hit_rate_percent": 99.0},
    "service": {"hits": 100, "misses": 1, "hit_rate_percent": 99.0}
  }
}
```

### POST /api/clear-caches

Clears all caches to free memory:

```json
{
  "success": true,
  "storage_instances_cleared": 1,
  "service_instances_cleared": 1,
  "models_cleared": 1,
  "embeddings_cleared": 50,
  "gc_collected": 150,
  "memory_freed_estimate_mb": 200.5
}
```

**Warning:** After clearing caches, the next request will be slower (cold start).

## Configuration Options

### Reduce Memory Usage

```bash
# Disable quality system (saves 150MB+)
export MCP_QUALITY_SYSTEM_ENABLED=false

# Disable consolidation (saves memory during idle)
export MCP_CONSOLIDATION_ENABLED=false

# Use smaller embedding model (if available)
export MCP_EMBEDDING_MODEL=all-MiniLM-L6-v2
```

### Enable Memory Monitoring

```bash
# Enable debug logging for memory operations
export MCP_LOG_LEVEL=DEBUG
```

## Graceful Shutdown

The service now properly cleans up resources on shutdown (v8.70.0+):

- **SIGTERM:** Clears all caches, runs garbage collection
- **SIGINT (Ctrl+C):** Same cleanup as SIGTERM
- **Normal exit:** atexit handler runs cleanup

### Shutdown Cleanup Includes:

1. Storage backend cache clearing
2. MemoryService cache clearing
3. Embedding model cache clearing
4. Computed embeddings cache clearing
5. Forced garbage collection

## Monitoring Script

Create a monitoring script to watch for orphaned processes:

```bash
#!/bin/bash
# monitor_memory.sh

MAX_PROCESSES=2
MAX_MEMORY_MB=2000

while true; do
    # Count MCP memory processes
    process_count=$(ps aux | grep -E "memory.*server|mcp-memory" | grep -v grep | wc -l)

    # Get total memory usage
    total_memory=$(ps aux | grep -E "memory.*server|mcp-memory" | grep -v grep | awk '{sum+=$6} END {print sum/1024}')

    echo "$(date): Processes=$process_count, Memory=${total_memory}MB"

    if [ "$process_count" -gt "$MAX_PROCESSES" ]; then
        echo "WARNING: Too many processes ($process_count > $MAX_PROCESSES)"
        # Optionally kill oldest processes
        # ps aux | grep -E "memory.*server" | grep -v grep | sort -k9 | head -n $((process_count - MAX_PROCESSES)) | awk '{print $2}' | xargs kill
    fi

    sleep 60
done
```

## Reporting Issues

If you experience memory issues:

1. **Collect diagnostics:**
   ```bash
   curl http://127.0.0.1:8000/api/memory-stats > memory_stats.json
   curl http://127.0.0.1:8000/api/health/detailed > health.json
   ps aux | grep memory > processes.txt
   ```

2. **Report to mcp-memory-service:**
   - Open an issue at: https://github.com/doobidoo/mcp-memory-service/issues

3. **Report to Claude Code (if processes not terminating):**
   - Open an issue at: https://github.com/anthropics/claude-code/issues

## Related Documentation

- [Troubleshooting Guide](../troubleshooting/)
- [Configuration Reference](../configuration/)
- [Memory Consolidation Guide](../guides/memory-consolidation-guide.md)
