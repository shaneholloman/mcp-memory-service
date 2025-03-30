#!/usr/bin/env python3
"""
Conversion script to help users migrate from pip to UV for the MCP Memory Service.
This script:
1. Installs UV if not already installed
2. Creates a UV-based virtual environment
3. Installs dependencies using UV
4. Creates platform-specific shortcuts
"""
import os
import sys
import platform
import subprocess
import shutil
from pathlib import Path

def print_header(text):
    """Print a formatted header."""
    print("\n" + "=" * 80)
    print(f" {text}")
    print("=" * 80)

def print_step(step, text):
    """Print a formatted step."""
    print(f"\n[{step}] {text}")

def print_info(text):
    """Print formatted info text."""
    print(f"  → {text}")

def print_error(text):
    """Print formatted error text."""
    print(f"  ❌ ERROR: {text}")

def print_success(text):
    """Print formatted success text."""
    print(f"  ✅ {text}")

def print_warning(text):
    """Print formatted warning text."""
    print(f"  ⚠️  {text}")

def check_uv():
    """Check if UV is installed."""
    try:
        subprocess.check_call([sys.executable, '-m', 'uv', '--version'], 
                             stdout=subprocess.DEVNULL, 
                             stderr=subprocess.DEVNULL)
        print_success("UV is already installed")
        return True
    except subprocess.SubprocessError:
        print_info("UV is not installed")
        return False

def install_uv():
    """Install UV package manager."""
    print_step("1", "Installing UV package manager")
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'uv'])
        print_success("UV installed successfully")
        return True
    except subprocess.SubprocessError as e:
        print_error(f"Failed to install UV: {e}")
        return False

def create_venv():
    """Create a virtual environment using UV."""
    print_step("2", "Creating a virtual environment with UV")
    
    # Determine venv path
    venv_path = os.path.join(os.getcwd(), ".venv")
    if os.path.exists(venv_path):
        print_warning(f"Virtual environment already exists at {venv_path}")
        response = input("Do you want to recreate it? (y/n): ")
        if response.lower() == 'y':
            try:
                shutil.rmtree(venv_path)
                print_info(f"Removed existing virtual environment: {venv_path}")
            except Exception as e:
                print_error(f"Failed to remove existing virtual environment: {e}")
                return False
        else:
            print_info("Skipping virtual environment creation")
            return True
    
    try:
        subprocess.check_call([sys.executable, '-m', 'uv', 'venv'])
        print_success(f"Created virtual environment at {venv_path}")
        
        # Print activation instructions
        if platform.system().lower() == "windows":
            print_info("Activate it with: .venv\\Scripts\\activate")
        else:
            print_info("Activate it with: source .venv/bin/activate")
        
        return True
    except subprocess.SubprocessError as e:
        print_error(f"Failed to create virtual environment: {e}")
        return False

def install_dependencies():
    """Install dependencies using UV."""
    print_step("3", "Installing dependencies with UV")
    
    # First check if requirements.txt exists
    req_path = os.path.join(os.getcwd(), "requirements.txt")
    if not os.path.exists(req_path):
        print_error(f"requirements.txt not found at {req_path}")
        return False
    
    try:
        print_info("Installing dependencies from requirements.txt")
        subprocess.check_call([sys.executable, '-m', 'uv', 'pip', 'install', '-r', 'requirements.txt'])
        print_success("Dependencies installed successfully")
        
        # Install the package itself
        print_info("Installing mcp-memory-service package")
        subprocess.check_call([sys.executable, '-m', 'uv', 'pip', 'install', '-e', '.'])
        print_success("Package installed successfully")
        
        return True
    except subprocess.SubprocessError as e:
        print_error(f"Failed to install dependencies: {e}")
        return False

def create_shortcuts():
    """Create platform-specific shortcuts for running with UV."""
    print_step("4", "Creating shortcuts")
    
    # Create .bat file for Windows
    if platform.system().lower() == "windows":
        try:
            with open("run-memory-uv.bat", "w") as f:
                f.write("@echo off\n")
                f.write("echo Running MCP Memory Service with UV...\n")
                f.write("call .venv\\Scripts\\activate\n")
                f.write("python -m uv run memory %*\n")
            print_success("Created run-memory-uv.bat")
        except Exception as e:
            print_error(f"Failed to create .bat file: {e}")
    else:
        # Create shell script for Unix-like systems
        try:
            with open("run-memory-uv.sh", "w") as f:
                f.write("#!/bin/bash\n")
                f.write("echo \"Running MCP Memory Service with UV...\"\n")
                f.write("source .venv/bin/activate\n")
                f.write("python -m uv run memory \"$@\"\n")
            
            # Make it executable
            os.chmod("run-memory-uv.sh", 0o755)
            print_success("Created run-memory-uv.sh")
        except Exception as e:
            print_error(f"Failed to create shell script: {e}")
    
    # Create a platform-independent Python wrapper
    try:
        with open("run_with_uv.py", "w") as f:
            f.write("""#!/usr/bin/env python3
'''
Simple wrapper to run MCP Memory Service with UV
'''
import os
import sys
import subprocess

def main():
    print("Running MCP Memory Service with UV...")
    
    cmd = [sys.executable, '-m', 'uv', 'run', 'memory']
    cmd.extend(sys.argv[1:])  # Add any command line arguments
    
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\\nInterrupted by user")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
""")
        print_success("Created run_with_uv.py")
    except Exception as e:
        print_error(f"Failed to create Python wrapper: {e}")

def update_config():
    """Provide instructions for updating Claude Desktop configuration."""
    print_step("5", "Updating Claude Desktop configuration")
    
    print_info("To use UV with Claude Desktop, update your claude_desktop_config.json:")
    print("""
  "memory": {
    "command": "uv",
    "args": [
      "--directory",
      "your_mcp_memory_service_directory",
      "run",
      "memory"
    ],
    "env": {
      "MCP_MEMORY_CHROMA_PATH": "your_chroma_db_path",
      "MCP_MEMORY_BACKUPS_PATH": "your_backups_path"
    }
  }""")
    
    print_info("Replace paths with your actual file locations")

def main():
    """Main function to convert from pip to UV."""
    print_header("Converting MCP Memory Service to UV")
    
    # Make sure we're in the right directory
    repo_root = Path(__file__).parent.parent
    if not (repo_root / "src" / "mcp_memory_service").exists():
        print_error("This script must be run from the mcp-memory-service directory")
        print_info(f"Please change to: {repo_root}")
        return
    
    # Check and install UV
    if not check_uv() and not install_uv():
        print_error("Failed to install UV, cannot continue")
        return
    
    # Create virtual environment
    if not create_venv():
        print_warning("Failed to create virtual environment, continuing anyway")
    
    # Install dependencies
    if not install_dependencies():
        print_warning("Failed to install all dependencies, you may need to run manually:")
        print_info("uv pip install -r requirements.txt")
        print_info("uv pip install -e .")
    
    # Create shortcuts
    create_shortcuts()
    
    # Update config
    update_config()
    
    print_header("Migration Complete")
    print_info("You can now run the memory service using UV:")
    if platform.system().lower() == "windows":
        print_info("  run-memory-uv.bat")
    else:
        print_info("  ./run-memory-uv.sh")
    print_info("  python run_with_uv.py")
    print_info("  python -m uv run memory")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nScript interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)
