"""
LLM Code Lens - Utility Functions
Shared utility functions used across multiple modules.
"""

from typing import Dict, List, Set, Optional

def estimate_todo_priority(text: str) -> str:
    """
    Estimate TODO priority based on content.
    
    Args:
        text: The text of the TODO comment
        
    Returns:
        Priority level: 'high', 'medium', or 'low'
    """
    text = text.lower()
    if any(word in text for word in ['urgent', 'critical', 'fixme', 'bug', 'memory leak', 'security']):
        return 'high'
    if any(word in text for word in ['important', 'needed', 'should']):
        return 'medium'
    return 'low'

def is_potential_entry_point(file_path: str, analysis: dict) -> bool:
    """
    Identify if a file is a potential entry point.
    
    Args:
        file_path: Path to the file
        analysis: Analysis data for the file
        
    Returns:
        bool: True if the file is likely an entry point
    """
    from pathlib import Path
    
    filename = Path(file_path).name
    if filename in {'main.py', 'app.py', 'cli.py', 'server.py', 'index.js', 'server.js'}:
        return True
    
    # Check for main-like functions
    for func in analysis.get('functions', []):
        if func.get('name') in {'main', 'run', 'start', 'cli', 'execute'}:
            return True
    
    return False

def is_core_file(analysis: dict) -> bool:
    """
    Identify if a file is likely a core component.
    
    Args:
        analysis: Analysis data for the file
        
    Returns:
        bool: True if the file is likely a core component
    """
    # Check function count
    if len(analysis.get('functions', [])) > 5:
        return True
    
    # Check class count
    if len(analysis.get('classes', [])) > 2:
        return True
    
    # Check function complexity
    complex_funcs = sum(1 for f in analysis.get('functions', [])
                       if (f.get('complexity', 0) > 5 or
                           f.get('loc', 0) > 50 or
                           len(f.get('args', [])) > 3))
    if complex_funcs >= 1:
        return True
    
    # Check file complexity
    if analysis.get('metrics', {}).get('complexity', 0) > 20:
        return True
    
    return False
