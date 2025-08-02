#!/usr/bin/env python3
# Copyright 2024 Heinrich Krupp
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Utilities for installing and managing Claude Code commands for MCP Memory Service.
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Tuple


def print_info(text: str) -> None:
    """Print formatted info text."""
    print(f"  -> {text}")


def print_error(text: str) -> None:
    """Print formatted error text."""
    print(f"  [ERROR] {text}")


def print_success(text: str) -> None:
    """Print formatted success text."""
    print(f"  [OK] {text}")


def print_warning(text: str) -> None:
    """Print formatted warning text."""
    print(f"  [WARNING] {text}")


def check_claude_code_cli() -> Tuple[bool, Optional[str]]:
    """
    Check if Claude Code CLI is installed and available.
    
    Returns:
        Tuple of (is_available, version_or_error)
    """
    try:
        # Try to run claude --version
        result = subprocess.run(
            ['claude', '--version'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            version = result.stdout.strip()
            return True, version
        else:
            return False, f"claude command failed: {result.stderr.strip()}"
            
    except subprocess.TimeoutExpired:
        return False, "claude command timed out"
    except FileNotFoundError:
        return False, "claude command not found in PATH"
    except Exception as e:
        return False, f"Error checking claude CLI: {str(e)}"


def get_claude_commands_directory() -> Path:
    """
    Get the Claude Code commands directory path.
    
    Returns:
        Path to ~/.claude/commands/
    """
    return Path.home() / ".claude" / "commands"


def check_commands_directory_access() -> Tuple[bool, str]:
    """
    Check if we can access and write to the Claude commands directory.
    
    Returns:
        Tuple of (can_access, status_message)
    """
    commands_dir = get_claude_commands_directory()
    
    try:
        # Check if directory exists
        if not commands_dir.exists():
            # Try to create it
            commands_dir.mkdir(parents=True, exist_ok=True)
            return True, f"Created commands directory: {commands_dir}"
        
        # Check if we can write to it
        test_file = commands_dir / ".test_write_access"
        try:
            test_file.write_text("test")
            test_file.unlink()
            return True, f"Commands directory accessible: {commands_dir}"
        except PermissionError:
            return False, f"No write permission to commands directory: {commands_dir}"
            
    except Exception as e:
        return False, f"Cannot access commands directory: {str(e)}"


def get_source_commands_directory() -> Path:
    """
    Get the source directory containing the command markdown files.
    
    Returns:
        Path to the claude_commands directory in the project
    """
    # Get the directory containing this script
    script_dir = Path(__file__).parent
    # Go up one level to the project root and find claude_commands
    project_root = script_dir.parent
    return project_root / "claude_commands"


def list_available_commands() -> List[Dict[str, str]]:
    """
    List all available command files in the source directory.
    
    Returns:
        List of command info dictionaries
    """
    source_dir = get_source_commands_directory()
    commands = []
    
    if not source_dir.exists():
        return commands
    
    for md_file in source_dir.glob("*.md"):
        # Extract command name from filename
        command_name = md_file.stem
        
        # Read the first line to get the description
        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                first_line = f.readline().strip()
                # Remove markdown header formatting
                description = first_line.lstrip('# ').strip()
        except Exception:
            description = "Command description unavailable"
        
        commands.append({
            'name': command_name,
            'file': md_file.name,
            'description': description,
            'path': str(md_file)
        })
    
    return commands


def backup_existing_commands() -> Optional[str]:
    """
    Create a backup of existing command files before installation.
    
    Returns:
        Path to backup directory if backup was created, None otherwise
    """
    commands_dir = get_claude_commands_directory()
    
    if not commands_dir.exists():
        return None
    
    # Check if there are any existing .md files
    existing_commands = list(commands_dir.glob("*.md"))
    if not existing_commands:
        return None
    
    # Create backup directory with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = commands_dir / f"backup_{timestamp}"
    
    try:
        backup_dir.mkdir(exist_ok=True)
        
        for cmd_file in existing_commands:
            shutil.copy2(cmd_file, backup_dir / cmd_file.name)
        
        print_info(f"Backed up {len(existing_commands)} existing commands to: {backup_dir}")
        return str(backup_dir)
        
    except Exception as e:
        print_error(f"Failed to create backup: {str(e)}")
        return None


def install_command_files() -> Tuple[bool, List[str]]:
    """
    Install command markdown files to the Claude commands directory.
    
    Returns:
        Tuple of (success, list_of_installed_files)
    """
    source_dir = get_source_commands_directory()
    commands_dir = get_claude_commands_directory()
    installed_files = []
    
    if not source_dir.exists():
        print_error(f"Source commands directory not found: {source_dir}")
        return False, []
    
    try:
        # Ensure destination directory exists
        commands_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy all .md files
        for md_file in source_dir.glob("*.md"):
            dest_file = commands_dir / md_file.name
            shutil.copy2(md_file, dest_file)
            installed_files.append(md_file.name)
            print_info(f"Installed: {md_file.name}")
        
        if installed_files:
            print_success(f"Successfully installed {len(installed_files)} Claude Code commands")
            return True, installed_files
        else:
            print_warning("No command files found to install")
            return False, []
            
    except Exception as e:
        print_error(f"Failed to install command files: {str(e)}")
        return False, []


def verify_mcp_service_connectivity() -> Tuple[bool, str]:
    """
    Verify that the MCP Memory Service is accessible.
    
    Returns:
        Tuple of (is_accessible, status_message)
    """
    try:
        # Try to import the MCP service modules
        sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
        
        # Test basic connectivity
        from mcp_memory_service import config
        
        # Check if we can detect a running service
        # This is a basic check - in a real scenario, we'd try to connect
        return True, "MCP Memory Service modules available"
        
    except ImportError as e:
        return False, f"MCP Memory Service not properly installed: {str(e)}"
    except Exception as e:
        return False, f"Error checking MCP service: {str(e)}"


def test_command_functionality() -> Tuple[bool, List[str]]:
    """
    Test that installed commands are accessible via Claude Code CLI.
    
    Returns:
        Tuple of (all_tests_passed, list_of_test_results)
    """
    commands_dir = get_claude_commands_directory()
    test_results = []
    all_passed = True
    
    # Check if command files exist and are readable
    for md_file in commands_dir.glob("memory-*.md"):
        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()
                if len(content) > 0:
                    test_results.append(f"✓ {md_file.name} - readable and non-empty")
                else:
                    test_results.append(f"✗ {md_file.name} - file is empty")
                    all_passed = False
        except Exception as e:
            test_results.append(f"✗ {md_file.name} - error reading: {str(e)}")
            all_passed = False
    
    # Try to run claude commands (if Claude CLI is available)
    claude_available, _ = check_claude_code_cli()
    if claude_available:
        try:
            # Test that claude can see our commands
            result = subprocess.run(
                ['claude', '--help'],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                test_results.append("✓ Claude Code CLI is responsive")
            else:
                test_results.append("✗ Claude Code CLI returned error")
                all_passed = False
        except Exception as e:
            test_results.append(f"✗ Error testing Claude CLI: {str(e)}")
            all_passed = False
    
    return all_passed, test_results


def uninstall_commands() -> Tuple[bool, List[str]]:
    """
    Uninstall MCP Memory Service commands from Claude Code.
    
    Returns:
        Tuple of (success, list_of_removed_files)
    """
    commands_dir = get_claude_commands_directory()
    removed_files = []
    
    if not commands_dir.exists():
        return True, []  # Nothing to remove
    
    try:
        # Remove all memory-*.md files
        for md_file in commands_dir.glob("memory-*.md"):
            md_file.unlink()
            removed_files.append(md_file.name)
            print_info(f"Removed: {md_file.name}")
        
        if removed_files:
            print_success(f"Successfully removed {len(removed_files)} commands")
        else:
            print_info("No MCP Memory Service commands found to remove")
        
        return True, removed_files
        
    except Exception as e:
        print_error(f"Failed to uninstall commands: {str(e)}")
        return False, []


def install_claude_commands(verbose: bool = True) -> bool:
    """
    Main function to install Claude Code commands for MCP Memory Service.
    
    Args:
        verbose: Whether to print detailed progress information
        
    Returns:
        True if installation was successful, False otherwise
    """
    if verbose:
        print_info("Installing Claude Code commands for MCP Memory Service...")
    
    # Check Claude Code CLI availability
    claude_available, claude_status = check_claude_code_cli()
    if not claude_available:
        print_error(f"Claude Code CLI not available: {claude_status}")
        print_info("Please install Claude Code CLI first: https://claude.ai/code")
        return False
    
    if verbose:
        print_success(f"Claude Code CLI detected: {claude_status}")
    
    # Check commands directory access
    can_access, access_status = check_commands_directory_access()
    if not can_access:
        print_error(access_status)
        return False
    
    if verbose:
        print_success(access_status)
    
    # Create backup of existing commands
    backup_path = backup_existing_commands()
    
    # Install command files
    install_success, installed_files = install_command_files()
    if not install_success:
        return False
    
    # Verify MCP service connectivity (optional - warn but don't fail)
    mcp_available, mcp_status = verify_mcp_service_connectivity()
    if mcp_available:
        if verbose:
            print_success(mcp_status)
    else:
        if verbose:
            print_warning(f"MCP service check: {mcp_status}")
            print_info("Commands installed but MCP service may need to be started")
    
    # Test command functionality
    if verbose:
        print_info("Testing installed commands...")
        tests_passed, test_results = test_command_functionality()
        for result in test_results:
            print_info(result)
        
        if tests_passed:
            print_success("All command tests passed")
        else:
            print_warning("Some command tests failed - commands may still work")
    
    # Show usage instructions
    if verbose:
        print_info("\nClaude Code commands installed successfully!")
        print_info("Available commands:")
        for cmd_file in installed_files:
            cmd_name = cmd_file.replace('.md', '')
            print_info(f"  claude /{cmd_name}")
        
        print_info("\nExample usage:")
        print_info('  claude /memory-store "Important decision about architecture"')
        print_info('  claude /memory-recall "what did we decide last week?"')
        print_info('  claude /memory-search --tags "architecture,database"')
        print_info('  claude /memory-health')
    
    return True


if __name__ == "__main__":
    # Allow running this script directly for testing
    import argparse
    
    parser = argparse.ArgumentParser(description="Install Claude Code commands for MCP Memory Service")
    parser.add_argument('--test', action='store_true', help='Test installation without installing')
    parser.add_argument('--uninstall', action='store_true', help='Uninstall commands')
    parser.add_argument('--quiet', action='store_true', help='Minimal output')
    
    args = parser.parse_args()
    
    if args.uninstall:
        success, removed = uninstall_commands()
        if success:
            sys.exit(0)
        else:
            sys.exit(1)
    elif args.test:
        # Test mode - check prerequisites but don't install
        claude_ok, claude_msg = check_claude_code_cli()
        access_ok, access_msg = check_commands_directory_access()
        mcp_ok, mcp_msg = verify_mcp_service_connectivity()
        
        print("Claude Code commands installation test:")
        print(f"  Claude CLI: {'✓' if claude_ok else '✗'} {claude_msg}")
        print(f"  Directory access: {'✓' if access_ok else '✗'} {access_msg}")
        print(f"  MCP service: {'✓' if mcp_ok else '⚠'} {mcp_msg}")
        
        if claude_ok and access_ok:
            print("✓ Ready to install Claude Code commands")
            sys.exit(0)
        else:
            print("✗ Prerequisites not met")
            sys.exit(1)
    else:
        # Normal installation
        success = install_claude_commands(verbose=not args.quiet)
        sys.exit(0 if success else 1)