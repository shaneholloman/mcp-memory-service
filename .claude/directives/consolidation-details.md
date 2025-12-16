# Memory Consolidation System - Detailed Reference

**Quick Summary for CLAUDE.md**: See main file for architecture overview. This file contains performance expectations, configuration details, and operational procedures.

## Performance Expectations (Real-World)

Based on v8.23.1 test with 2,495 memories:

| Backend | First Run | Subsequent Runs | Notes |
|---------|-----------|----------------|-------|
| **SQLite-Vec** | 5-25s | 5-25s | Fast, local-only |
| **Cloudflare** | 2-4min | 1-3min | Network-dependent, cloud-only |
| **Hybrid** | 4-6min | 2-4min | Slower but provides multi-device sync |

**Why Hybrid takes longer**: Local SQLite operations (~5ms) + Cloudflare cloud sync (~150ms per update). Trade-off: Processing time for data persistence across devices.

**Recommendation**: Hybrid backend is recommended for production despite longer consolidation time.

## Complete Configuration

```bash
# Enable consolidation (default: true)
MCP_CONSOLIDATION_ENABLED=true

# Association-based quality boost (v8.47.0+)
MCP_CONSOLIDATION_QUALITY_BOOST_ENABLED=true   # Enable boost (default: true)
MCP_CONSOLIDATION_MIN_CONNECTIONS_FOR_BOOST=5  # Min connections (default: 5)
MCP_CONSOLIDATION_QUALITY_BOOST_FACTOR=1.2     # Boost multiplier (default: 1.2 = 20%)

# Scheduler configuration (in config.py)
CONSOLIDATION_SCHEDULE = {
    'daily': '02:00',              # Daily at 2 AM
    'weekly': 'SUN 03:00',         # Weekly on Sunday at 3 AM
    'monthly': '01 04:00',         # Monthly on 1st at 4 AM
    'quarterly': 'disabled',       # Disabled
    'yearly': 'disabled'           # Disabled
}
```

## HTTP API Endpoints

| Endpoint | Method | Description | Response Time |
|----------|--------|-------------|---------------|
| `/api/consolidation/trigger` | POST | Trigger consolidation | ~10-30s |
| `/api/consolidation/status` | GET | Scheduler status | <5ms |
| `/api/consolidation/recommendations/{horizon}` | GET | Get recommendations | ~50ms |

**Example:**
```bash
# Trigger weekly consolidation
curl -X POST http://127.0.0.1:8000/api/consolidation/trigger \
  -H "Content-Type: application/json" \
  -d '{"time_horizon": "weekly"}'

# Check status
curl http://127.0.0.1:8000/api/consolidation/status
```

## Code Execution API (Token Efficiency)

```python
from mcp_memory_service.api import consolidate, scheduler_status

# Trigger consolidation (15 tokens vs 150 MCP tool - 90% reduction)
result = consolidate('weekly')

# Check scheduler (10 tokens vs 125 - 92% reduction)
status = scheduler_status()
```

## Features

- **Exponential decay scoring** - Prioritize recent, frequently accessed memories
- **Association-based quality boost** 🆕 - Well-connected memories (≥5 connections) get 20% quality boost
- **Creative association discovery** - Find semantic connections (0.3-0.7 similarity)
- **Semantic clustering** - Group related memories (DBSCAN algorithm)
- **Compression** - Summarize redundant information (preserves originals)
- **Controlled forgetting** - Archive low-relevance memories (90+ days inactive)

## Migration from MCP-only Mode (v8.22.x → v8.23.0+)

**No action required** - Consolidation automatically runs in HTTP server if enabled.

For users without HTTP server:
```bash
# Enable HTTP server in .env
export MCP_HTTP_ENABLED=true

# Restart service
systemctl --user restart mcp-memory-http.service
```

## Operational Guide

See [docs/guides/memory-consolidation-guide.md](../../docs/guides/memory-consolidation-guide.md) for:
- Detailed operational procedures
- Monitoring and metrics
- Troubleshooting
- Best practices

Wiki version: [Memory Consolidation System Guide](https://github.com/doobidoo/mcp-memory-service/wiki/Memory-Consolidation-System-Guide)
