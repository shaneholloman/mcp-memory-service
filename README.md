# MCP Memory Service

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![smithery badge](https://smithery.ai/badge/@doobidoo/mcp-memory-service)](https://smithery.ai/server/@doobidoo/mcp-memory-service)

An MCP server providing semantic memory and persistent storage capabilities for Claude Desktop using ChromaDB and sentence transformers. This service enables long-term memory storage with semantic search capabilities, making it ideal for maintaining context across conversations and instances.

<img width="240" alt="grafik" src="https://github.com/user-attachments/assets/eab1f341-ca54-445c-905e-273cd9e89555" />
<a href="https://glama.ai/mcp/servers/bzvl3lz34o"><img width="380" height="200" src="https://glama.ai/mcp/servers/bzvl3lz34o/badge" alt="Memory Service MCP server" /></a>

## Features

- Semantic search using sentence transformers
- **Natural language time-based recall** (e.g., "last week", "yesterday morning")
- Tag-based memory retrieval system
- Persistent storage using ChromaDB
- Automatic database backups
- Memory optimization tools
- Exact match retrieval
- Debug mode for similarity analysis
- Database health monitoring
- Duplicate detection and cleanup
- Customizable embedding model
- **Cross-platform compatibility** (Apple Silicon, Intel, Windows, Linux)
- **Hardware-aware optimizations** for different environments
- **Graceful fallbacks** for limited hardware resources

## Installation

### Quick Start (Recommended)

The enhanced installation script automatically detects your system and installs the appropriate dependencies:

```bash
# Clone the repository
git clone https://github.com/doobidoo/mcp-memory-service.git
cd mcp-memory-service

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Run the installation script
python install.py
```

The `install.py` script will:
1. Detect your system architecture and available hardware accelerators
2. Install the appropriate dependencies for your platform
3. Configure the optimal settings for your environment
4. Verify the installation and provide diagnostics if needed

### Windows Installation (Special Case)

Windows users may encounter PyTorch installation issues due to platform-specific wheel availability. Use our Windows-specific installation script:

```bash
# After activating your virtual environment
python scripts/install_windows.py
```

This script handles:
1. Detecting CUDA availability and version
2. Installing the appropriate PyTorch version from the correct index URL
3. Installing other dependencies without conflicting with PyTorch
4. Verifying the installation

### Installing via Smithery

To install Memory Service for Claude Desktop automatically via [Smithery](https://smithery.ai/server/@doobidoo/mcp-memory-service):
~~~bash
npx -y @smithery/cli install @doobidoo/mcp-memory-service --client claude
~~~
**Note:** The Smithery installation method currently does not work as intended. Please use the other installation methods until this issue is resolved.

### Detailed Installation Guide

For comprehensive installation instructions and troubleshooting, see the [Installation Guide](docs/guides/installation.md).

## Claude MCP Configuration

### Standard Configuration

Add the following to your `claude_desktop_config.json` file:

```json
{
  "memory": {
    "command": "uv",
    "args": [
      "--directory",
      "your_mcp_memory_service_directory",  // e.g., "C:\\REPOSITORIES\\mcp-memory-service"
      "run",
      "memory"
    ],
    "env": {
      "MCP_MEMORY_CHROMA_PATH": "your_chroma_db_path",  // e.g., "C:\\Users\\John.Doe\\AppData\\Local\\mcp-memory\\chroma_db"
      "MCP_MEMORY_BACKUPS_PATH": "your_backups_path"  // e.g., "C:\\Users\\John.Doe\\AppData\\Local\\mcp-memory\\backups"
    }
  }
}
```

### Windows-Specific Configuration (Recommended)

For Windows users, we recommend using the wrapper script to ensure PyTorch is properly installed:

```json
{
  "memory": {
    "command": "python",
    "args": [
      "C:\\path\\to\\mcp-memory-service\\memory_wrapper.py"
    ],
    "env": {
      "MCP_MEMORY_CHROMA_PATH": "C:\\Users\\YourUsername\\AppData\\Local\\mcp-memory\\chroma_db",
      "MCP_MEMORY_BACKUPS_PATH": "C:\\Users\\YourUsername\\AppData\\Local\\mcp-memory\\backups"
    }
  }
}
```

The wrapper script will:
1. Check if PyTorch is installed and properly configured
2. Install PyTorch with the correct index URL if needed
3. Run the memory server with the appropriate configuration

## Usage

To run the memory server directly (for testing):

```bash
# Quick run script (recommended for testing)
python scripts/run_memory_server.py

# For isolated testing of methods
python src/chroma_test_isolated.py
```

## Memory Operations

The memory service provides the following operations through the MCP server:

### Core Memory Operations

1. `store_memory` - Store new information with optional tags
2. `retrieve_memory` - Perform semantic search for relevant memories
3. `recall_memory` - Retrieve memories using natural language time expressions 
4. `search_by_tag` - Find memories using specific tags
5. `exact_match_retrieve` - Find memories with exact content match
6. `debug_retrieve` - Retrieve memories with similarity scores

### Database Management

7. `create_backup` - Create database backup
8. `get_stats` - Get memory statistics
9. `optimize_db` - Optimize database performance
10. `check_database_health` - Get database health metrics
11. `check_embedding_model` - Verify model status

### Memory Management

12. `delete_memory` - Delete specific memory by hash
13. `delete_by_tag` - Delete all memories with specific tag
14. `cleanup_duplicates` - Remove duplicate entries

## Configuration Options

Configure through environment variables:

```
CHROMA_DB_PATH: Path to ChromaDB storage
BACKUP_PATH: Path for backups
AUTO_BACKUP_INTERVAL: Backup interval in hours (default: 24)
MAX_MEMORIES_BEFORE_OPTIMIZE: Threshold for auto-optimization (default: 10000)
SIMILARITY_THRESHOLD: Default similarity threshold (default: 0.7)
MAX_RESULTS_PER_QUERY: Maximum results per query (default: 10)
BACKUP_RETENTION_DAYS: Number of days to keep backups (default: 7)
LOG_LEVEL: Logging level (default: INFO)

# Hardware-specific environment variables
PYTORCH_ENABLE_MPS_FALLBACK: Enable MPS fallback for Apple Silicon (default: 1)
MCP_MEMORY_USE_ONNX: Use ONNX Runtime for CPU-only deployments (default: 0)
MCP_MEMORY_USE_DIRECTML: Use DirectML for Windows acceleration (default: 0)
MCP_MEMORY_MODEL_NAME: Override the default embedding model
MCP_MEMORY_BATCH_SIZE: Override the default batch size
```

## Hardware Compatibility

| Platform | Architecture | Accelerator | Status |
|----------|--------------|-------------|--------|
| macOS | Apple Silicon (M1/M2/M3) | MPS | ✅ Fully supported |
| macOS | Apple Silicon under Rosetta 2 | CPU | ✅ Supported with fallbacks |
| macOS | Intel | CPU | ✅ Fully supported |
| Windows | x86_64 | CUDA | ✅ Fully supported |
| Windows | x86_64 | DirectML | ✅ Supported |
| Windows | x86_64 | CPU | ✅ Supported with fallbacks |
| Linux | x86_64 | CUDA | ✅ Fully supported |
| Linux | x86_64 | ROCm | ✅ Supported |
| Linux | x86_64 | CPU | ✅ Supported with fallbacks |
| Linux | ARM64 | CPU | ✅ Supported with fallbacks |

## Testing

```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run all tests
pytest tests/

# Run specific test categories
pytest tests/test_memory_ops.py
pytest tests/test_semantic_search.py
pytest tests/test_database.py

# Verify environment compatibility
python scripts/verify_environment_enhanced.py

# Verify PyTorch installation on Windows
python scripts/verify_pytorch_windows.py

# Perform comprehensive installation verification
python scripts/test_installation.py
```

## Troubleshooting

See the [Installation Guide](docs/guides/installation.md#troubleshooting-common-installation-issues) for detailed troubleshooting steps.

### Quick Troubleshooting Tips

- **Windows PyTorch errors**: Use `python scripts/install_windows.py`
- **macOS Intel dependency conflicts**: Use `python install.py --force-compatible-deps`
- **Recursion errors**: Run `python scripts/fix_sitecustomize.py` 
- **Environment verification**: Run `python scripts/verify_environment_enhanced.py`
- **Memory issues**: Set `MCP_MEMORY_BATCH_SIZE=4` and try a smaller model
- **Apple Silicon**: Ensure Python 3.10+ built for ARM64, set `PYTORCH_ENABLE_MPS_FALLBACK=1`
- **Installation testing**: Run `python scripts/test_installation.py`

## Project Structure

```
mcp-memory-service/
├── src/mcp_memory_service/      # Core package code
│   ├── __init__.py
│   ├── config.py                # Configuration utilities
│   ├── models/                  # Data models
│   ├── storage/                 # Storage implementations
│   ├── utils/                   # Utility functions
│   └── server.py                # Main MCP server
├── scripts/                     # Helper scripts
├── memory_wrapper.py            # Windows wrapper script
├── install.py                   # Enhanced installation script
└── tests/                       # Test suite
```

## Development Guidelines

- Python 3.10+ with type hints
- Use dataclasses for models
- Triple-quoted docstrings for modules and functions
- Async/await pattern for all I/O operations
- Follow PEP 8 style guidelines
- Include tests for new features

## License

MIT License - See LICENSE file for details

## Acknowledgments

- ChromaDB team for the vector database
- Sentence Transformers project for embedding models
- MCP project for the protocol specification

## Contact

[t.me/doobidoo](https://t.me/+MJtKdOWzmQdhY2Vi)
