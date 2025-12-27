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

"""
Utility handler functions for MCP server.

Database health checks, cache statistics, and monitoring utilities.
Extracted from server_impl.py Phase 2.3 refactoring.
"""

import os
import json
import logging
import traceback
from typing import List

from mcp import types
from ...server.cache_manager import _CACHE_STATS, _STORAGE_CACHE, _MEMORY_SERVICE_CACHE
from ...config import STORAGE_BACKEND, SQLITE_VEC_PATH
from ..._version import __version__

logger = logging.getLogger(__name__)


async def handle_check_database_health(server, arguments: dict) -> List[types.TextContent]:
    """Handle database health check requests with performance metrics."""
    logger.info("=== EXECUTING CHECK_DATABASE_HEALTH ===")
    try:
        # Initialize storage lazily when needed
        try:
            storage = await server._ensure_storage_initialized()
        except Exception as init_error:
            # Storage initialization failed
            result = {
                "validation": {
                    "status": "unhealthy",
                    "message": f"Storage initialization failed: {str(init_error)}"
                },
                "statistics": {
                    "status": "error",
                    "error": "Cannot get statistics - storage not initialized"
                },
                "performance": {
                    "storage": {},
                    "server": {
                        "average_query_time_ms": server.get_average_query_time(),
                        "total_queries": len(server.query_times)
                    }
                }
            }

            logger.error(f"Storage initialization failed during health check: {str(init_error)}")
            return [types.TextContent(
                type="text",
                text=f"Database Health Check Results:\n{json.dumps(result, indent=2)}"
            )]

        # Skip db_utils completely for health check - implement directly here
        # Get storage type for backend-specific handling
        storage_type = storage.__class__.__name__

        # Direct health check implementation based on storage type
        is_valid = False
        message = ""
        stats = {}

        if storage_type == "SqliteVecMemoryStorage":
            # Direct SQLite-vec validation
            if not hasattr(storage, 'conn') or storage.conn is None:
                is_valid = False
                message = "SQLite database connection is not initialized"
            else:
                try:
                    # Check for required tables
                    cursor = storage.conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='memories'")
                    if not cursor.fetchone():
                        is_valid = False
                        message = "SQLite database is missing required tables"
                    else:
                        # Count memories
                        cursor = storage.conn.execute('SELECT COUNT(*) FROM memories')
                        memory_count = cursor.fetchone()[0]

                        # Check if embedding tables exist
                        cursor = storage.conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='memory_embeddings'")
                        has_embeddings = cursor.fetchone() is not None

                        # Check embedding model
                        has_model = hasattr(storage, 'embedding_model') and storage.embedding_model is not None

                        # Collect stats
                        stats = {
                            "status": "healthy",
                            "backend": "sqlite-vec",
                            "total_memories": memory_count,
                            "has_embedding_tables": has_embeddings,
                            "has_embedding_model": has_model,
                            "embedding_model": storage.embedding_model_name if hasattr(storage, 'embedding_model_name') else "none"
                        }

                        # Get database file size
                        db_path = storage.db_path if hasattr(storage, 'db_path') else None
                        if db_path and os.path.exists(db_path):
                            file_size = os.path.getsize(db_path)
                            stats["database_size_bytes"] = file_size
                            stats["database_size_mb"] = round(file_size / (1024 * 1024), 2)

                        is_valid = True
                        message = "SQLite-vec database validation successful"
                except Exception as e:
                    is_valid = False
                    message = f"SQLite database validation error: {str(e)}"
                    stats = {
                        "status": "error",
                        "error": str(e),
                        "backend": "sqlite-vec"
                    }

        elif storage_type == "CloudflareStorage":
            # Cloudflare storage validation
            try:
                # Check if storage is properly initialized
                if not hasattr(storage, 'client') or storage.client is None:
                    is_valid = False
                    message = "Cloudflare storage client is not initialized"
                    stats = {
                        "status": "error",
                        "error": "Cloudflare storage client is not initialized",
                        "backend": "cloudflare"
                    }
                else:
                    # Get storage stats
                    storage_stats = await storage.get_stats()

                    # Collect basic health info
                    stats = {
                        "status": "healthy",
                        "backend": "cloudflare",
                        "total_memories": storage_stats.get("total_memories", 0),
                        "vectorize_index": storage.vectorize_index,
                        "d1_database_id": storage.d1_database_id,
                        "r2_bucket": storage.r2_bucket,
                        "embedding_model": storage.embedding_model
                    }

                    # Add additional stats if available
                    stats.update(storage_stats)

                    is_valid = True
                    message = "Cloudflare storage validation successful"

            except Exception as e:
                is_valid = False
                message = f"Cloudflare storage validation error: {str(e)}"
                stats = {
                    "status": "error",
                    "error": str(e),
                    "backend": "cloudflare"
                }

        elif storage_type == "HybridMemoryStorage":
            # Hybrid storage validation (SQLite-vec primary + Cloudflare secondary)
            try:
                if not hasattr(storage, 'primary') or storage.primary is None:
                    is_valid = False
                    message = "Hybrid storage primary backend is not initialized"
                    stats = {
                        "status": "error",
                        "error": "Hybrid storage primary backend is not initialized",
                        "backend": "hybrid"
                    }
                else:
                    primary_storage = storage.primary
                    # Validate primary storage (SQLite-vec)
                    if not hasattr(primary_storage, 'conn') or primary_storage.conn is None:
                        is_valid = False
                        message = "Hybrid storage: SQLite connection is not initialized"
                        stats = {
                            "status": "error",
                            "error": "SQLite connection is not initialized",
                            "backend": "hybrid"
                        }
                    else:
                        # Check for required tables
                        cursor = primary_storage.conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='memories'")
                        if not cursor.fetchone():
                            is_valid = False
                            message = "Hybrid storage: SQLite database is missing required tables"
                            stats = {
                                "status": "error",
                                "error": "SQLite database is missing required tables",
                                "backend": "hybrid"
                            }
                        else:
                            # Count memories
                            cursor = primary_storage.conn.execute('SELECT COUNT(*) FROM memories')
                            memory_count = cursor.fetchone()[0]

                            # Check if embedding tables exist
                            cursor = primary_storage.conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='memory_embeddings'")
                            has_embeddings = cursor.fetchone() is not None

                            # Check secondary (Cloudflare) status
                            cloudflare_status = "not_configured"
                            if hasattr(storage, 'secondary') and storage.secondary:
                                sync_service = getattr(storage, 'sync_service', None)
                                if sync_service and getattr(sync_service, 'is_running', False):
                                    cloudflare_status = "syncing"
                                else:
                                    cloudflare_status = "configured"

                            # Collect stats
                            stats = {
                                "status": "healthy",
                                "backend": "hybrid",
                                "total_memories": memory_count,
                                "has_embeddings": has_embeddings,
                                "database_path": getattr(primary_storage, 'db_path', SQLITE_VEC_PATH),
                                "cloudflare_sync": cloudflare_status
                            }

                            is_valid = True
                            message = f"Hybrid storage validation successful ({memory_count} memories, Cloudflare: {cloudflare_status})"

            except Exception as e:
                is_valid = False
                message = f"Hybrid storage validation error: {str(e)}"
                stats = {
                    "status": "error",
                    "error": str(e),
                    "backend": "hybrid"
                }

        else:
            is_valid = False
            message = f"Unknown storage type: {storage_type}"
            stats = {
                "status": "error",
                "error": f"Unknown storage type: {storage_type}",
                "backend": "unknown"
            }

        # Get performance stats from optimized storage
        performance_stats = {}
        if hasattr(storage, 'get_performance_stats') and callable(storage.get_performance_stats):
            try:
                performance_stats = storage.get_performance_stats()
            except Exception as perf_error:
                logger.warning(f"Could not get performance stats: {str(perf_error)}")
                performance_stats = {"error": str(perf_error)}

        # Get server-level performance stats
        server_stats = {
            "average_query_time_ms": server.get_average_query_time(),
            "total_queries": len(server.query_times)
        }

        # Add storage type for debugging
        server_stats["storage_type"] = storage_type

        # Add storage initialization status for debugging
        if hasattr(storage, 'get_initialization_status') and callable(storage.get_initialization_status):
            try:
                server_stats["storage_initialization"] = storage.get_initialization_status()
            except Exception:
                pass

        # Combine results with performance data
        result = {
            "version": __version__,
            "validation": {
                "status": "healthy" if is_valid else "unhealthy",
                "message": message
            },
            "statistics": stats,
            "performance": {
                "storage": performance_stats,
                "server": server_stats
            }
        }

        logger.info(f"Database health result with performance data: {result}")
        return [types.TextContent(
            type="text",
            text=f"Database Health Check Results:\n{json.dumps(result, indent=2)}"
        )]
    except Exception as e:
        logger.error(f"Error in check_database_health: {str(e)}")
        logger.error(traceback.format_exc())
        return [types.TextContent(
            type="text",
            text=f"Error checking database health: {str(e)}"
        )]


async def handle_get_cache_stats(server, arguments: dict) -> List[types.TextContent]:
    """
    Get MCP server global cache statistics for performance monitoring.

    Returns detailed metrics about storage and memory service caching,
    including hit rates, initialization times, and cache sizes.
    """
    global _CACHE_STATS, _STORAGE_CACHE, _MEMORY_SERVICE_CACHE

    try:
        # Import shared stats calculation utility
        from ...utils.cache_manager import CacheStats, calculate_cache_stats_dict

        # Convert global dict to CacheStats dataclass
        stats = CacheStats(
            total_calls=_CACHE_STATS["total_calls"],
            storage_hits=_CACHE_STATS["storage_hits"],
            storage_misses=_CACHE_STATS["storage_misses"],
            service_hits=_CACHE_STATS["service_hits"],
            service_misses=_CACHE_STATS["service_misses"],
            initialization_times=_CACHE_STATS["initialization_times"]
        )

        # Calculate statistics using shared utility
        cache_sizes = (len(_STORAGE_CACHE), len(_MEMORY_SERVICE_CACHE))
        result = calculate_cache_stats_dict(stats, cache_sizes)

        # Add server-specific details
        result["storage_cache"]["keys"] = list(_STORAGE_CACHE.keys())
        result["backend_info"] = {
            "storage_backend": STORAGE_BACKEND,
            "sqlite_path": SQLITE_VEC_PATH
        }

        logger.info(f"Cache stats retrieved: {result['message']}")

        # Return JSON string for easy parsing by clients
        return [types.TextContent(
            type="text",
            text=json.dumps(result, indent=2)
        )]

    except Exception as e:
        logger.error(f"Error in get_cache_stats: {str(e)}")
        logger.error(traceback.format_exc())
        return [types.TextContent(
            type="text",
            text=f"Error getting cache stats: {str(e)}"
        )]
