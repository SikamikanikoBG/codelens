#!/usr/bin/env python
"""
Pre-commit hook to run tests before committing.
Works on both Windows and Linux/Mac.
"""
import sys
import subprocess
from pathlib import Path

def run_command(command):
    """Run a command and return its result."""
    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            shell=True,  # Required for Windows compatibility
            encoding='utf-8'
        )
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return 1, '', str(e)

def main():
    print("Running pre-commit tests...")
    
    try:
        # Run tests with pytest
        print("Running pytest...")
        test_command = "python -m pytest"
        code, stdout, stderr = run_command(test_command)
        
        if stdout:
            print(stdout)
        if stderr:
            print(stderr, file=sys.stderr)
        
        if code != 0:
            print("Tests failed. Commit aborted.")
            return 1
            
        return 0
    
    except Exception as e:
        print(f"Error during pre-commit hook: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())