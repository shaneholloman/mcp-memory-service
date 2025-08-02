#!/usr/bin/env python3
"""
Installation script for MCP Memory Service with cross-platform compatibility.
This script guides users through the installation process with the appropriate
dependencies for their platform.
"""
import os
import sys
import platform
import subprocess
import argparse
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

def detect_system():
    """Detect the system architecture and platform."""
    system = platform.system().lower()
    machine = platform.machine().lower()
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
    
    is_windows = system == "windows"
    is_macos = system == "darwin"
    is_linux = system == "linux"
    is_arm = machine in ("arm64", "aarch64")
    is_x86 = machine in ("x86_64", "amd64", "x64")
    
    print_info(f"System: {platform.system()} {platform.release()}")
    print_info(f"Architecture: {machine}")
    print_info(f"Python: {python_version}")
    
    # Check for virtual environment
    in_venv = sys.prefix != sys.base_prefix
    if not in_venv:
        print_warning("Not running in a virtual environment. It's recommended to install in a virtual environment.")
    else:
        print_info(f"Virtual environment: {sys.prefix}")
    
    # Check for Homebrew PyTorch installation
    has_homebrew_pytorch = False
    homebrew_pytorch_version = None
    if is_macos:
        try:
            # Check if pytorch is installed via brew
            result = subprocess.run(
                ['brew', 'list', 'pytorch', '--version'],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                has_homebrew_pytorch = True
                # Extract version from output
                version_line = result.stdout.strip()
                homebrew_pytorch_version = version_line.split()[1] if len(version_line.split()) > 1 else "Unknown"
                print_info(f"Detected Homebrew PyTorch installation: {homebrew_pytorch_version}")
        except (subprocess.SubprocessError, FileNotFoundError):
            pass
    
    return {
        "system": system,
        "machine": machine,
        "python_version": python_version,
        "is_windows": is_windows,
        "is_macos": is_macos,
        "is_linux": is_linux,
        "is_arm": is_arm,
        "is_x86": is_x86,
        "in_venv": in_venv,
        "has_homebrew_pytorch": has_homebrew_pytorch,
        "homebrew_pytorch_version": homebrew_pytorch_version
    }

def detect_gpu():
    """Detect GPU and acceleration capabilities."""
    system_info = detect_system()
    
    # Check for CUDA
    has_cuda = False
    cuda_version = None
    if system_info["is_windows"]:
        cuda_path = os.environ.get('CUDA_PATH')
        if cuda_path and os.path.exists(cuda_path):
            has_cuda = True
            try:
                # Try to get CUDA version
                nvcc_output = subprocess.check_output([os.path.join(cuda_path, 'bin', 'nvcc'), '--version'], 
                                                     stderr=subprocess.STDOUT, 
                                                     universal_newlines=True)
                for line in nvcc_output.split('\n'):
                    if 'release' in line:
                        cuda_version = line.split('release')[-1].strip().split(',')[0].strip()
                        break
            except (subprocess.SubprocessError, FileNotFoundError):
                pass
    elif system_info["is_linux"]:
        cuda_paths = ['/usr/local/cuda', os.environ.get('CUDA_HOME')]
        for path in cuda_paths:
            if path and os.path.exists(path):
                has_cuda = True
                try:
                    # Try to get CUDA version
                    nvcc_output = subprocess.check_output([os.path.join(path, 'bin', 'nvcc'), '--version'], 
                                                         stderr=subprocess.STDOUT, 
                                                         universal_newlines=True)
                    for line in nvcc_output.split('\n'):
                        if 'release' in line:
                            cuda_version = line.split('release')[-1].strip().split(',')[0].strip()
                            break
                except (subprocess.SubprocessError, FileNotFoundError):
                    pass
                break
    
    # Check for ROCm (AMD)
    has_rocm = False
    rocm_version = None
    if system_info["is_linux"]:
        rocm_paths = ['/opt/rocm', os.environ.get('ROCM_HOME')]
        for path in rocm_paths:
            if path and os.path.exists(path):
                has_rocm = True
                try:
                    # Try to get ROCm version
                    with open(os.path.join(path, 'bin', '.rocmversion'), 'r') as f:
                        rocm_version = f.read().strip()
                except (FileNotFoundError, IOError):
                    try:
                        rocm_output = subprocess.check_output(['rocminfo'], 
                                                            stderr=subprocess.STDOUT, 
                                                            universal_newlines=True)
                        for line in rocm_output.split('\n'):
                            if 'Version' in line:
                                rocm_version = line.split(':')[-1].strip()
                                break
                    except (subprocess.SubprocessError, FileNotFoundError):
                        pass
                break
    
    # Check for MPS (Apple Silicon)
    has_mps = False
    if system_info["is_macos"] and system_info["is_arm"]:
        try:
            # Check if Metal is supported
            result = subprocess.run(
                ['system_profiler', 'SPDisplaysDataType'],
                capture_output=True,
                text=True
            )
            has_mps = 'Metal' in result.stdout
        except (subprocess.SubprocessError, FileNotFoundError):
            pass
    
    # Check for DirectML (Windows)
    has_directml = False
    if system_info["is_windows"]:
        try:
            # Check if DirectML package is installed
            import pkg_resources
            pkg_resources.get_distribution('torch-directml')
            has_directml = True
        except (ImportError, pkg_resources.DistributionNotFound):
            # Check if DirectML is available on the system
            try:
                import ctypes
                ctypes.WinDLL('DirectML.dll')
                has_directml = True
            except (ImportError, OSError):
                pass
    
    # Print GPU information
    if has_cuda:
        print_info(f"CUDA detected: {cuda_version or 'Unknown version'}")
    if has_rocm:
        print_info(f"ROCm detected: {rocm_version or 'Unknown version'}")
    if has_mps:
        print_info("Apple Metal Performance Shaders (MPS) detected")
    if has_directml:
        print_info("DirectML detected")
    
    if not (has_cuda or has_rocm or has_mps or has_directml):
        print_info("No GPU acceleration detected, will use CPU-only mode")
    
    return {
        "has_cuda": has_cuda,
        "cuda_version": cuda_version,
        "has_rocm": has_rocm,
        "rocm_version": rocm_version,
        "has_mps": has_mps,
        "has_directml": has_directml
    }

def check_dependencies():
    """Check for required dependencies.
    
    Note on package managers:
    - Traditional virtual environments (venv, virtualenv) include pip by default
    - Alternative package managers like uv may not include pip or may manage packages differently
    - We attempt multiple detection methods for pip and only fail if:
      a) We're not in a virtual environment, or
      b) We can't detect pip AND can't install dependencies
    
    We proceed with installation even if pip isn't detected when in a virtual environment,
    assuming an alternative package manager (like uv) is handling dependencies.
    
    Returns:
        bool: True if all dependencies are met, False otherwise.
    """
    print_step("2", "Checking dependencies")
    
    # Check for pip
    pip_installed = False
    
    # Try subprocess check first
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', '--version'], 
                             stdout=subprocess.DEVNULL, 
                             stderr=subprocess.DEVNULL)
        pip_installed = True
        print_info("pip is installed")
    except subprocess.SubprocessError:
        # Fallback to import check
        try:
            import pip
            pip_installed = True
            print_info(f"pip is installed: {pip.__version__}")
        except ImportError:
            # Check if we're in a virtual environment
            in_venv = sys.prefix != sys.base_prefix
            if in_venv:
                print_warning("pip could not be detected, but you're in a virtual environment. "
                            "If you're using uv or another alternative package manager, this is normal. "
                            "Continuing installation...")
                pip_installed = True  # Proceed anyway
            else:
                print_error("pip is not installed. Please install pip first.")
                return False
    
    # Check for setuptools
    try:
        import setuptools
        print_info(f"setuptools is installed: {setuptools.__version__}")
    except ImportError:
        print_warning("setuptools is not installed. Will attempt to install it.")
        # If pip is available, use it to install setuptools
        if pip_installed:
            try:
                subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'setuptools'], 
                                    stdout=subprocess.DEVNULL)
                print_success("setuptools installed successfully")
            except subprocess.SubprocessError:
                # Check if in virtual environment
                in_venv = sys.prefix != sys.base_prefix
                if in_venv:
                    print_warning("Failed to install setuptools with pip. If you're using an alternative package manager "
                                "like uv, please install setuptools manually using that tool (e.g., 'uv pip install setuptools').")
                else:
                    print_error("Failed to install setuptools. Please install it manually.")
                    return False
        else:
            # Should be unreachable since pip_installed would only be False if we returned earlier
            print_error("Cannot install setuptools without pip. Please install setuptools manually.")
            return False
    
    # Check for wheel
    try:
        import wheel
        print_info(f"wheel is installed: {wheel.__version__}")
    except ImportError:
        print_warning("wheel is not installed. Will attempt to install it.")
        # If pip is available, use it to install wheel
        if pip_installed:
            try:
                subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'wheel'], 
                                    stdout=subprocess.DEVNULL)
                print_success("wheel installed successfully")
            except subprocess.SubprocessError:
                # Check if in virtual environment
                in_venv = sys.prefix != sys.base_prefix
                if in_venv:
                    print_warning("Failed to install wheel with pip. If you're using an alternative package manager "
                                "like uv, please install wheel manually using that tool (e.g., 'uv pip install wheel').")
                else:
                    print_error("Failed to install wheel. Please install it manually.")
                    return False
        else:
            # Should be unreachable since pip_installed would only be False if we returned earlier
            print_error("Cannot install wheel without pip. Please install wheel manually.")
            return False
    
    return True

def install_pytorch_platform_specific(system_info, gpu_info):
    """Install PyTorch with platform-specific configurations."""
    if system_info["is_windows"]:
        return install_pytorch_windows(gpu_info)
    elif system_info["is_macos"] and system_info["is_x86"]:
        return install_pytorch_macos_intel()
    else:
        # For other platforms, let the regular installer handle it
        return True

def install_pytorch_macos_intel():
    """Install PyTorch specifically for macOS with Intel CPUs."""
    print_step("3a", "Installing PyTorch for macOS Intel CPU")
    
    # Use the versions known to work well on macOS Intel and with Python 3.13+
    try:
        # For Python 3.13+, we need newer PyTorch versions
        python_version = sys.version_info
        
        if python_version >= (3, 13):
            # For Python 3.13+, try to install latest compatible version
            print_info(f"Installing PyTorch for macOS Intel (Python {python_version.major}.{python_version.minor})...")
            print_info("Attempting to install latest PyTorch compatible with Python 3.13...")
            
            try:
                # Try to install without version specifiers to get latest compatible version
                cmd = [
                    sys.executable, '-m', 'pip', 'install',
                    "torch", "torchvision", "torchaudio"
                ]
                print_info(f"Running: {' '.join(cmd)}")
                subprocess.check_call(cmd)
                st_version = "3.0.0"  # Newer sentence-transformers for newer PyTorch
            except subprocess.SubprocessError as e:
                print_warning(f"Failed to install latest PyTorch: {e}")
                # Fallback to a specific version
                torch_version = "2.1.0"
                torch_vision_version = "0.16.0"
                torch_audio_version = "2.1.0"
                st_version = "3.0.0"
                
                print_info(f"Trying fallback to PyTorch {torch_version}...")
                
                cmd = [
                    sys.executable, '-m', 'pip', 'install',
                    f"torch=={torch_version}",
                    f"torchvision=={torch_vision_version}",
                    f"torchaudio=={torch_audio_version}"
                ]
                print_info(f"Running: {' '.join(cmd)}")
                subprocess.check_call(cmd)
        else:
            # Use traditional versions for older Python
            torch_version = "1.13.1"
            torch_vision_version = "0.14.1"
            torch_audio_version = "0.13.1"
            st_version = "2.2.2"
            
            print_info(f"Installing PyTorch {torch_version} for macOS Intel (Python {python_version.major}.{python_version.minor})...")
            
            # Install PyTorch first with compatible version
            cmd = [
                sys.executable, '-m', 'pip', 'install',
                f"torch=={torch_version}",
                f"torchvision=={torch_vision_version}",
                f"torchaudio=={torch_audio_version}"
            ]
            
            print_info(f"Running: {' '.join(cmd)}")
            subprocess.check_call(cmd)
        
        # Install a compatible version of sentence-transformers
        print_info(f"Installing sentence-transformers {st_version}...")
        
        cmd = [
            sys.executable, '-m', 'pip', 'install',
            f"sentence-transformers=={st_version}"
        ]
        
        print_info(f"Running: {' '.join(cmd)}")
        subprocess.check_call(cmd)
        
        print_success(f"PyTorch {torch_version} and sentence-transformers {st_version} installed successfully for macOS Intel")
        return True
    except subprocess.SubprocessError as e:
        print_error(f"Failed to install PyTorch for macOS Intel: {e}")
        
        # Provide fallback instructions
        if python_version >= (3, 13):
            print_warning("You may need to manually install compatible versions for Python 3.13+ on Intel macOS:")
            print_info("pip install torch==2.3.0 torchvision==0.18.0 torchaudio==2.3.0")
            print_info("pip install sentence-transformers==3.0.0")
        else:
            print_warning("You may need to manually install compatible versions for Intel macOS:")
            print_info("pip install torch==1.13.1 torchvision==0.14.1 torchaudio==0.13.1")
            print_info("pip install sentence-transformers==2.2.2")
        
        return False

def install_pytorch_windows(gpu_info):
    """Install PyTorch on Windows using the appropriate index URL."""
    print_step("3a", "Installing PyTorch for Windows")
    
    # Determine the appropriate PyTorch index URL based on GPU
    if gpu_info["has_cuda"]:
        # Get CUDA version and determine appropriate index URL
        cuda_version = gpu_info.get("cuda_version", "")
        
        # Extract major version from CUDA version string
        cuda_major = None
        if cuda_version:
            # Try to extract the major version (e.g., "11.8" -> "11")
            try:
                cuda_major = cuda_version.split('.')[0]
            except (IndexError, AttributeError):
                pass
        
        # Default to cu118 if we couldn't determine the version or it's not a common one
        if cuda_major == "12":
            cuda_suffix = "cu121"  # CUDA 12.x
            print_info(f"Detected CUDA {cuda_version}, using cu121 channel")
        elif cuda_major == "11":
            cuda_suffix = "cu118"  # CUDA 11.x
            print_info(f"Detected CUDA {cuda_version}, using cu118 channel")
        elif cuda_major == "10":
            cuda_suffix = "cu102"  # CUDA 10.x
            print_info(f"Detected CUDA {cuda_version}, using cu102 channel")
        else:
            # Default to cu118 as a safe choice for newer NVIDIA GPUs
            cuda_suffix = "cu118"
            print_info(f"Using default cu118 channel for CUDA {cuda_version}")
            
        index_url = f"https://download.pytorch.org/whl/{cuda_suffix}"
    else:
        # CPU-only version
        index_url = "https://download.pytorch.org/whl/cpu"
        print_info("Using CPU-only PyTorch for Windows")
    
    # Install PyTorch with the appropriate index URL
    try:
        # Use a stable version that's known to have Windows wheels
        torch_version = "2.1.0"  # This version has Windows wheels available
        
        cmd = [
            sys.executable, '-m', 'pip', 'install',
            f"torch=={torch_version}",
            f"torchvision=={torch_version}",
            f"torchaudio=={torch_version}",
            f"--index-url={index_url}"
        ]
        
        print_info(f"Running: {' '.join(cmd)}")
        subprocess.check_call(cmd)
        
        # Check if DirectML is needed
        if gpu_info["has_directml"]:
            print_info("Installing torch-directml for DirectML support")
            subprocess.check_call([
                sys.executable, '-m', 'pip', 'install', 'torch-directml>=0.2.0'
            ])
            
        print_success("PyTorch installed successfully for Windows")
        return True
    except subprocess.SubprocessError as e:
        print_error(f"Failed to install PyTorch for Windows: {e}")
        print_warning("You may need to manually install PyTorch using instructions from https://pytorch.org/get-started/locally/")
        return False

def detect_storage_backend_compatibility(system_info, gpu_info):
    """Detect which storage backends are compatible with the current environment."""
    print_step("3a", "Analyzing storage backend compatibility")
    
    compatibility = {
        "chromadb": {"supported": True, "issues": [], "recommendation": "default"},
        "sqlite_vec": {"supported": True, "issues": [], "recommendation": "lightweight"}
    }
    
    # Check ChromaDB compatibility issues
    chromadb_issues = []
    
    # macOS Intel compatibility issues
    if system_info["is_macos"] and system_info["is_x86"]:
        chromadb_issues.append("ChromaDB has known installation issues on older macOS Intel systems")
        chromadb_issues.append("May require specific dependency versions")
        compatibility["chromadb"]["recommendation"] = "problematic"
        compatibility["sqlite_vec"]["recommendation"] = "recommended"
    
    # Memory constraints
    total_memory_gb = 0
    try:
        import psutil
        total_memory_gb = psutil.virtual_memory().total / (1024**3)
    except ImportError:
        # Fallback memory detection
        try:
            with open('/proc/meminfo', 'r') as f:
                for line in f:
                    if line.startswith('MemTotal:'):
                        total_memory_gb = int(line.split()[1]) / (1024**2)
                        break
        except (FileNotFoundError, IOError):
            pass
    
    if total_memory_gb > 0 and total_memory_gb < 4:
        chromadb_issues.append(f"System has {total_memory_gb:.1f}GB RAM - ChromaDB may consume significant memory")
        compatibility["sqlite_vec"]["recommendation"] = "recommended"
    
    # Older Python versions
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
    if sys.version_info < (3, 9):
        chromadb_issues.append(f"Python {python_version} may have ChromaDB compatibility issues")
    
    # ARM architecture considerations
    if system_info["is_arm"]:
        print_info("ARM architecture detected - both backends should work well")
    
    compatibility["chromadb"]["issues"] = chromadb_issues
    
    # Print compatibility analysis
    print_info("Storage Backend Compatibility Analysis:")
    
    for backend, info in compatibility.items():
        status = "✅" if info["supported"] else "❌"
        rec_text = {
            "recommended": "🌟 RECOMMENDED",
            "default": "📦 Standard",
            "problematic": "⚠️  May have issues",
            "lightweight": "🪶 Lightweight"
        }.get(info["recommendation"], "")
        
        print_info(f"  {status} {backend.upper()}: {rec_text}")
        
        if info["issues"]:
            for issue in info["issues"]:
                print_info(f"    • {issue}")
    
    return compatibility

def choose_storage_backend(system_info, gpu_info, args):
    """Choose storage backend based on environment and user preferences."""
    compatibility = detect_storage_backend_compatibility(system_info, gpu_info)
    
    # Check if user specified a backend via environment
    env_backend = os.environ.get('MCP_MEMORY_STORAGE_BACKEND')
    if env_backend:
        print_info(f"Using storage backend from environment: {env_backend}")
        return env_backend
    
    # Check for command line argument (we'll add this)
    if hasattr(args, 'storage_backend') and args.storage_backend:
        print_info(f"Using storage backend from command line: {args.storage_backend}")
        return args.storage_backend
    
    # Auto-select based on compatibility
    recommended_backend = None
    for backend, info in compatibility.items():
        if info["recommendation"] == "recommended":
            recommended_backend = backend
            break
    
    if not recommended_backend:
        recommended_backend = "chromadb"  # Default fallback
    
    # Interactive selection if no auto-recommendation is clear
    if compatibility["chromadb"]["recommendation"] == "problematic":
        print_step("3b", "Storage Backend Selection")
        print_info("Based on your system, ChromaDB may have installation issues.")
        print_info("SQLite-vec is recommended as a lightweight, compatible alternative.")
        print_info("")
        print_info("Available options:")
        print_info("  1. SQLite-vec (Recommended) - Lightweight, fast, minimal dependencies")
        print_info("  2. ChromaDB (Standard) - Full-featured but may have issues on your system")
        print_info("  3. Auto-detect - Try ChromaDB first, fallback to SQLite-vec if it fails")
        print_info("")
        
        while True:
            try:
                choice = input("Choose storage backend [1-3] (default: 1): ").strip()
                if not choice:
                    choice = "1"
                
                if choice == "1":
                    return "sqlite_vec"
                elif choice == "2":
                    return "chromadb"
                elif choice == "3":
                    return "auto_detect"
                else:
                    print_error("Please enter 1, 2, or 3")
            except (EOFError, KeyboardInterrupt):
                print_info("\nUsing recommended backend: sqlite_vec")
                return "sqlite_vec"
    
    return recommended_backend

def install_storage_backend(backend, system_info):
    """Install the chosen storage backend."""
    print_step("3c", f"Installing {backend} storage backend")
    
    if backend == "sqlite_vec":
        try:
            print_info("Installing SQLite-vec...")
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'sqlite-vec'])
            print_success("SQLite-vec installed successfully")
            return True
        except subprocess.SubprocessError as e:
            print_error(f"Failed to install SQLite-vec: {e}")
            return False
            
    elif backend == "chromadb":
        try:
            print_info("Installing ChromaDB...")
            chromadb_version = "0.5.23"
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', f'chromadb=={chromadb_version}'])
            print_success(f"ChromaDB {chromadb_version} installed successfully")
            return True
        except subprocess.SubprocessError as e:
            print_error(f"Failed to install ChromaDB: {e}")
            print_info("This is a known issue on some systems (especially older macOS Intel)")
            return False
            
    elif backend == "auto_detect":
        print_info("Attempting auto-detection...")
        
        # Try ChromaDB first
        print_info("Trying ChromaDB installation...")
        if install_storage_backend("chromadb", system_info):
            print_success("ChromaDB installed successfully")
            return "chromadb"
        
        print_warning("ChromaDB installation failed, falling back to SQLite-vec...")
        if install_storage_backend("sqlite_vec", system_info):
            print_success("SQLite-vec installed successfully as fallback")
            return "sqlite_vec"
        
        print_error("Both storage backends failed to install")
        return False
    
    return False

def install_package(args):
    """Install the package with the appropriate dependencies, supporting pip or uv."""
    print_step("3", "Installing MCP Memory Service")

    # Determine installation mode
    install_mode = []
    if args.dev:
        install_mode = ['-e']
        print_info("Installing in development mode")

    # Set environment variables for installation
    env = os.environ.copy()

    # Detect if pip is available
    pip_available = False
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', '--version'],
                              stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL)
        pip_available = True
    except subprocess.SubprocessError:
        pip_available = False

    # Detect if uv is available
    uv_path = shutil.which("uv")
    uv_available = uv_path is not None

    # Decide installer command prefix
    if pip_available:
        installer_cmd = [sys.executable, '-m', 'pip']
    elif uv_available:
        installer_cmd = ['uv', 'pip']
        print_warning("pip not found, but uv detected. Using 'uv pip' for installation.")
    else:
        print_error("Neither pip nor uv detected. Cannot install packages.")
        return False

    # Get system and GPU info
    system_info = detect_system()
    gpu_info = detect_gpu()

    # Choose and install storage backend
    chosen_backend = choose_storage_backend(system_info, gpu_info, args)
    if chosen_backend == "auto_detect":
        # Handle auto-detection case
        actual_backend = install_storage_backend(chosen_backend, system_info)
        if not actual_backend:
            print_error("Failed to install any storage backend")
            return False
        chosen_backend = actual_backend
    else:
        # Install the chosen backend
        if not install_storage_backend(chosen_backend, system_info):
            print_error(f"Failed to install {chosen_backend} storage backend")
            return False

    # Set environment variable for chosen backend
    if chosen_backend == "sqlite_vec":
        env['MCP_MEMORY_STORAGE_BACKEND'] = 'sqlite_vec'
        print_info("Configured to use SQLite-vec storage backend")
    else:
        env['MCP_MEMORY_STORAGE_BACKEND'] = 'chromadb'
        print_info("Configured to use ChromaDB storage backend")

    # Set environment variables based on detected GPU
    if gpu_info.get("has_cuda"):
        print_info("Configuring for CUDA installation")
    elif gpu_info.get("has_rocm"):
        print_info("Configuring for ROCm installation")
        env['MCP_MEMORY_USE_ROCM'] = '1'
    elif gpu_info.get("has_mps"):
        print_info("Configuring for Apple Silicon MPS installation")
        env['PYTORCH_ENABLE_MPS_FALLBACK'] = '1'
    elif gpu_info.get("has_directml"):
        print_info("Configuring for DirectML installation")
        env['MCP_MEMORY_USE_DIRECTML'] = '1'
    else:
        print_info("Configuring for CPU-only installation")
        env['MCP_MEMORY_USE_ONNX'] = '1'

    # Check for Homebrew PyTorch installation
    using_homebrew_pytorch = False
    if system_info.get("has_homebrew_pytorch"):
        print_info(f"Using existing Homebrew PyTorch installation (version: {system_info.get('homebrew_pytorch_version')})")
        using_homebrew_pytorch = True
        # Set the environment variable to use ONNX for embeddings
        env['MCP_MEMORY_USE_ONNX'] = '1'
        # Skip the PyTorch installation step
        pytorch_installed = True
    else:
        # Handle platform-specific PyTorch installation
        pytorch_installed = install_pytorch_platform_specific(system_info, gpu_info)
        if not pytorch_installed:
            print_warning("Platform-specific PyTorch installation failed, but will continue with package installation")

    try:
        # SQLite-vec with ONNX for macOS with homebrew PyTorch or compatibility issues
        if (system_info["is_macos"] and system_info["is_x86"] and 
            (sys.version_info >= (3, 13) or using_homebrew_pytorch or args.skip_pytorch)):
            
            if using_homebrew_pytorch:
                print_info("Using Homebrew PyTorch - installing with SQLite-vec + ONNX configuration")
            elif args.skip_pytorch:
                print_info("Skipping PyTorch installation - using SQLite-vec + ONNX configuration")
            else:
                print_info("Using Python 3.13+ on macOS Intel - using SQLite-vec + ONNX configuration")
            
            # First try to install without ML dependencies
            try:
                cmd = installer_cmd + ['install', '--no-deps'] + install_mode + ['.']
                print_info(f"Running: {' '.join(cmd)}")
                subprocess.check_call(cmd, env=env)
                
                # Install core dependencies except torch/sentence-transformers
                print_info("Installing core dependencies except ML libraries...")
                
                # Create a list of dependencies to install
                dependencies = [
                    "mcp>=1.0.0,<2.0.0",
                    "onnxruntime>=1.14.1"  # ONNX runtime is required
                ]
                
                # Add backend-specific dependencies
                if chosen_backend == "sqlite_vec":
                    dependencies.append("sqlite-vec>=0.1.0")
                else:
                    dependencies.append("chromadb==0.5.23")
                    dependencies.append("tokenizers==0.20.3")
                
                # Install dependencies
                subprocess.check_call(
                    [sys.executable, '-m', 'pip', 'install'] + dependencies
                )
                
                # Set environment variables for ONNX
                print_info("Configuring to use ONNX runtime for inference without PyTorch...")
                env['MCP_MEMORY_USE_ONNX'] = '1'
                if chosen_backend != "sqlite_vec":
                    print_info("Switching to SQLite-vec backend for better compatibility")
                    env['MCP_MEMORY_STORAGE_BACKEND'] = 'sqlite_vec'
                
                print_success("MCP Memory Service installed successfully (SQLite-vec + ONNX)")
                
                if using_homebrew_pytorch:
                    print_info("Using Homebrew PyTorch installation for embedding generation")
                    print_info("Environment configured to use SQLite-vec backend and ONNX runtime")
                else:
                    print_warning("ML libraries (PyTorch/sentence-transformers) were not installed due to compatibility issues")
                    print_info("The service will use ONNX runtime for inference instead")
                
                return True
            except subprocess.SubprocessError as e:
                print_error(f"Failed to install with ONNX approach: {e}")
                # Fall through to try standard installation
        
        # Standard installation
        cmd = installer_cmd + ['install'] + install_mode + ['.']
        print_info(f"Running: {' '.join(cmd)}")
        subprocess.check_call(cmd, env=env)
        print_success("MCP Memory Service installed successfully")
        return True
    except subprocess.SubprocessError as e:
        print_error(f"Failed to install MCP Memory Service: {e}")
        
        # Special handling for macOS with compatibility issues
        if system_info["is_macos"] and system_info["is_x86"]:
            print_warning("Installation on macOS Intel is challenging")
            print_info("Try manually installing with:")
            print_info("1. pip install --no-deps .")
            print_info("2. pip install sqlite-vec>=0.1.0 mcp>=1.0.0,<2.0.0 onnxruntime>=1.14.1")
            print_info("3. export MCP_MEMORY_USE_ONNX=1")
            print_info("4. export MCP_MEMORY_STORAGE_BACKEND=sqlite_vec")
            
            if system_info.get("has_homebrew_pytorch"):
                print_info("Homebrew PyTorch was detected but installation still failed.")
                print_info("Try running: python install.py --storage-backend sqlite_vec --skip-pytorch")
            
        return False

def configure_paths(args):
    """Configure paths for the MCP Memory Service."""
    print_step("4", "Configuring paths")
    
    # Get system info
    system_info = detect_system()
    
    # Determine home directory
    home_dir = Path.home()
    
    # Determine base directory based on platform
    if platform.system() == 'Darwin':  # macOS
        base_dir = home_dir / 'Library' / 'Application Support' / 'mcp-memory'
    elif platform.system() == 'Windows':  # Windows
        base_dir = Path(os.environ.get('LOCALAPPDATA', '')) / 'mcp-memory'
    else:  # Linux and others
        base_dir = home_dir / '.local' / 'share' / 'mcp-memory'
    
    # Create directories based on storage backend
    storage_backend = os.environ.get('MCP_MEMORY_STORAGE_BACKEND', 'chromadb')
    
    if storage_backend == 'sqlite_vec':
        # For sqlite-vec, we need a database file path
        storage_path = args.chroma_path or (base_dir / 'sqlite_vec.db')
        storage_dir = storage_path.parent if storage_path.name.endswith('.db') else storage_path
        backups_path = args.backups_path or (base_dir / 'backups')
        
        try:
            os.makedirs(storage_dir, exist_ok=True)
            os.makedirs(backups_path, exist_ok=True)
            print_info(f"SQLite-vec database: {storage_path}")
            print_info(f"Backups path: {backups_path}")
            
            # Test if directory is writable
            test_file = os.path.join(storage_dir, '.write_test')
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
        except Exception as e:
            print_error(f"Failed to configure SQLite-vec paths: {e}")
            return False
    else:
        # ChromaDB configuration
        chroma_path = args.chroma_path or (base_dir / 'chroma_db')
        backups_path = args.backups_path or (base_dir / 'backups')
        storage_path = chroma_path
        
        try:
            os.makedirs(chroma_path, exist_ok=True)
            os.makedirs(backups_path, exist_ok=True)
            print_info(f"ChromaDB path: {chroma_path}")
            print_info(f"Backups path: {backups_path}")
            
            # Test if directories are writable
            test_file = os.path.join(chroma_path, '.write_test')
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
        except Exception as e:
            print_error(f"Failed to configure ChromaDB paths: {e}")
            return False
    
    # Test backups directory for both backends
    try:
        test_file = os.path.join(backups_path, '.write_test')
        with open(test_file, 'w') as f:
            f.write('test')
        os.remove(test_file)
        print_success("Storage directories created and are writable")
    except Exception as e:
        print_error(f"Failed to test backups directory: {e}")
        return False
        
        # Configure Claude Desktop if available
        claude_config_paths = [
            home_dir / 'Library' / 'Application Support' / 'Claude' / 'claude_desktop_config.json',
            home_dir / '.config' / 'Claude' / 'claude_desktop_config.json',
            Path('claude_config') / 'claude_desktop_config.json'
        ]
        
        for config_path in claude_config_paths:
            if config_path.exists():
                print_info(f"Found Claude Desktop config at {config_path}")
                try:
                    import json
                    with open(config_path, 'r') as f:
                        config = json.load(f)
                    
                    # Update or add MCP Memory configuration
                    if 'mcpServers' not in config:
                        config['mcpServers'] = {}
                    
                    # Create environment configuration based on storage backend
                    env_config = {
                        "MCP_MEMORY_BACKUPS_PATH": str(backups_path),
                        "MCP_MEMORY_STORAGE_BACKEND": storage_backend
                    }
                    
                    if storage_backend == 'sqlite_vec':
                        env_config["MCP_MEMORY_SQLITE_PATH"] = str(storage_path)
                    else:
                        env_config["MCP_MEMORY_CHROMA_PATH"] = str(storage_path)
                    
                    # Create or update the memory server configuration
                    if system_info["is_windows"]:
                        # Use the memory_wrapper.py script for Windows
                        script_path = os.path.abspath("memory_wrapper.py")
                        config['mcpServers']['memory'] = {
                            "command": "python",
                            "args": [script_path],
                            "env": env_config
                        }
                        print_info("Configured Claude Desktop to use memory_wrapper.py for Windows")
                    else:
                        # Use the standard configuration for other platforms
                        config['mcpServers']['memory'] = {
                            "command": "uv",
                            "args": [
                                "--directory",
                                os.path.abspath("."),
                                "run",
                                "memory"
                            ],
                            "env": env_config
                        }
                    
                    with open(config_path, 'w') as f:
                        json.dump(config, f, indent=2)
                    
                    print_success("Updated Claude Desktop configuration")
                except Exception as e:
                    print_warning(f"Failed to update Claude Desktop configuration: {e}")
                break
        
        return True
    except Exception as e:
        print_error(f"Failed to configure paths: {e}")
        return False

def verify_installation():
    """Verify the installation."""
    print_step("5", "Verifying installation")
    
    # Get system info
    system_info = detect_system()
    
    # Check if the package is installed
    try:
        import mcp_memory_service
        print_success(f"MCP Memory Service is installed: {mcp_memory_service.__file__}")
    except ImportError:
        print_error("MCP Memory Service is not installed correctly")
        return False
    
    # Check if the entry point is available
    memory_script = shutil.which('memory')
    if memory_script:
        print_success(f"Memory command is available: {memory_script}")
    else:
        print_warning("Memory command is not available in PATH")
    
    # Check storage backend installation
    storage_backend = os.environ.get('MCP_MEMORY_STORAGE_BACKEND', 'sqlite_vec')
    
    if storage_backend == 'sqlite_vec':
        try:
            import sqlite_vec
            print_success(f"SQLite-vec is installed: {sqlite_vec.__version__}")
        except ImportError:
            print_error("SQLite-vec is not installed correctly")
            return False
    elif storage_backend == 'chromadb':
        try:
            import chromadb
            print_success(f"ChromaDB is installed: {chromadb.__version__}")
        except ImportError:
            print_error("ChromaDB is not installed correctly")
            return False
    
    # Check for ONNX runtime
    try:
        import onnxruntime
        print_success(f"ONNX Runtime is installed: {onnxruntime.__version__}")
        use_onnx = os.environ.get('MCP_MEMORY_USE_ONNX', '').lower() in ('1', 'true', 'yes')
        if use_onnx:
            print_info("Environment configured to use ONNX runtime for inference")
    except ImportError:
        print_warning("ONNX Runtime is not installed. This is recommended for CPU-only operation.")
        print_info("Install with: pip install onnxruntime>=1.14.1")
    
    # Check for Homebrew PyTorch
    homebrew_pytorch = False
    if system_info.get("has_homebrew_pytorch"):
        homebrew_pytorch = True
        print_success(f"Homebrew PyTorch detected: {system_info.get('homebrew_pytorch_version')}")
        print_info("Using system-installed PyTorch instead of pip version")
    
    # Check ML dependencies as optional
    pytorch_installed = False
    try:
        import torch
        pytorch_installed = True
        print_info(f"PyTorch is installed: {torch.__version__}")
        
        # Check for CUDA
        if torch.cuda.is_available():
            print_success(f"CUDA is available: {torch.version.cuda}")
            print_info(f"GPU: {torch.cuda.get_device_name(0)}")
        # Check for MPS (Apple Silicon)
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            print_success("MPS (Metal Performance Shaders) is available")
        # Check for DirectML
        else:
            try:
                import torch_directml
                print_success(f"DirectML is available: {torch_directml.__version__}")
            except ImportError:
                print_info("Using CPU-only PyTorch")
        
        # For macOS Intel, verify compatibility with sentence-transformers
        if system_info["is_macos"] and system_info["is_x86"]:
            torch_version = torch.__version__.split('.')
            major, minor = int(torch_version[0]), int(torch_version[1])
            
            print_info(f"Verifying torch compatibility on macOS Intel (v{major}.{minor})")
            if major < 1 or (major == 1 and minor < 6):
                print_warning(f"PyTorch version {torch.__version__} may be too old for sentence-transformers")
            elif major > 2 or (major == 2 and minor > 1):
                print_warning(f"PyTorch version {torch.__version__} may be too new for sentence-transformers 2.2.2")
                print_info("If you encounter issues, try downgrading to torch 2.0.1")
            
    except ImportError:
        print_warning("PyTorch is not installed via pip. This is okay for basic operation with SQLite-vec backend.")
        if homebrew_pytorch:
            print_info("Using Homebrew PyTorch installation instead of pip version")
        else:
            print_info("For full functionality including embedding generation, install with: pip install 'mcp-memory-service[ml]'")
        pytorch_installed = False
    
    # Check if sentence-transformers is installed correctly (only if PyTorch is installed)
    if pytorch_installed or homebrew_pytorch:
        try:
            import sentence_transformers
            print_success(f"sentence-transformers is installed: {sentence_transformers.__version__}")
            
            if pytorch_installed:
                # Verify compatibility between torch and sentence-transformers
                st_version = sentence_transformers.__version__.split('.')
                torch_version = torch.__version__.split('.')
                
                st_major, st_minor = int(st_version[0]), int(st_version[1])
                torch_major, torch_minor = int(torch_version[0]), int(torch_version[1])
                
                # Specific compatibility check for macOS Intel
                if system_info["is_macos"] and system_info["is_x86"]:
                    if st_major >= 3 and (torch_major < 1 or (torch_major == 1 and torch_minor < 11)):
                        print_warning(f"sentence-transformers {sentence_transformers.__version__} requires torch>=1.11.0")
                        print_info("This may cause runtime issues - consider downgrading sentence-transformers to 2.2.2")
            
            # Verify by trying to load a model (minimal test)
            try:
                print_info("Testing sentence-transformers model loading...")
                test_model = sentence_transformers.SentenceTransformer('paraphrase-MiniLM-L3-v2')
                print_success("Successfully loaded test model")
            except Exception as e:
                print_warning(f"Model loading test failed: {e}")
                print_warning("There may be compatibility issues between PyTorch and sentence-transformers")
                
        except ImportError:
            print_warning("sentence-transformers is not installed. This is okay for basic operation with SQLite-vec backend.")
            print_info("For full functionality including embedding generation, install with: pip install 'mcp-memory-service[ml]'")
    
    # Check for SQLite-vec + ONNX configuration
    if storage_backend == 'sqlite_vec' and os.environ.get('MCP_MEMORY_USE_ONNX', '').lower() in ('1', 'true', 'yes'):
        print_success("SQLite-vec + ONNX configuration is set up correctly")
        print_info("This configuration can run without PyTorch dependency")
        
        try:
            # Import the key components to verify installation
            from mcp_memory_service.storage.sqlite_vec import SqliteVecMemoryStorage
            from mcp_memory_service.models.memory import Memory
            print_success("SQLite-vec + ONNX components loaded successfully")
            
            # Check paths
            sqlite_path = os.environ.get('MCP_MEMORY_SQLITE_PATH', '')
            if sqlite_path:
                print_info(f"SQLite-vec database path: {sqlite_path}")
            else:
                print_warning("MCP_MEMORY_SQLITE_PATH is not set")
            
            backups_path = os.environ.get('MCP_MEMORY_BACKUPS_PATH', '')
            if backups_path:
                print_info(f"Backups path: {backups_path}")
            else:
                print_warning("MCP_MEMORY_BACKUPS_PATH is not set")
            
        except ImportError as e:
            print_error(f"Failed to import SQLite-vec components: {e}")
            return False
            
    # Check if MCP Memory Service package is installed correctly
    try:
        import mcp_memory_service
        print_success(f"MCP Memory Service is installed correctly")
        return True
    except ImportError:
        print_error("MCP Memory Service is not installed correctly")
        return False

def main():
    """Main installation function."""
    parser = argparse.ArgumentParser(description="Install MCP Memory Service")
    parser.add_argument('--dev', action='store_true', help='Install in development mode')
    parser.add_argument('--chroma-path', type=str, help='Path to ChromaDB storage')
    parser.add_argument('--backups-path', type=str, help='Path to backups storage')
    parser.add_argument('--force-compatible-deps', action='store_true', 
                        help='Force compatible versions of PyTorch (2.0.1) and sentence-transformers (2.2.2)')
    parser.add_argument('--fallback-deps', action='store_true',
                        help='Use fallback versions of PyTorch (1.13.1) and sentence-transformers (2.2.2)')
    parser.add_argument('--storage-backend', choices=['chromadb', 'sqlite_vec', 'auto_detect'],
                        help='Choose storage backend: chromadb (default), sqlite_vec (lightweight), or auto_detect (try chromadb, fallback to sqlite_vec)')
    parser.add_argument('--skip-pytorch', action='store_true',
                        help='Skip PyTorch installation and use ONNX runtime with SQLite-vec backend instead')
    parser.add_argument('--use-homebrew-pytorch', action='store_true',
                        help='Use existing Homebrew PyTorch installation instead of pip version')
    args = parser.parse_args()
    
    print_header("MCP Memory Service Installation")
    
    # Step 1: Detect system
    print_step("1", "Detecting system")
    system_info = detect_system()
    
    # Check if user requested force-compatible dependencies for macOS Intel
    if args.force_compatible_deps:
        if system_info["is_macos"] and system_info["is_x86"]:
            print_info("Installing compatible dependencies as requested...")
            # Select versions based on Python version
            python_version = sys.version_info
            if python_version >= (3, 13):
                # Python 3.13+ compatible versions
                torch_version = "2.3.0"
                torch_vision_version = "0.18.0"
                torch_audio_version = "2.3.0"
                st_version = "3.0.0"
            else:
                # Older Python versions
                torch_version = "2.0.1"
                torch_vision_version = "2.0.1"
                torch_audio_version = "2.0.1"
                st_version = "2.2.2"
                
            try:
                subprocess.check_call([
                    sys.executable, '-m', 'pip', 'install',
                    f"torch=={torch_version}", f"torchvision=={torch_vision_version}", f"torchaudio=={torch_audio_version}",
                    f"sentence-transformers=={st_version}"
                ])
                print_success("Compatible dependencies installed successfully")
            except subprocess.SubprocessError as e:
                print_error(f"Failed to install compatible dependencies: {e}")
        else:
            print_warning("--force-compatible-deps is only applicable for macOS with Intel CPUs")
    
    # Check if user requested fallback dependencies for troubleshooting
    if args.fallback_deps:
        print_info("Installing fallback dependencies as requested...")
        # Select versions based on Python version
        python_version = sys.version_info
        if python_version >= (3, 13):
            # Python 3.13+ compatible fallback versions
            torch_version = "2.3.0"
            torch_vision_version = "0.18.0"
            torch_audio_version = "2.3.0"
            st_version = "3.0.0"
        else:
            # Older Python fallback versions
            torch_version = "1.13.1"
            torch_vision_version = "0.14.1"
            torch_audio_version = "0.13.1"
            st_version = "2.2.2"
            
        try:
            subprocess.check_call([
                sys.executable, '-m', 'pip', 'install',
                f"torch=={torch_version}", f"torchvision=={torch_vision_version}", f"torchaudio=={torch_audio_version}",
                f"sentence-transformers=={st_version}"
            ])
            print_success("Fallback dependencies installed successfully")
        except subprocess.SubprocessError as e:
            print_error(f"Failed to install fallback dependencies: {e}")
    
    # Step 2: Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Step 3: Install package
    if not install_package(args):
        # If installation fails and we're on macOS Intel, suggest using the force-compatible-deps option
        if system_info["is_macos"] and system_info["is_x86"]:
            print_warning("Installation failed on macOS Intel.")
            print_info("Try running the script with '--force-compatible-deps' to force compatible versions:")
            print_info("python install.py --force-compatible-deps")
        sys.exit(1)
    
    # Step 4: Configure paths
    if not configure_paths(args):
        print_warning("Path configuration failed, but installation may still work")
    
    # Step 5: Verify installation
    if not verify_installation():
        print_warning("Installation verification failed, but installation may still work")
        # If verification fails and we're on macOS Intel, suggest using the force-compatible-deps option
        if system_info["is_macos"] and system_info["is_x86"]:
            python_version = sys.version_info
            print_info("For macOS Intel compatibility issues, try these steps:")
            print_info("1. First uninstall current packages: pip uninstall -y torch torchvision torchaudio sentence-transformers")
            print_info("2. Then reinstall with compatible versions: python install.py --force-compatible-deps")
            
            if python_version >= (3, 13):
                print_info("For Python 3.13+, you may need to manually install the following:")
                print_info("pip install torch==2.3.0 torchvision==0.18.0 torchaudio==2.3.0")
                print_info("pip install sentence-transformers==3.0.0")
    
    print_header("Installation Complete")
    
    # Get final storage backend info
    final_backend = os.environ.get('MCP_MEMORY_STORAGE_BACKEND', 'chromadb')
    use_onnx = os.environ.get('MCP_MEMORY_USE_ONNX', '').lower() in ('1', 'true', 'yes')
    
    print_info("You can now run the MCP Memory Service using the 'memory' command")
    print_info(f"Storage Backend: {final_backend.upper()}")
    
    if final_backend == 'sqlite_vec':
        print_info("✅ Using SQLite-vec - lightweight, fast, minimal dependencies")
        print_info("   • No complex dependencies or build issues")
        print_info("   • Excellent performance for typical use cases")
    else:
        print_info("✅ Using ChromaDB - full-featured vector database")
        print_info("   • Advanced features and extensive ecosystem")
    
    if use_onnx:
        print_info("✅ Using ONNX Runtime for inference")
        print_info("   • Compatible with Homebrew PyTorch")
        print_info("   • Reduced dependencies for better compatibility")
    
    print_info("For more information, see the README.md file")
    
    # Print macOS Intel specific information if applicable
    if system_info["is_macos"] and system_info["is_x86"]:
        print_info("\nMacOS Intel Notes:")
        
        if system_info.get("has_homebrew_pytorch"):
            print_info("- Using Homebrew PyTorch installation: " + system_info.get("homebrew_pytorch_version", "Unknown"))
            print_info("- The MCP Memory Service is configured to use SQLite-vec + ONNX runtime")
            print_info("- To start the memory service, use:")
            print_info("  export MCP_MEMORY_USE_ONNX=1")
            print_info("  export MCP_MEMORY_STORAGE_BACKEND=sqlite_vec")
            print_info("  memory")
        else:
            print_info("- If you encounter issues, try the --force-compatible-deps option")
            
            python_version = sys.version_info
            if python_version >= (3, 13):
                print_info("- For optimal performance on Intel Macs with Python 3.13+, torch==2.3.0 and sentence-transformers==3.0.0 are recommended")
                print_info("- You can manually install these versions with:")
                print_info("  pip install torch==2.3.0 torchvision==0.18.0 torchaudio==2.3.0 sentence-transformers==3.0.0")
            else:
                print_info("- For optimal performance on Intel Macs, torch==2.0.1 and sentence-transformers==2.2.2 are recommended")
                print_info("- You can manually install these versions with:")
                print_info("  pip install torch==2.0.1 torchvision==2.0.1 torchaudio==2.0.1 sentence-transformers==2.2.2")
                
        print_info("\nTroubleshooting Tips:")
        print_info("- If you have a Homebrew PyTorch installation, use: --use-homebrew-pytorch")
        print_info("- To completely skip PyTorch installation, use: --skip-pytorch")
        print_info("- To force the SQLite-vec backend, use: --storage-backend sqlite_vec")
        print_info("- For a quick test, try running: python test_memory.py")

if __name__ == "__main__":
    main()