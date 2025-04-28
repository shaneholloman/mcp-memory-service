# MCP Memory Service Documentation

Welcome to the MCP Memory Service documentation. This directory contains comprehensive guides for installing, using, and troubleshooting the service.

## Guides

- [Installation Guide](guides/installation.md) - Comprehensive installation instructions for all platforms
- [Troubleshooting Guide](guides/troubleshooting.md) - Solutions for common issues and debugging procedures
- [Migration Guide](guides/migration.md) - Instructions for migrating memories between different ChromaDB instances

## Technical Documentation

- [Tag Storage Procedure](technical/tag-storage.md) - Technical details about tag storage and migration
- [Memory Migration](technical/memory-migration.md) - Technical details about memory migration process

## Quick Links

- [Main README](../README.md) - Overview of the service and its features
- [Hardware Compatibility](../README.md#hardware-compatibility) - Supported platforms and accelerators
- [Configuration Options](../README.md#configuration-options) - Available environment variables and settings

## Platform-Specific Notes

### Windows
- Uses Windows-specific installation script
- Requires PyTorch wheels from specific index URL
- See [Windows Installation Guide](guides/installation.md#windows)

### macOS
- Intel x86_64: Uses specific PyTorch versions for compatibility
- Apple Silicon: Supports MPS acceleration with fallbacks
- See [macOS Installation Guide](guides/installation.md#macos)

## Available Scripts

The `scripts/` directory contains several useful tools:

### Core Scripts
- `run_memory_server.py` - Direct runner for MCP Memory Service
- `verify_environment.py` - Enhanced environment compatibility verification
- `fix_sitecustomize.py` - Fix for recursion issues with enhanced platform support
- `mcp-migration.py` - Memory migration tool supporting local and remote migrations

### Platform-Specific Scripts
- `install_windows.py` - Windows-specific installation
- `verify_pytorch_windows.py` - Windows PyTorch verification

## Script Usage Examples

### Environment Verification
```bash
python scripts/verify_environment.py
```

### Memory Migration
```bash
# Local to Remote Migration
python scripts/mcp-migration.py --source-type local --source-config /path/to/local/chroma --target-type remote --target-config '{"host": "remote-host", "port": 8000}'

# Remote to Local Migration
python scripts/mcp-migration.py --source-type remote --source-config '{"host": "remote-host", "port": 8000}' --target-type local --target-config /path/to/local/chroma
```

### Site Customization Fix
```bash
python scripts/fix_sitecustomize.py
```

## Configuration

- See [Claude MCP Configuration](../README.md#claude-mcp-configuration) for configuration options
- Sample configuration templates are available in the `claude_config/` directory