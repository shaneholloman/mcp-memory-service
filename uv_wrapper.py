#!/usr/bin/env python3
"""
UV Wrapper for MCP Memory Service
"""
import os
import sys
import subprocess
import platform
import argparse

def parse_args():
    parser = argparse.ArgumentParser(description="UV Wrapper for MCP Memory Service")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--chroma-path", type=str, help="Path to ChromaDB storage")
    parser.add_argument("--backups-path", type=str, help="Path to backups storage")
    return parser.parse_args()

def main():
    args = parse_args()
    
    # Check if UV is installed
    try:
        subprocess.check_call([sys.executable, '-m', 'uv', '--version'], 
                             stdout=subprocess.DEVNULL, 
                             stderr=subprocess.DEVNULL)
    except subprocess.SubprocessError:
        print("UV is not installed. Installing UV...")
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'uv'])
            print("UV installed successfully")
        except subprocess.SubprocessError as e:
            print(f"Failed to install UV: {e}")
            print("Please install UV manually: pip install uv")
            sys.exit(1)
    
    # Set environment variables
    env = os.environ.copy()
    env['UV_ACTIVE'] = '1'
    
    if args.debug:
        env['LOG_LEVEL'] = 'DEBUG'
        
    if args.chroma_path:
        env['MCP_MEMORY_CHROMA_PATH'] = args.chroma_path
        
    if args.backups_path:
        env['MCP_MEMORY_BACKUPS_PATH'] = args.backups_path
    
    # Run the memory service with UV
    uv_cmd = [sys.executable, '-m', 'uv', 'run', 'memory']
    
    if args.debug:
        uv_cmd.append('--debug')
    
    try:
        subprocess.run(uv_cmd, env=env)
    except KeyboardInterrupt:
        print("Memory service interrupted")
    except Exception as e:
        print(f"Error running memory service: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
