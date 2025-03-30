#!/usr/bin/env python3
"""
Script to install UV package manager
"""
import os
import sys
import subprocess
import platform

def main():
    print("Installing UV package manager...")
    
    try:
        # Install UV using pip
        subprocess.check_call([
            sys.executable, '-m', 'pip', 'install', 'uv'
        ])
        
        print("UV installed successfully!")
        print("You can now use UV for faster dependency management:")
        print("  uv pip install -r requirements.txt")
        
        # Create shortcut script
        system = platform.system().lower()
        if system == "windows":
            # Create .bat file for Windows
            with open("uv-run.bat", "w") as f:
                f.write(f"@echo off\n")
                f.write(f"python -m uv run memory %*\n")
            print("Created uv-run.bat shortcut")
        else:
            # Create shell script for Unix-like systems
            with open("uv-run.sh", "w") as f:
                f.write("#!/bin/sh\n")
                f.write("python -m uv run memory \"$@\"\n")
            
            # Make it executable
            try:
                os.chmod("uv-run.sh", 0o755)
            except:
                pass
            print("Created uv-run.sh shortcut")
        
    except subprocess.SubprocessError as e:
        print(f"Error installing UV: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
