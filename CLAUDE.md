# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

MCP Memory Service is a Model Context Protocol server that provides semantic memory and persistent storage capabilities for Claude Desktop using ChromaDB and sentence transformers. The project enables long-term memory storage with semantic search across conversations.

## Key Commands

### Development
- **Install dependencies**: `python install.py` (platform-aware installation)
- **Run server**: `python scripts/run_memory_server.py` or `uv run memory`
- **Run tests**: `pytest tests/`
- **Run specific test**: `pytest tests/unit/test_memory_models.py::TestMemoryModel::test_memory_creation`
- **Check environment**: `python scripts/verify_environment.py`
- **Debug with MCP Inspector**: `npx @modelcontextprotocol/inspector uv --directory /path/to/repo run memory`
- **Check documentation links**: `python scripts/check_documentation_links.py` (validates all internal markdown links)
- **Test Docker functionality**: `python scripts/test_docker_functionality.py` (comprehensive Docker container verification)
- **Setup git merge drivers**: `./scripts/setup-git-merge-drivers.sh` (one-time setup for new contributors)
- **Store memory**: `/memory-store "content"` - Store information directly to MCP Memory Service at narrowbox.local:8443

### Build & Package
- **Build package**: `python -m build`
- **Install locally**: `pip install -e .`

## Architecture

### Core Components

1. **Server Layer** (`src/mcp_memory_service/server.py`)
   - Implements MCP protocol with async request handlers
   - Global model and embedding caches for performance
   - Handles all memory operations (store, retrieve, search, delete)

2. **Storage Abstraction** (`src/mcp_memory_service/storage/`)
   - `base.py`: Abstract interface for storage backends
   - `chroma.py`: ChromaDB implementation
   - `chroma_enhanced.py`: Extended features (time parsing, advanced search)

3. **Models** (`src/mcp_memory_service/models/memory.py`)
   - `Memory`: Core dataclass for memory entries
   - `MemoryMetadata`: Metadata structure
   - All models use Python dataclasses with type hints

4. **Configuration** (`src/mcp_memory_service/config.py`)
   - Environment-based configuration
   - Platform-specific optimizations
   - Hardware acceleration detection

### Key Design Patterns

- **Async/Await**: All I/O operations are async
- **Type Safety**: Comprehensive type hints (Python 3.10+)
- **Error Handling**: Specific exception types with clear messages
- **Caching**: Global caches for models and embeddings to improve performance
- **Platform Detection**: Automatic hardware optimization (CUDA, MPS, DirectML, ROCm)

### MCP Protocol Operations

Memory operations implemented:
- `store_memory`: Store new memories with tags and metadata
- `retrieve_memory`: Basic retrieval by query
- `recall_memory`: Natural language time-based retrieval
- `search_by_tag`: Tag-based search
- `delete_memory`: Delete specific memories
- `delete_by_tag/tags`: Bulk deletion by tags
- `optimize_db`: Database optimization
- `check_database_health`: Health monitoring
- `debug_retrieve`: Similarity analysis for debugging

### Testing

Tests are organized by type:
- `tests/unit/`: Unit tests for individual components
- `tests/integration/`: Integration tests for full workflows
- `tests/performance/`: Performance benchmarks

Run tests with coverage: `pytest --cov=src/mcp_memory_service tests/`

### Environment Variables

Key configuration:
- `MCP_MEMORY_CHROMA_PATH`: ChromaDB storage location (default: `~/.mcp_memory_chroma`)
- `MCP_MEMORY_BACKUPS_PATH`: Backup location (default: `~/.mcp_memory_backups`)
- `MCP_MEMORY_INCLUDE_HOSTNAME`: Enable automatic machine identification (default: `false`)
  - When enabled, adds client hostname as `source:hostname` tag to stored memories
  - Clients can specify hostname via `client_hostname` parameter or `X-Client-Hostname` header
  - Fallback to server hostname if client doesn't provide one
- `MCP_API_KEY`: API key for HTTP authentication (optional, no default)
- `LOG_LEVEL`: Logging verbosity (DEBUG, INFO, WARNING, ERROR)
- Platform-specific: `PYTORCH_ENABLE_MPS_FALLBACK`, `MCP_MEMORY_USE_ONNX`

#### API Key Configuration

The `MCP_API_KEY` environment variable enables HTTP API authentication:

```bash
# Generate a secure API key
export MCP_API_KEY="$(openssl rand -base64 32)"

# Or set manually
export MCP_API_KEY="your-secure-api-key-here"
```

When set, all HTTP API requests require the `Authorization: Bearer <api_key>` header. This is essential for production deployments and multi-client setups.

### Platform Support

The codebase includes platform-specific optimizations:
- **macOS**: MPS acceleration for Apple Silicon, CPU fallback for Intel
- **Windows**: CUDA, DirectML, or CPU
- **Linux**: CUDA, ROCm, or CPU

Hardware detection is automatic via `utils/system_detection.py`.

### Memory Storage Command

The `/memory-store` command allows direct storage of information to the MCP Memory Service:

**Basic Usage:**
```bash
/memory-store "content to store"
```

**Advanced Usage:**
- Automatically detects project context and adds relevant tags
- Captures git repository information and recent commits
- Adds client hostname via the hostname capture feature
- Uses direct curl to `https://narrowbox.local:8443/api/memories`
- No temporary files or confirmation prompts required

**Example Patterns:**
```bash
/memory-store "Fixed critical bug in hostname capture logic"
/memory-store "Decision: Use SQLite-vec for better performance than ChromaDB"
/memory-store "TODO: Update Docker configuration after database backend change"
```

The command will:
1. Analyze current working directory and git context
2. Generate appropriate tags (project name, file types, git commits)
3. Store directly via curl with proper JSON formatting
4. Return content hash and applied tags for confirmation

### Development Tips

1. When modifying storage backends, ensure compatibility with the abstract base class
2. Memory operations should handle duplicates gracefully (content hashing)
3. Time parsing supports natural language ("yesterday", "last week")
4. Use the debug_retrieve operation to analyze similarity scores
5. The server maintains global state for models - be careful with concurrent modifications
6. All new features should include corresponding tests
7. Use semantic commit messages for version management
8. Use `/memory-store` to capture important decisions and context during development

### Git Configuration

#### Automated uv.lock Conflict Resolution

The repository includes automated resolution for `uv.lock` conflicts:

1. **For new contributors**: Run `./scripts/setup-git-merge-drivers.sh` once after cloning
2. **How it works**: 
   - Git automatically resolves `uv.lock` conflicts using the incoming version
   - Then runs `uv sync` to regenerate the lock file based on your `pyproject.toml`
   - Ensures consistent dependency resolution across all environments

Files involved:
- `.gitattributes`: Defines merge strategy for `uv.lock`
- `scripts/uv-lock-merge.sh`: Custom merge driver script
- `scripts/setup-git-merge-drivers.sh`: One-time setup for contributors

### Common Issues

1. **MPS Fallback**: On macOS, if MPS fails, set `PYTORCH_ENABLE_MPS_FALLBACK=1`
2. **ONNX Runtime**: For compatibility issues, use `MCP_MEMORY_USE_ONNX=true`
3. **ChromaDB Persistence**: Ensure write permissions for storage paths
4. **Memory Usage**: Model loading is deferred until first use to reduce startup time
5. **uv.lock Conflicts**: Should resolve automatically; if not, ensure git merge drivers are set up