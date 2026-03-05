"""HTTP Server Manager for MCP Memory Service multi-client coordination."""

import asyncio
import logging
import os
import subprocess
import sys

logger = logging.getLogger(__name__)


async def auto_start_http_server_if_needed() -> bool:
    """
    Auto-start HTTP server if needed for multi-client coordination.

    The HTTP server is started when either of the following env vars is set to
    ``true`` or ``1``:

    * ``MCP_HTTP_ENABLED``            – the documented, commonly used variable
    * ``MCP_MEMORY_HTTP_AUTO_START``  – legacy alias kept for back-compat

    Returns:
        bool: True if server was started or already running, False if failed
    """
    try:
        # Check if HTTP auto-start is enabled (accept either env var)
        http_enabled = os.getenv("MCP_HTTP_ENABLED", "").lower() in ("true", "1")
        auto_start = os.getenv("MCP_MEMORY_HTTP_AUTO_START", "").lower() in ("true", "1")
        if not (http_enabled or auto_start):
            logger.debug("HTTP auto-start not enabled (set MCP_HTTP_ENABLED=true to enable)")
            return False

        # Check if server is already running
        from ..utils.port_detection import is_port_in_use
        port = int(os.getenv("MCP_HTTP_PORT", "8000"))
        host = os.getenv("MCP_HTTP_HOST", "localhost")

        if await is_port_in_use(host, port):
            logger.info(f"HTTP server already running on port {port}")
            return True

        # Build subprocess command using the installed package entrypoint.
        # Using the module name without the "src." prefix so this works for
        # both pip-installed packages and uvx invocations.
        cmd = [
            sys.executable, "-m", "mcp_memory_service.web.app",
            "--port", str(port),
            "--host", host,
        ]

        # Forward auth and connection env vars to the subprocess so that
        # sessions started by hooks (which send Bearer tokens) can authenticate.
        passthrough_vars = [
            "MCP_API_KEY",
            "MCP_ALLOW_ANONYMOUS_ACCESS",
            "MCP_HTTP_PORT",
            "MCP_HTTP_HOST",
            "MCP_HTTP_ENABLED",
            "MEMORY_STORAGE_BACKEND",
            "CHROMA_DB_PATH",
            "SQLITE_DB_PATH",
        ]
        env = os.environ.copy()
        for var in passthrough_vars:
            value = os.getenv(var)
            if value is not None:
                env[var] = value

        logger.info(f"Starting HTTP server on port {port}")
        process = subprocess.Popen(
            cmd,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )

        # Poll until the port becomes active or we time-out.
        # The embedding model (sentence-transformers) takes ~7-8 seconds to load
        # on first use, so we allow up to 30 seconds total.
        max_wait_seconds = 30
        poll_interval = 2
        elapsed = 0

        while elapsed < max_wait_seconds:
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

            if process.poll() is not None:
                # Process exited unexpectedly
                logger.warning(
                    f"HTTP server process exited with code {process.returncode} "
                    f"after {elapsed}s"
                )
                return False

            if await is_port_in_use(host, port):
                logger.info(
                    f"HTTP server ready on port {port} (after {elapsed}s)"
                )
                return True

        # Timed out waiting for the server to become ready
        logger.warning(
            f"HTTP server process started but port {port} not in use after "
            f"{max_wait_seconds}s – server may still be loading"
        )
        # Return True because the process is still running; it may become
        # ready shortly after the caller's first request.
        return process.poll() is None

    except Exception as e:
        logger.error(f"Failed to auto-start HTTP server: {e}")
        return False