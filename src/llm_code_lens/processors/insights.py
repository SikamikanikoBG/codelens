from typing import Dict, List, Set
from pathlib import Path

def generate_insights(analysis: Dict[str, dict]) -> List[str]:
    """Generate insights with improved handling."""
    insights = []
    
    # Basic project stats
    total_files = len(analysis) if isinstance(analysis, dict) else 0
    if total_files == 1:
        insights.append("Found 1 analyzable file")
    elif total_files > 0:
        insights.append(f"Found {total_files} analyzable files")
        
    # Track metrics
    todo_count = 0
    memory_leaks = 0
    for file_analysis in analysis.values():
        if isinstance(file_analysis, dict):
            todos = file_analysis.get('todos', [])
            todo_count += len(todos)
            # Check for memory leak TODOs
            memory_leaks += sum(1 for todo in todos 
                              if 'memory leak' in todo.get('text', '').lower())
    
    if todo_count > 0:
        insights.append(f"Found {todo_count} TODOs across {total_files} files")
    if memory_leaks > 0:
        insights.append(f"Found {memory_leaks} potential memory leak issues")

    return insights
