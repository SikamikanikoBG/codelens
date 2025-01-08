#!/usr/bin/env python
"""
Script to install git hooks.
Works on both Windows and Linux/Mac.
"""
import os
import sys
import shutil
from pathlib import Path

def install_hooks():
    """Install git hooks for the project."""
    try:
        # Get the project root directory 
        project_root = Path(__file__).parent.parent
        
        # Paths
        git_hooks_dir = project_root / '.git' / 'hooks'
        pre_commit_source = project_root / 'scripts' / 'pre-commit.py'
        pre_commit_dest = git_hooks_dir / 'pre-commit'
        
        # Verify git repository
        if not git_hooks_dir.exists():
            print("Error: .git/hooks directory not found. Are you in a git repository?")
            return 1
            
        # Verify source file
        if not pre_commit_source.exists():
            print(f"Error: Source hook not found at {pre_commit_source}")
            return 1
        
        # Remove existing hook if present
        if pre_commit_dest.exists():
            os.remove(pre_commit_dest)
        
        # Copy the pre-commit hook
        shutil.copy2(pre_commit_source, pre_commit_dest)
        
        # Make the hook executable (no effect on Windows, required for Unix)
        os.chmod(pre_commit_dest, 0o755)
        
        print(f"Successfully installed git pre-commit hook to {pre_commit_dest}")
        return 0
        
    except Exception as e:
        print(f"Error installing hooks: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(install_hooks())