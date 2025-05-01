# MCP Memory Service - Development Guidelines

## Commands
- Run memory server: `python scripts/run_memory_server.py`
- Run tests: `pytest tests/`
- Run specific test: `pytest tests/test_memory_ops.py::test_store_memory -v`
- Check environment: `python scripts/verify_environment_enhanced.py`
- Windows installation: `python scripts/install_windows.py`
- Build package: `python -m build`

## Installation Guidelines
- Always install in a virtual environment: `python -m venv venv`
- Use `install.py` for cross-platform installation
- Windows requires special PyTorch installation with correct index URL:
  ```bash
  pip install torch==2.1.0 torchvision==2.1.0 torchaudio==2.1.0 --index-url https://download.pytorch.org/whl/cu118
  ```
- For recursion errors, run: `python scripts/fix_sitecustomize.py`

## Code Style
- Python 3.10+ with type hints
- Use dataclasses for models (see `models/memory.py`)
- Triple-quoted docstrings for modules and functions
- Async/await pattern for all I/O operations
- Error handling with specific exception types and informative messages
- Logging with appropriate levels for different severity
- Commit messages follow semantic release format: `type(scope): message`

## Project Structure
- `src/mcp_memory_service/` - Core package code
  - `models/` - Data models
  - `storage/` - Database abstraction
  - `utils/` - Helper functions
  - `server.py` - MCP protocol implementation
- `scripts/` - Utility scripts
- `memory_wrapper.py` - Windows wrapper script
- `install.py` - Cross-platform installation script

## Dependencies
- ChromaDB (0.5.23) for vector database
- sentence-transformers (>=2.2.2) for embeddings
- PyTorch (platform-specific installation)
- MCP protocol (>=1.0.0, <2.0.0) for client-server communication

## Troubleshooting
- For Windows installation issues, use `scripts/install_windows.py`
- Apple Silicon requires Python 3.10+ built for ARM64
- CUDA issues: verify with `torch.cuda.is_available()`
- For MCP protocol issues, check `server.py` for required methods

## Debugging with MCP-Inspector

To debug the MCP-MEMORY-SERVICE using the [MCP-Inspector](https://modelcontextprotocol.io/docs/tools/inspector) tool, you can use the following command pattern:

```bash
MCP_MEMORY_CHROMA_PATH="/path/to/your/chroma_db" MCP_MEMORY_BACKUPS_PATH="/path/to/your/backups" npx @modelcontextprotocol/inspector uv --directory /path/to/mcp-memory-service run memory
```

Replace the paths with your specific directories:
- `/path/to/your/chroma_db`: Location where Chroma database files are stored
- `/path/to/your/backups`: Location for memory backups
- `/path/to/mcp-memory-service`: Directory containing the MCP-MEMORY-SERVICE code

For example:
```bash
MCP_MEMORY_CHROMA_PATH="~/Library/Mobile Documents/com~apple~CloudDocs/AI/claude-memory/chroma_db" MCP_MEMORY_BACKUPS_PATH="~/Library/Mobile Documents/com~apple~CloudDocs/AI/claude-memory/backups" npx @modelcontextprotocol/inspector uv --directory ~/Documents/GitHub/mcp-memory-service run memory
```

This command sets the required environment variables and runs the memory service through the inspector tool for debugging purposes.
