"""
Cache management module for MCP Memory Service.

Copyright (c) 2024 mcp-memory-service
Licensed under the MIT License. See LICENSE file in the project root.

GLOBAL CACHING FOR MCP SERVER PERFORMANCE OPTIMIZATION
========================================================
Module-level caches to persist storage/service instances across stateless HTTP calls.
This reduces initialization overhead from ~1,810ms to <400ms on cache hits.

Cache Keys:
- Storage: "{backend_type}:{db_path}" (e.g., "sqlite_vec:/path/to/db")
- MemoryService: storage instance ID (id(storage))

Thread Safety:
- Uses asyncio.Lock to prevent race conditions during concurrent access

Lifecycle:
- Cached instances persist for the lifetime of the Python process
- NOT cleared between stateless HTTP calls (intentional for performance)
- Cleaned up on process shutdown via lifespan context manager
"""

import asyncio
import time
from typing import Dict, Any, Optional

from .logging_config import logger


# =============================================================================
# GLOBAL CACHE STORAGE
# =============================================================================

_STORAGE_CACHE: Dict[str, Any] = {}  # Storage instances keyed by "{backend}:{path}"
_MEMORY_SERVICE_CACHE: Dict[int, Any] = {}  # MemoryService instances keyed by storage ID
_CACHE_LOCK: Optional[asyncio.Lock] = None  # Initialized on first use to avoid event loop issues
_CACHE_STATS = {
    "storage_hits": 0,
    "storage_misses": 0,
    "service_hits": 0,
    "service_misses": 0,
    "total_calls": 0,
    "initialization_times": []  # Track initialization durations for cache misses
}


# =============================================================================
# CACHE FUNCTIONS
# =============================================================================

def _get_cache_lock() -> asyncio.Lock:
    """Get or create the global cache lock (lazy initialization to avoid event loop issues)."""
    global _CACHE_LOCK
    if _CACHE_LOCK is None:
        _CACHE_LOCK = asyncio.Lock()
    return _CACHE_LOCK


def _get_or_create_memory_service(storage: Any) -> Any:
    """
    Get cached MemoryService or create new one.

    Args:
        storage: Storage instance to use as cache key

    Returns:
        MemoryService instance (cached or newly created)
    """
    from ..services.memory_service import MemoryService

    storage_id = id(storage)
    if storage_id in _MEMORY_SERVICE_CACHE:
        memory_service = _MEMORY_SERVICE_CACHE[storage_id]
        _CACHE_STATS["service_hits"] += 1
        logger.info(f"✅ MemoryService Cache HIT - Reusing service instance (storage_id: {storage_id})")
    else:
        _CACHE_STATS["service_misses"] += 1
        logger.info(f"❌ MemoryService Cache MISS - Creating new service instance...")

        # Initialize memory service with shared business logic
        memory_service = MemoryService(storage)

        # Cache the memory service instance
        _MEMORY_SERVICE_CACHE[storage_id] = memory_service
        logger.info(f"💾 Cached MemoryService instance (storage_id: {storage_id})")

    return memory_service


def _log_cache_performance(start_time: float) -> None:
    """
    Log comprehensive cache performance statistics.

    Args:
        start_time: Timer start time to calculate total elapsed time
    """
    total_time = (time.time() - start_time) * 1000
    cache_hit_rate = (
        (_CACHE_STATS["storage_hits"] + _CACHE_STATS["service_hits"]) /
        (_CACHE_STATS["total_calls"] * 2)  # 2 caches per call
    ) * 100

    logger.info(
        f"📊 Cache Stats - "
        f"Hit Rate: {cache_hit_rate:.1f}% | "
        f"Storage: {_CACHE_STATS['storage_hits']}H/{_CACHE_STATS['storage_misses']}M | "
        f"Service: {_CACHE_STATS['service_hits']}H/{_CACHE_STATS['service_misses']}M | "
        f"Total Time: {total_time:.1f}ms"
    )
