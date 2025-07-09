"""
Version checking module for LLM Code Lens.
Checks for newer versions on PyPI and notifies users.
"""

import requests
import time
from packaging import version
from typing import Optional, Tuple
from rich.console import Console

# Import the current version
from . import __version__

console = Console()

def check_for_newer_version() -> None:
    """
    Check if a newer version is available on PyPI and print a notification if so.
    Designed to fail silently if checks cannot be performed.
    """
    try:
        current = _get_current_version()
        latest, pkg_url = _get_latest_version()
        
        if latest and version.parse(latest) > version.parse(current):
            console.print(f"[bold yellow]⚠️ A newer version ({latest}) of LLM Code Lens is available![/]")
            console.print(f"[yellow]You're currently using version {current}[/]")
            console.print(f"[yellow]Upgrade with: pip install --upgrade llm_code_lens[/]")
            console.print(f"[yellow]See what's new: {pkg_url}[/]\n")
    except Exception:
        # Fail silently - version check should never interrupt main functionality
        pass

def _get_current_version() -> str:
    """Get the current package version."""
    return __version__

def _get_latest_version() -> Tuple[Optional[str], str]:
    """
    Fetch the latest version from PyPI.
    
    Returns:
        Tuple containing (latest_version, package_url) or (None, default_url) on failure
    """
    default_url = "https://pypi.org/project/llm-code-lens/"
    
    try:
        # Use a short timeout to prevent hanging
        response = requests.get(
            "https://pypi.org/pypi/llm-code-lens/json",
            timeout=3.0
        )
        
        if response.status_code == 200:
            data = response.json()
            latest_version = data.get("info", {}).get("version")
            return latest_version, default_url
        
        return None, default_url
    except (requests.RequestException, ValueError, KeyError):
        # Handle network issues, JSON parsing errors, or missing keys
        return None, default_url
