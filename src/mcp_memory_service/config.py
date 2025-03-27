"""
MCP Memory Service
Copyright (c) 2024 Heinrich Krupp
Licensed under the MIT License. See LICENSE file in the project root for full license text.
"""
import os
import sys
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

def validate_and_create_path(path: str) -> str:
    """Validate and create a directory path, ensuring it's writable."""
    try:
        # Convert to absolute path
        abs_path = os.path.abspath(path)
        
        # Create directory if it doesn't exist
        os.makedirs(abs_path, exist_ok=True)

        # Add small delay to prevent potential race condition on macOS during initial write test
        time.sleep(0.1)
        
        # Check if directory is writable
        test_file = os.path.join(abs_path, '.write_test')
        try:
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
        except Exception as e:
            raise PermissionError(f"Directory {abs_path} is not writable: {str(e)}")
        logger.info(f"Directory {abs_path} is writable.")
        return abs_path
    except Exception as e:
        logger.error(f"Error validating path {path}: {str(e)}")
        raise

# Determine base directory - prefer local over Cloud
def get_base_directory() -> str:
    """Get base directory for storage, with fallback options."""
    # First choice: Environment variable
    if base_dir := os.getenv('MCP_MEMORY_BASE_DIR'):
        return validate_and_create_path(base_dir)
    
    # Second choice: Local app data directory
    home = str(Path.home())
    if sys.platform == 'darwin':  # macOS
        base = os.path.join(home, 'Library', 'Application Support', 'mcp-memory')
    elif sys.platform == 'win32':  # Windows
        base = os.path.join(os.getenv('LOCALAPPDATA', ''), 'mcp-memory')
    else:  # Linux and others
        base = os.path.join(home, '.local', 'share', 'mcp-memory')
    
    return validate_and_create_path(base)

# Initialize paths
try:
    BASE_DIR = get_base_directory()
    
    # Try multiple environment variable names for ChromaDB path
    chroma_path = None
    for env_var in ['MCP_MEMORY_CHROMA_PATH', 'mcpMemoryChromaPath']:
        if path := os.getenv(env_var):
            chroma_path = path
            logger.info(f"Using {env_var}={path} for ChromaDB path")
            break
    
    # If no environment variable is set, use the default path
    if not chroma_path:
        chroma_path = os.path.join(BASE_DIR, 'chroma_db')
        logger.info(f"No ChromaDB path environment variable found, using default: {chroma_path}")

    # Try multiple environment variable names for backups path
    backups_path = None
    for env_var in ['MCP_MEMORY_BACKUPS_PATH', 'mcpMemoryBackupsPath']:
        if path := os.getenv(env_var):
            backups_path = path
            logger.info(f"Using {env_var}={path} for backups path")
            break
    
    # If no environment variable is set, use the default path
    if not backups_path:
        backups_path = os.path.join(BASE_DIR, 'backups')
        logger.info(f"No backups path environment variable found, using default: {backups_path}")
    
    CHROMA_PATH = validate_and_create_path(chroma_path)
    BACKUPS_PATH = validate_and_create_path(backups_path)

    # Print the final paths used
    logger.info(f"Using ChromaDB path: {CHROMA_PATH}")
    logger.info(f"Using backups path: {BACKUPS_PATH}")

except Exception as e:
    logger.error(f"Fatal error initializing paths: {str(e)}")
    sys.exit(1)

# Server settings
SERVER_NAME = "memory"
SERVER_VERSION = "0.2.0"

# ChromaDB settings
CHROMA_SETTINGS = {
    "anonymized_telemetry": False,
    "allow_reset": True,
    "is_persistent": True,
    "chroma_db_impl": "duckdb+parquet"
}

# Collection settings
COLLECTION_METADATA = {
    "hnsw:space": "cosine",
    "hnsw:construction_ef": 100,  # Increased for better accuracy
    "hnsw:search_ef": 100        # Increased for better search results
}
