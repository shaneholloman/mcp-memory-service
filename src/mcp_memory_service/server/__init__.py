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
Server package for MCP Memory Service.

Modular server components for better maintainability:
- client_detection: MCP client detection (Claude Desktop, LM Studio, etc.)
- logging_config: Client-aware logging configuration
- environment: Python path setup, version checks, performance config
- cache_manager: Global caching for storage and service instances
"""

# Client Detection
from .client_detection import MCP_CLIENT, detect_mcp_client

# Logging Configuration
from .logging_config import DualStreamHandler, configure_logging, logger

# Environment Configuration
from .environment import (
    setup_python_paths,
    check_uv_environment,
    check_version_consistency,
    configure_environment,
    configure_performance_environment
)

# Cache Management
from .cache_manager import (
    _STORAGE_CACHE,
    _MEMORY_SERVICE_CACHE,
    _CACHE_LOCK,
    _CACHE_STATS,
    _get_cache_lock,
    _get_or_create_memory_service,
    _log_cache_performance
)

# Backward compatibility: Import main functions from server_impl.py
# server_impl.py (formerly server.py) contains main() and async_main()
# We re-export them for backward compatibility: from mcp_memory_service.server import main
from ..server_impl import main, async_main, MemoryServer

__all__ = [
    # Client Detection
    'MCP_CLIENT',
    'detect_mcp_client',

    # Logging
    'DualStreamHandler',
    'configure_logging',
    'logger',

    # Environment
    'setup_python_paths',
    'check_uv_environment',
    'check_version_consistency',
    'configure_environment',
    'configure_performance_environment',

    # Cache
    '_STORAGE_CACHE',
    '_MEMORY_SERVICE_CACHE',
    '_CACHE_LOCK',
    '_CACHE_STATS',
    '_get_cache_lock',
    '_get_or_create_memory_service',
    '_log_cache_performance',

    # Entry points and core classes (for backward compatibility)
    'main',
    'async_main',
    'MemoryServer',
]
