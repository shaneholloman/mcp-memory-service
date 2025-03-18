# MCP Memory Service Installation Guide

This guide provides detailed instructions for installing and configuring the MCP Memory Service, including the memory wrapper for Windows systems.

## Prerequisites

- Python 3.8 or higher
- pip (Python package installer)
- Git (to clone the repository)

## Installation Steps

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/mcp-memory-service.git
cd mcp-memory-service
```

### 2. Standard Installation

The simplest way to install the MCP Memory Service is to use the provided installation script:

```bash
python install.py
```

This script will:
- Detect your system configuration
- Check for dependencies
- Install the package with appropriate dependencies
- Configure paths for ChromaDB and backups
- Update Claude Desktop configuration if available

### 3. Windows Installation with Memory Wrapper

On Windows systems, the installation script automatically configures the service to use the `memory_wrapper.py` script, which ensures PyTorch is properly installed and handles Windows-specific issues.

The wrapper provides:
- Improved error handling
- Dependency verification
- Automatic PyTorch installation with the correct CUDA version
- Environment configuration for optimal performance

### 4. Manual Configuration

If you need to manually configure the MCP Memory Service:

#### 4.1. Configure Claude Desktop

Edit your Claude Desktop configuration file located at:
- Windows: `%LOCALAPPDATA%\Claude\claude_desktop_config.json`
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Linux: `~/.config/Claude/claude_desktop_config.json`

Add the following configuration:

```json
{
  "mcpServers": {
    "memory": {
      "command": "python",
      "args": ["path/to/memory_wrapper.py"],
      "env": {
        "MCP_MEMORY_CHROMA_PATH": "path/to/chroma_db",
        "MCP_MEMORY_BACKUPS_PATH": "path/to/backups"
      }
    }
  }
}
```

Replace `path/to/memory_wrapper.py`, `path/to/chroma_db`, and `path/to/backups` with the actual paths on your system.

#### 4.2. Configure Paths

The MCP Memory Service uses the following default paths:
- Windows: `%LOCALAPPDATA%\mcp-memory\chroma_db` and `%LOCALAPPDATA%\mcp-memory\backups`
- macOS: `~/Library/Application Support/mcp-memory/chroma_db` and `~/Library/Application Support/mcp-memory/backups`
- Linux: `~/.local/share/mcp-memory/chroma_db` and `~/.local/share/mcp-memory/backups`

You can customize these paths using environment variables:
- `MCP_MEMORY_CHROMA_PATH`: Path to ChromaDB storage
- `MCP_MEMORY_BACKUPS_PATH`: Path to backups storage

### 5. Running the Service

#### 5.1. Using the Wrapper (Windows)

```bash
python memory_wrapper.py
```

Optional arguments:
- `--debug`: Enable debug logging
- `--no-auto-install`: Disable automatic PyTorch installation
- `--force-cpu`: Force CPU-only mode even if GPU is available
- `--chroma-path PATH`: Custom path to ChromaDB storage
- `--backups-path PATH`: Custom path to backups storage

#### 5.2. Direct Execution

```bash
memory
```

Or:

```bash
python -m mcp_memory_service.server
```

## Troubleshooting

### PyTorch Installation Issues

If you encounter issues with PyTorch installation on Windows:

1. Manually install PyTorch with the appropriate CUDA version:
   ```bash
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
   ```
   (Replace `cu118` with the appropriate CUDA version for your system)

2. Run the installation script again:
   ```bash
   python install.py
   ```

### Memory Wrapper Debugging

For detailed debugging information:

```bash
python memory_wrapper.py --debug
```

This will print extensive information about your environment, installed packages, and any issues encountered.

### Common Issues

1. **"Method not found" errors in logs**: 
   - This may indicate that the MCP protocol implementation is missing required methods.
   - Ensure you have the latest version of the code with all required MCP protocol handlers.

2. **PyTorch CUDA errors**:
   - If you encounter CUDA-related errors, try forcing CPU mode:
   ```bash
   python memory_wrapper.py --force-cpu
   ```

3. **Import errors**:
   - If you see import errors, ensure all dependencies are installed:
   ```bash
   pip install -r requirements.txt
   ```

## Verification

To verify that the MCP Memory Service is running correctly:

1. Check the logs for successful initialization messages
2. Ensure there are no recurring errors
3. Test the service by using it with Claude Desktop

## Integration with Claude Desktop

After installation, Claude Desktop should automatically detect and use the MCP Memory Service. To verify:

1. Open Claude Desktop
2. Check the logs for successful connection to the memory service
3. Try using memory-related features in Claude Desktop

If Claude Desktop is not connecting to the memory service, ensure the configuration file is correctly set up as described in section 4.1.