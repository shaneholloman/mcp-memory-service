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
Logging configuration module for MCP Memory Service.

Provides client-aware logging that adjusts output behavior based on MCP client type.
Claude Desktop requires strict JSON mode (stderr only), while LM Studio supports
dual-stream output (stdout for INFO/DEBUG, stderr for WARNING+).
"""

import sys
import os
import logging
from .client_detection import MCP_CLIENT

# Custom logging handler that routes INFO/DEBUG to stdout, WARNING/ERROR to stderr
class DualStreamHandler(logging.Handler):
    """Client-aware handler that adjusts logging behavior based on MCP client."""

    def __init__(self, client_type='claude_desktop'):
        super().__init__()
        self.client_type = client_type
        self.stdout_handler = logging.StreamHandler(sys.stdout)
        self.stderr_handler = logging.StreamHandler(sys.stderr)

        # Set the same formatter for both handlers
        formatter = logging.Formatter('%(levelname)s:%(name)s:%(message)s')
        self.stdout_handler.setFormatter(formatter)
        self.stderr_handler.setFormatter(formatter)

    def emit(self, record):
        """Route log records based on client type and level."""
        # For Claude Desktop: strict JSON mode - suppress most output, route everything to stderr
        if self.client_type == 'claude_desktop':
            # Only emit WARNING and above to stderr to maintain JSON protocol
            if record.levelno >= logging.WARNING:
                self.stderr_handler.emit(record)
            # Suppress INFO/DEBUG for Claude Desktop to prevent JSON parsing errors
            return

        # For LM Studio: enhanced mode with dual-stream
        if record.levelno >= logging.WARNING:  # WARNING, ERROR, CRITICAL
            self.stderr_handler.emit(record)
        else:  # DEBUG, INFO
            self.stdout_handler.emit(record)

def configure_logging():
    """Configure root logger with client-aware handler."""
    # Configure logging with client-aware handler BEFORE any imports that use logging
    log_level = os.getenv('LOG_LEVEL', 'WARNING').upper()  # Default to WARNING for performance
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level, logging.WARNING))

    # Remove any existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Add our custom client-aware handler
    client_aware_handler = DualStreamHandler(client_type=MCP_CLIENT)
    root_logger.addHandler(client_aware_handler)

    return logging.getLogger(__name__)

# Auto-configure on import
logger = configure_logging()
