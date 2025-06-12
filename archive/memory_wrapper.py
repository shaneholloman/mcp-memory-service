#!/usr/bin/env python3
"""
Enhanced Wrapper script for MCP Memory Service on Windows.
This script ensures that PyTorch is properly installed before running the memory server,
with improved debugging, error handling, and dependency management.
"""
# Disable sitecustomize.py and other import hooks to prevent recursion issues
# These must be set before importing any other modules
import os
os.environ["PYTHONNOUSERSITE"] = "1"  # Disable user site-packages
os.environ["PYTHONPATH"] = ""  # Clear PYTHONPATH

import sys
import subprocess
import importlib.util
import argparse
import traceback
import site
import platform
import time
from pathlib import Path

# Configure logging level
DEBUG = False

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="MCP Memory Service Wrapper")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--no-auto-install", action="store_true", help="Disable automatic PyTorch installation")
    parser.add_argument("--force-cpu", action="store_true", help="Force CPU-only mode even if GPU is available")
    parser.add_argument("--chroma-path", type=str, help="Path to ChromaDB storage")
    parser.add_argument("--backups-path", type=str, help="Path to backups storage")
    return parser.parse_args()

def print_debug(text):
    """Print formatted debug text to stderr."""
    if DEBUG:
        print(f"[DEBUG] {text}", file=sys.stderr, flush=True)

def print_info(text):
    """Print formatted info text to stderr."""
    print(f"[INFO] {text}", file=sys.stderr, flush=True)

def print_error(text):
    """Print formatted error text to stderr."""
    print(f"[ERROR] {text}", file=sys.stderr, flush=True)

def print_success(text):
    """Print formatted success text to stderr."""
    print(f"[SUCCESS] {text}", file=sys.stderr, flush=True)

def print_warning(text):
    """Print formatted warning text to stderr."""
    print(f"[WARNING] {text}", file=sys.stderr, flush=True)

def print_environment_info():
    """Print detailed environment information for debugging."""
    print_debug("=== Environment Information ===")
    print_debug(f"Python version: {sys.version}")
    print_debug(f"Python executable: {sys.executable}")
    print_debug(f"Platform: {platform.platform()}")
    print_debug(f"System: {platform.system()} {platform.release()}")
    print_debug(f"Architecture: {platform.machine()}")
    print_debug(f"Current working directory: {os.getcwd()}")
    print_debug(f"Script directory: {os.path.dirname(os.path.abspath(__file__))}")
    
    # Print Python path
    print_debug("Python path:")
    for path in sys.path:
        print_debug(f"  - {path}")
    
    # Print environment variables
    print_debug("Environment variables:")
    for key, value in os.environ.items():
        if key.startswith("PYTHON") or key.startswith("PATH") or key.startswith("MCP") or "TORCH" in key:
            print_debug(f"  - {key}={value}")
    
    # Check if running in virtual environment
    in_venv = sys.prefix != sys.base_prefix
    print_debug(f"Running in virtual environment: {in_venv}")
    if in_venv:
        print_debug(f"Virtual environment path: {sys.prefix}")

def check_installed_packages():
    """Check and print information about installed packages."""
    print_debug("=== Installed Packages ===")
    try:
        import pkg_resources
        for package in pkg_resources.working_set:
            if package.key in ["torch", "torchvision", "torchaudio", "sentence-transformers",
                              "transformers", "chromadb", "mcp", "mcp-memory-service"]:
                print_debug(f"  - {package.key}=={package.version}")
    except ImportError:
        print_debug("Could not import pkg_resources to check installed packages")

def check_pytorch():
    """Check if PyTorch is installed and properly configured."""
    print_info("Checking PyTorch installation")
    
    # Save original sys.path
    original_sys_path = sys.path.copy()
    
    # Temporarily disable import hooks
    original_meta_path = sys.meta_path
    sys.meta_path = [finder for finder in sys.meta_path
                    if not hasattr(finder, 'find_spec') or
                    not hasattr(finder, 'blocked_packages')]
    
    try:
        # Add site-packages to sys.path
        site_packages = os.path.join(sys.prefix, 'Lib', 'site-packages')
        if site_packages not in sys.path:
            sys.path.insert(0, site_packages)
        
        # Try to find torch directly in site-packages
        torch_path = os.path.join(site_packages, 'torch')
        if os.path.exists(torch_path) and torch_path not in sys.path:
            sys.path.insert(0, torch_path)
        
        # Try to import torch directly
        print_debug("Attempting to import torch directly")
        
        # Use importlib to import torch
        import importlib.util
        import importlib.machinery
        
        # Find the torch module spec
        torch_spec = importlib.machinery.PathFinder.find_spec('torch', [site_packages])
        if torch_spec is None:
            print_error("Could not find torch module spec")
            return False
        
        # Load the torch module
        torch = importlib.util.module_from_spec(torch_spec)
        torch_spec.loader.exec_module(torch)
        
        print_success(f"PyTorch is installed (version {torch.__version__})")
        print_debug(f"PyTorch location: {torch.__file__}")
        
        # Check if PyTorch C extensions are available
        if hasattr(torch, '_C'):
            print_debug("PyTorch C extensions are available")
        else:
            print_warning("PyTorch C extensions might not be properly installed")
        
        # Check if CUDA is available
        if torch.cuda.is_available():
            print_success(f"CUDA is available (version {torch.version.cuda})")
            print_info(f"GPU: {torch.cuda.get_device_name(0)}")
            print_debug(f"GPU Memory: {torch.cuda.get_device_properties(0).total_memory / (1024**3):.2f} GB")
            
            # Test a simple CUDA operation
            try:
                x = torch.rand(5, 3).cuda()
                y = torch.rand(5, 3).cuda()
                z = x + y
                print_debug("Basic CUDA tensor operations work correctly")
            except Exception as e:
                print_warning(f"CUDA tensor operations failed: {e}")
                print_warning("Falling back to CPU mode")
                os.environ["CUDA_VISIBLE_DEVICES"] = ""
        else:
            print_info("CUDA is not available, using CPU-only mode")
            
            # Check if DirectML is available
            try:
                directml_spec = importlib.machinery.PathFinder.find_spec('torch_directml', [site_packages])
                if directml_spec is not None:
                    torch_directml = importlib.util.module_from_spec(directml_spec)
                    directml_spec.loader.exec_module(torch_directml)
                    print_success(f"DirectML is available (version {torch_directml.__version__})")
            except Exception:
                print_debug("DirectML is not available")
            
        # Test a simple tensor operation
        try:
            x = torch.rand(5, 3)
            y = torch.rand(5, 3)
            z = x + y
            print_debug("Basic tensor operations work correctly")
        except Exception as e:
            print_error(f"Failed to perform basic tensor operations: {e}")
            return False
        
        # Add torch to sys.modules to make it available to other modules
        sys.modules['torch'] = torch
        
        return True
    except ImportError as e:
        print_error(f"PyTorch is not installed: {e}")
        return False
    except Exception as e:
        print_error(f"Error checking PyTorch installation: {e}")
        print_debug(traceback.format_exc())
        return False
    finally:
        # Restore original sys.path and meta_path
        sys.path = original_sys_path
        sys.meta_path = original_meta_path

def check_sentence_transformers():
    """Check if sentence-transformers is installed and properly configured."""
    print_info("Checking sentence-transformers installation")
    try:
        import sentence_transformers
        print_success(f"sentence-transformers is installed (version {sentence_transformers.__version__})")
        print_debug(f"sentence-transformers location: {sentence_transformers.__file__}")
        return True
    except ImportError as e:
        print_error(f"sentence-transformers is not installed: {e}")
        return False
    except Exception as e:
        print_error(f"Error checking sentence-transformers installation: {e}")
        print_debug(traceback.format_exc())
        return False

def check_chromadb():
    """Check if ChromaDB is installed and properly configured."""
    print_info("Checking ChromaDB installation")
    try:
        import chromadb
        print_success(f"ChromaDB is installed (version {chromadb.__version__})")
        print_debug(f"ChromaDB location: {chromadb.__file__}")
        return True
    except ImportError as e:
        print_error(f"ChromaDB is not installed: {e}")
        return False
    except Exception as e:
        print_error(f"Error checking ChromaDB installation: {e}")
        print_debug(traceback.format_exc())
        return False

def check_mcp():
    """Check if MCP is installed and properly configured."""
    print_info("Checking MCP installation")
    try:
        import mcp
        print_success(f"MCP is installed (version {mcp.__version__})")
        print_debug(f"MCP location: {mcp.__file__}")
        return True
    except ImportError as e:
        print_error(f"MCP is not installed: {e}")
        return False
    except Exception as e:
        print_error(f"Error checking MCP installation: {e}")
        print_debug(traceback.format_exc())
        return False

def prevent_pip_auto_install():
    """Prevent pip from automatically installing packages."""
    print_debug("Setting up environment variables to prevent automatic PyTorch installation")
    
    # Set environment variables to prevent pip from installing dependencies
    os.environ["PIP_NO_DEPENDENCIES"] = "1"
    os.environ["PIP_NO_INSTALL"] = "1"
    
    # Create a .pth file in site-packages to prevent automatic installation
    try:
        site_packages = site.getsitepackages()[0]
        pth_path = os.path.join(site_packages, 'no_auto_install.pth')
        
        if not os.path.exists(pth_path):
            with open(pth_path, 'w') as f:
                f.write("""
# Prevent automatic installation of packages
import os
os.environ["PIP_NO_DEPENDENCIES"] = "1"
os.environ["PIP_NO_INSTALL"] = "1"
""")
            print_debug(f"Created .pth file at {pth_path}")
    except Exception as e:
        print_debug(f"Could not create .pth file: {e}")
    
    # Monkey patch pip to prevent automatic installation
    try:
        # Try to import pip without triggering auto-installation
        pip_spec = importlib.util.find_spec("pip")
        if pip_spec:
            import pip._internal.resolve
            original_get_requirement = pip._internal.resolve.Resolver.get_installation_candidate
            
            def patched_get_installation_candidate(self, requirement_set, candidate):
                # Block torch installations from PyPI
                if candidate.name in ['torch', 'torchvision', 'torchaudio'] and 'pypi.org' in str(candidate.link):
                    print_warning(f"Blocked automatic installation attempt for {candidate.name} from {candidate.link}")
                    return None
                return original_get_requirement(self, requirement_set, candidate)
            
            pip._internal.resolve.Resolver.get_installation_candidate = patched_get_installation_candidate
            print_debug("Successfully patched pip to prevent automatic PyTorch installation")
    except (ImportError, AttributeError) as e:
        print_debug(f"Could not patch pip: {e}")

def install_pytorch(no_auto_install=False):
    """Install PyTorch using the platform-specific installation method."""
    if no_auto_install:
        print_warning("Automatic PyTorch installation is disabled")
        return False
    
    # Get the system information
    system = platform.system().lower()
    machine = platform.machine().lower()
    
    # Determine the appropriate installation method based on the platform
    if system == "windows":
        print_info("Installing PyTorch using the Windows-specific installation script")
        
        # Get the directory of this script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Run the Windows-specific installation script
        install_script = os.path.join(script_dir, "scripts", "install_windows.py")
        if os.path.exists(install_script):
            try:
                print_debug(f"Running installation script: {install_script}")
                subprocess.check_call([sys.executable, install_script])
                print_success("PyTorch installed successfully")
                
                # Reload sys.path to include newly installed packages
                print_debug("Reloading sys.path to include newly installed packages")
                site.main()
                
                return True
            except subprocess.SubprocessError as e:
                print_error(f"Failed to install PyTorch: {e}")
                return False
        else:
            print_error(f"Installation script not found: {install_script}")
            return False
    elif system == "darwin":  # macOS
        print_info("Installing PyTorch for macOS")
        try:
            # Install PyTorch for macOS - Use the specific versions you need
            print_debug("Installing PyTorch for macOS using pip")
            subprocess.check_call([
                sys.executable, '-m', 'pip', 'install',
                "torch==1.13.1",
                "torchvision==0.14.1",
                "torchaudio==0.13.1"
            ])
            
            # Reload sys.path to include newly installed packages
            print_debug("Reloading sys.path to include newly installed packages")
            site.main()
            
            print_success("PyTorch installed successfully for macOS")
            return True
        except subprocess.SubprocessError as e:
            print_error(f"Failed to install PyTorch for macOS: {e}")
            return False
    else:  # Linux or other platforms
        print_info("Installing PyTorch for Linux/other platform")
        try:
            # Generic PyTorch installation for Linux
            subprocess.check_call([
                sys.executable, '-m', 'pip', 'install',
                "torch==1.13.1",
                "torchvision==0.14.1", 
                "torchaudio==0.13.1"
            ])
            
            # Reload sys.path to include newly installed packages
            print_debug("Reloading sys.path to include newly installed packages")
            site.main()
            
            print_success("PyTorch installed successfully")
            return True
        except subprocess.SubprocessError as e:
            print_error(f"Failed to install PyTorch: {e}")
            return False

def setup_environment(args):
    """Set up environment variables for the memory server."""
    print_info("Setting up environment variables")
    
    # Set environment variables to prevent PyTorch from trying to update
    os.environ["PIP_NO_DEPENDENCIES"] = "1"
    os.environ["PIP_NO_INSTALL"] = "1"
    
    # Set environment variables for better cross-platform compatibility
    os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"
    
    # For Windows with limited GPU memory, use smaller chunks
    if platform.system().lower() == "windows":
        os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "max_split_size_mb:128"
    
    # Force CPU mode if requested
    if args.force_cpu:
        print_info("Forcing CPU-only mode")
        os.environ["CUDA_VISIBLE_DEVICES"] = ""
        os.environ["MCP_MEMORY_FORCE_CPU"] = "1"
    
    # Set ChromaDB path if provided
    if args.chroma_path:
        print_info(f"Using custom ChromaDB path: {args.chroma_path}")
        os.environ["MCP_MEMORY_CHROMA_PATH"] = args.chroma_path
    
    # Set backups path if provided
    if args.backups_path:
        print_info(f"Using custom backups path: {args.backups_path}")
        os.environ["MCP_MEMORY_BACKUPS_PATH"] = args.backups_path
    
    # Print all environment variables for debugging
    if DEBUG:
        print_debug("Environment variables after setup:")
        for key, value in sorted(os.environ.items()):
            if key.startswith("PYTHON") or key.startswith("PATH") or key.startswith("MCP") or "TORCH" in key:
                print_debug(f"  - {key}={value}")

def run_memory_server():
    """Run the MCP Memory Service with enhanced error handling."""
    print_info("Starting MCP Memory Service")
    
    # Save original sys.path and meta_path
    original_sys_path = sys.path.copy()
    original_meta_path = sys.meta_path
    
    # Temporarily disable import hooks
    sys.meta_path = [finder for finder in sys.meta_path
                    if not hasattr(finder, 'find_spec') or
                    not hasattr(finder, 'blocked_packages')]
    
    try:
        # Get the directory of this script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Add src directory to path if it exists
        src_dir = os.path.join(script_dir, "src")
        if os.path.exists(src_dir) and src_dir not in sys.path:
            print_debug(f"Adding {src_dir} to sys.path")
            sys.path.insert(0, src_dir)
        
        # Add site-packages to sys.path
        site_packages = os.path.join(sys.prefix, 'Lib', 'site-packages')
        if site_packages not in sys.path:
            sys.path.insert(0, site_packages)
        
        # Try to import using importlib
        print_debug("Attempting to import mcp_memory_service.server using importlib")
        import importlib.util
        import importlib.machinery
        
        # First try to find the module in site-packages
        server_spec = importlib.machinery.PathFinder.find_spec('mcp_memory_service.server', [site_packages])
        
        # If not found, try to find it in src directory
        if server_spec is None and os.path.exists(src_dir):
            server_spec = importlib.machinery.PathFinder.find_spec('mcp_memory_service.server', [src_dir])
        
        if server_spec is None:
            print_error("Could not find mcp_memory_service.server module spec")
            sys.exit(1)
        
        # Load the server module
        server = importlib.util.module_from_spec(server_spec)
        server_spec.loader.exec_module(server)
        
        print_debug("Successfully imported mcp_memory_service.server")
        
        # Run the memory server with error handling
        try:
            print_debug("Calling mcp_memory_service.server.main()")
            server.main()
        except Exception as e:
            print_error(f"Error running memory server: {e}")
            print_debug(traceback.format_exc())
            sys.exit(1)
    except ImportError as e:
        print_error(f"Failed to import mcp_memory_service.server: {e}")
        print_debug(traceback.format_exc())
        sys.exit(1)
    except Exception as e:
        print_error(f"Error setting up memory server: {e}")
        print_debug(traceback.format_exc())
        sys.exit(1)
    finally:
        # Restore original sys.path and meta_path
        sys.path = original_sys_path
        sys.meta_path = original_meta_path

def main():
    """Main function with enhanced error handling and debugging."""
    # Parse command line arguments
    args = parse_args()
    
    # Set global debug flag
    global DEBUG
    DEBUG = args.debug
    
    print_info("Enhanced Memory wrapper script starting")
    
    # Print detailed environment information for debugging
    if DEBUG:
        print_environment_info()
        check_installed_packages()
    
    # Set up environment variables
    setup_environment(args)
    
    # Prevent automatic PyTorch installation
    prevent_pip_auto_install()
    
    # Check if PyTorch is installed
    pytorch_ok = check_pytorch()
    if not pytorch_ok:
        print_info("PyTorch is not installed or not working properly")
        if not args.no_auto_install:
            print_info("Attempting to install PyTorch")
            if not install_pytorch(args.no_auto_install):
                print_error("Failed to install PyTorch, cannot continue")
                sys.exit(1)
        else:
            print_error("Automatic PyTorch installation is disabled, cannot continue")
            sys.exit(1)
    
    # Check other dependencies
    st_ok = check_sentence_transformers()
    chroma_ok = check_chromadb()
    mcp_ok = check_mcp()
    
    if not (st_ok and chroma_ok and mcp_ok):
        print_warning("Some dependencies are missing or not working properly")
        print_warning("Will attempt to continue anyway, but errors may occur")
    
    # Add a small delay to ensure all imports are properly initialized
    print_debug("Waiting 1 second before starting the memory server")
    time.sleep(1)
    
    # Run the memory server
    run_memory_server()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print_info("Script interrupted by user")
        sys.exit(0)
    except Exception as e:
        print_error(f"Unhandled exception: {e}")
        print_debug(traceback.format_exc())
        sys.exit(1)