"""
LLM Code Lens - Insights Generator
Generates insights from code analysis results.
"""

from typing import Dict, List
from pathlib import Path
from ..utils import estimate_todo_priority

def generate_insights(analysis: Dict[str, dict]) -> List[str]:
    """
    Generate insights from code analysis results.
    
    Args:
        analysis: Dictionary of file paths to analysis results
        
    Returns:
        List of insight strings
    """
    insights = []
    
    # Basic project stats
    total_files = len(analysis) if isinstance(analysis, dict) else 0
    if total_files == 1:
        insights.append("Found 1 analyzable file")
    elif total_files > 0:
        insights.append(f"Found {total_files} analyzable files")
    
    # Track various metrics
    todo_count = 0
    todo_priorities = {'high': 0, 'medium': 0, 'low': 0}
    undocumented_count = 0
    complex_functions = []
    memory_leaks = 0
    
    for file_path, file_analysis in analysis.items():
        if not isinstance(file_analysis, dict):
            continue
            
        # Process TODOs
        for todo in file_analysis.get('todos', []):
            todo_count += 1
            text = todo.get('text', '').lower()
            priority = estimate_todo_priority(text)
            todo_priorities[priority] += 1
            
            # Check for memory leak TODOs
            if 'memory leak' in text:
                memory_leaks += 1
        
        # Process functions
        for func in file_analysis.get('functions', []):
            if not func.get('docstring'):
                undocumented_count += 1
            if func.get('complexity', 0) > 5 or func.get('loc', 0) > 50:
                complex_functions.append(f"{func.get('name', 'unnamed')} in {file_path}")
    
    # Add insights based on findings
    if todo_count > 0:
        insights.append(f"Found {todo_count} TODOs across {total_files} files")
        if todo_priorities['high'] > 0:
            insights.append(f"Found {todo_priorities['high']} high-priority TODOs")
    
    if memory_leaks > 0:
        insights.append(f"Found {memory_leaks} potential memory leak issues")
        
    if complex_functions:
        if len(complex_functions) <= 3:
            insights.append(f"Complex functions detected: {', '.join(complex_functions)}")
        else:
            insights.append(f"Found {len(complex_functions)} complex functions that might need attention")
    
    if undocumented_count > 0:
        insights.append(f"Found {undocumented_count} undocumented functions")
    
    return insights
