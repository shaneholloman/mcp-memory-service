# MCP Memory Service Installation Guide

This guide provides detailed instructions for installing the MCP Memory Service on different platforms and troubleshooting common installation issues.

## Prerequisites

- Python 3.10 or newer
- pip (latest version recommended)
- A virtual environment (venv or conda)
- Git (to clone the repository)

## Installation Methods

### 1. Standard Installation (All Platforms)

1. **Clone the repository**:
   ```bash
   git clone https://github.com/doobidoo/mcp-memory-service.git
   cd mcp-memory-service
   ```

2. **Create and activate a virtual environment**:
   ```bash
   # Using venv (recommended)
   python -m venv venv
   
   # On Windows
   venv\Scripts\activate
   
   # On macOS/Linux
   source venv/bin/activate
   ```

3. **Run the installation script**:
   ```bash
   python install.py
   ```

4. **Verify the installation**:
   ```bash
   python scripts/verify_environment_enhanced.py
   ```

### 2. Docker Installation (Recommended for Cross-Platform Compatibility)

For the easiest cross-platform deployment, use Docker:

1. **Clone the repository**:
   ```bash
   git clone https://github.com/doobidoo/mcp-memory-service.git
   cd mcp-memory-service
   ```

2. **Build and run with Docker Compose**:
   ```bash
   # Create directories for persistent storage
   mkdir -p ./data/chroma_db ./data/backups
   
   # Build and start the service
   docker-compose up -d
   ```

3. **Configure Claude Desktop** to use the Docker container:
   ```json
   {
     "memory": {
       "command": "docker",
       "args": [
         "run",
         "--rm",
         "-p", "8000:8000",
         "-v", "/path/to/data/chroma_db:/app/chroma_db",
         "-v", "/path/to/data/backups:/app/backups",
         "-e", "MCP_MEMORY_CHROMA_PATH=/app/chroma_db",
         "-e", "MCP_MEMORY_BACKUPS_PATH=/app/backups",
         "mcp-memory-service"
       ]
     }
   }
   ```

For detailed Docker deployment instructions, see [Docker Deployment Guide](../technical/docker-deployment.md).

## Platform-Specific Installation Instructions

### Windows

Windows requires special handling for PyTorch installation due to platform-specific wheel availability:

1. **Use the Windows-specific installation script** (recommended):
   ```bash
   python scripts/install_windows.py
   ```

2. **Alternative: Manual PyTorch installation**:
   ```bash
   # First install PyTorch with the appropriate index URL
   pip install torch==2.1.0 torchvision==2.1.0 torchaudio==2.1.0 --index-url https://download.pytorch.org/whl/cu118
   
   # Then install other dependencies without PyTorch
   pip install -r requirements.txt --no-deps
   pip install "mcp>=1.0.0,<2.0.0"
   
   # Finally install the package
   pip install -e .
   ```

3. **Fix recursion issues** (if encountered):
   ```bash
   python scripts/fix_sitecustomize.py
   ```

### macOS

#### Apple Silicon (M1/M2/M3)

For Apple Silicon Macs:

1. **Ensure you're using Python 3.10+ built for ARM64**:
   ```bash
   python --version
   python -c "import platform; print(platform.machine())"
   # Should output "arm64"
   ```
**If not, you can follow these steps to create and run the server in a virtual environment (Recommended)**
```bash
# requirements: 1-homebrew 2-python installation (brew install python)
# for Apple Silicon Macs, make sure to first uninstall pytorch, torch, torchvision if you have any of them installed
brew uninstall pytorch torchvision

# create and activate a virtual environment (first, make sure to delete the .venv folder if you git clone)
cd /path/to/your/cloned/project/
python -m venv .venv
source .venv/bin/activate

# install uv in the virtual environment (as the command that handles the project in JSON is uv, and it is more compatible with the
# project than python/python3/rye/etc.)
pip install uv

# make sure to give the JSON config the full PATH to the uv for Claude desktop.  "PATH_TO_YOUR_CLONED_PROJECT/.venv/bin/uv"

# Then install Pytorch manually
pip install torch torchvision torchaudio

# Then install other dependencies without PyTorch
pip install -r requirements.txt --no-deps

# Finally install the package
pip install -e .

#Then check if the server runs
memory
```

3. **Run the standard installation**:
   ```bash
   python install.py
   ```

4. **Enable MPS acceleration**:
   ```bash
   export PYTORCH_ENABLE_MPS_FALLBACK=1
   ```

#### Intel CPUs

For Intel-based Macs, there are known dependency conflicts between PyTorch and sentence-transformers. The installation script and memory wrapper have been updated to handle these correctly and now use these specific versions:

- torch==1.13.1
- torchvision==0.14.1
- torchaudio==0.13.1
- sentence-transformers==2.2.2

1. **Use the standard installation script** (now properly detects macOS Intel):
   ```bash
   python install.py
   ```
   
   This will now automatically install the correct versions for macOS Intel x86_64.

2. **Manual installation** (if the script fails):
   ```bash
   # First remove existing packages
   pip uninstall -y torch torchvision torchaudio sentence-transformers
   
   # Install compatible versions for Intel macOS
   pip install torch==1.13.1 torchvision==0.14.1 torchaudio==0.13.1
   pip install sentence-transformers==2.2.2
   
   # Install remaining dependencies
   pip install --no-deps .
   pip install chromadb==0.5.23 tokenizers==0.20.3 mcp>=1.0.0,<2.0.0
   ```
   
> Note: Previous versions recommended using torch==2.0.1, but 1.13.1 has been found to work more reliably across different Intel macOS configurations.

### Linux

For Linux with NVIDIA GPU:

1. **Ensure CUDA toolkit is installed**:
   ```bash
   nvidia-smi  # Check CUDA availability
   ```

2. **Run the standard installation**:
   ```bash
   python install.py
   ```

For Linux with AMD GPU:

1. **Ensure ROCm is installed** (for AMD GPUs):
   ```bash
   rocminfo  # Check ROCm availability
   ```

2. **Set ROCm environment variable before installation**:
   ```bash
   export MCP_MEMORY_USE_ROCM=1
   python install.py
   ```

## Configuring Claude Desktop

### Standard Configuration

Add the following to your `claude_desktop_config.json` file:

```json
{
  "memory": {
    "command": "uv",
    "args": [
      "--directory",
      "/path/to/mcp-memory-service",
      "run",
      "memory"
    ],
    "env": {
      "MCP_MEMORY_CHROMA_PATH": "/path/to/chroma_db",
      "MCP_MEMORY_BACKUPS_PATH": "/path/to/backups"
    }
  }
}
```

### Windows-Specific Configuration

For Windows, use the wrapper script:

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

## Troubleshooting Common Installation Issues

### PyTorch Installation Errors on Windows

If you see errors like:
```
error: Distribution `torch==2.5.1 @ registry+https://pypi.org/simple` can't be installed because it doesn't have a source distribution or wheel for the current platform
```

This means PyTorch doesn't have a wheel available for your Windows platform.

**Solution**:
1. Use the Windows-specific installation script:
   ```bash
   python scripts/install_windows.py
   ```

2. Or install PyTorch manually with the correct index URL:
   ```bash
   pip install torch==2.1.0 torchvision==2.1.0 torchaudio==2.1.0 --index-url https://download.pytorch.org/whl/cu118
   ```

### Recursion Errors Related to sitecustomize.py

If you see errors like:
```
RecursionError: maximum recursion depth exceeded while calling a Python object
```

**Solution**:
Run the sitecustomize fix script:
```bash
python scripts/fix_sitecustomize.py
```

### MPS Acceleration Issues on Apple Silicon

If you're having issues with GPU acceleration on Apple Silicon:

**Solution**:
1. Set the MPS fallback environment variable:
   ```bash
   export PYTORCH_ENABLE_MPS_FALLBACK=1
   ```

2. If you're still having issues, force CPU-only mode:
   ```bash
   export MCP_MEMORY_FORCE_CPU=1
   ```

### Memory Issues or Slow Performance

If you're experiencing out-of-memory errors or slow performance:

**Solution**:
1. Use a smaller batch size:
   ```bash
   export MCP_MEMORY_BATCH_SIZE=4
   ```

2. Use a smaller embedding model:
   ```bash
   export MCP_MEMORY_MODEL_NAME=paraphrase-MiniLM-L3-v2
   ```

### MCP Protocol Compatibility Issues

If you're seeing "Method not found" errors or JSON error popups in Claude Desktop:

**Solution**:
Make sure you're using the latest version of the MCP Memory Service which includes protocol compatibility fixes. Check that your server.py contains the required MCP protocol methods:
- resources/list
- resources/read
- resource_templates/list

### Dependency Version Conflicts

If you're seeing dependency version conflicts:

**Solution**:
1. Install dependencies with the `--no-deps` flag:
   ```bash
   pip install -r requirements.txt --no-deps
   ```

2. Install specific versions of problematic dependencies:
   ```bash
   pip install tokenizers==0.13.3
   ```

### PyTorch and sentence-transformers Conflicts on macOS Intel

If you see errors like these on macOS with Intel CPUs:
```
Could not find a version that satisfies the requirement torch>=1.11.0, sentence-transformers requires that torch>=1.11.0
```

Or if you encounter errors about the Windows installation script being used on macOS:
```
Installing PyTorch using the Windows-specific installation script
Installation script not found: /path/to/scripts/install_windows.py
```

These issues have been fixed in the latest version. The installation scripts now correctly detect macOS on Intel and install the appropriate versions.

**Solutions**:

1. **Use the updated standard installation** (recommended):
   ```bash
   python install.py
   ```
   
   The installation script now automatically detects macOS Intel and installs the correct versions (torch==1.13.1, torchvision==0.14.1, torchaudio==0.13.1).

2. **Manual installation**:
   ```bash
   # Uninstall conflicting packages
   pip uninstall -y torch torchvision torchaudio sentence-transformers
   
   # Install the specific versions known to work reliably on Intel macOS
   pip install torch==1.13.1 torchvision==0.14.1 torchaudio==0.13.1
   pip install sentence-transformers==2.2.2
   
   # Install the package with --no-deps
   pip install --no-deps .
   
   # Install remaining dependencies
   pip install chromadb==0.5.23 tokenizers==0.20.3 mcp>=1.0.0,<2.0.0 websockets>=11.0.3
   ```

3. **If you're experiencing issues with memory_wrapper.py**, make sure you have the latest version which now properly handles macOS platform detection and installs the correct PyTorch versions.

## Debug and Verification Tools

Use these scripts to debug and verify your installation:

```bash
# Enhanced environment verification
python scripts/verify_environment_enhanced.py

# Export detailed diagnostics
python scripts/verify_environment_enhanced.py --export

# Windows-specific PyTorch verification
python scripts/verify_pytorch_windows.py

# Test the memory server directly
python scripts/run_memory_server.py

# Test basic operations
python src/chroma_test_isolated.py
```

## Getting Help

If you encounter issues not covered in this guide:

1. Check the logs in Claude Desktop: `<log-directory>/mcp-server-memory.log`
2. Run the memory server directly to see any errors: `python scripts/run_memory_server.py`
3. Check the GitHub repository for issues or updates
4. Contact the developer via Telegram: t.me/doobeedoo