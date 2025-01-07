# File: R:\Projects\codelens\src\codelens\processor\summary.py

from typing import Dict, List
from pathlib import Path

def generate_summary(analysis: Dict[str, dict]) -> dict:
    """
    Generate comprehensive project summary from analysis results.
    
    Args:
        analysis: Dictionary containing analysis results for each file
        
    Returns:
        Dictionary containing project summary metrics and insights
    """
    summary = {
        'project_stats': {
            'total_files': len(analysis),
            'by_type': {},           # File counts by extension
            'lines_of_code': 0,      # Total LOC
            'avg_file_size': 0,      # Average file size
        },
        'code_metrics': {
            'functions': {
                'count': 0,
                'with_docs': 0,
                'complex': 0         # Functions with high complexity
            },
            'classes': {
                'count': 0,
                'with_docs': 0
            },
            'imports': {
                'count': 0,
                'unique': set()
            }
        },
        'maintenance': {
            'todos': [],            # List of TODOs with priority
            'comments_ratio': 0,    # Comments to code ratio
            'doc_coverage': 0       # Documentation coverage percentage
        },
        'structure': {
            'directories': set(),   # Unique directories
            'entry_points': [],     # Potential entry point files
            'core_files': []        # Files with high incoming dependencies
        }
    }
    
    # Process each file
    for file_path, file_analysis in analysis.items():
        _process_file_stats(file_path, file_analysis, summary)
        _process_code_metrics(file_analysis, summary)
        _process_maintenance_info(file_path, file_analysis, summary)
        _process_structure_info(file_path, file_analysis, summary)
    
    # Calculate averages and percentages
    _calculate_final_metrics(summary)
    
    return summary

def _process_file_stats(file_path: str, analysis: dict, summary: dict) -> None:
    """Process basic file statistics."""
    # Track file types
    ext = Path(file_path).suffix
    summary['project_stats']['by_type'][ext] = \
        summary['project_stats']['by_type'].get(ext, 0) + 1
    
    # Track lines of code
    metrics = analysis.get('metrics', {})
    loc = metrics.get('loc', 0)
    summary['project_stats']['lines_of_code'] += loc

def _process_code_metrics(analysis: dict, summary: dict) -> None:
    """Process code metrics from analysis."""
    metrics = analysis.get('metrics', {})
    
    # Functions
    functions = analysis.get('functions', [])
    summary['code_metrics']['functions']['count'] += len(functions)
    summary['code_metrics']['functions']['with_docs'] += \
        sum(1 for f in functions if f.get('docstring'))
    summary['code_metrics']['functions']['complex'] += \
        sum(1 for f in functions if f.get('loc', 0) > 50)
    
    # Classes
    classes = analysis.get('classes', [])
    summary['code_metrics']['classes']['count'] += len(classes)
    summary['code_metrics']['classes']['with_docs'] += \
        sum(1 for c in classes if c.get('docstring'))
    
    # Imports
    imports = analysis.get('imports', [])
    summary['code_metrics']['imports']['count'] += len(imports)
    summary['code_metrics']['imports']['unique'].update(imports)

def _process_maintenance_info(file_path: str, analysis: dict, summary: dict) -> None:
    """Process maintenance-related information."""
    # Track TODOs
    for todo in analysis.get('todos', []):
        summary['maintenance']['todos'].append({
            'file': file_path,
            'line': todo['line'],
            'text': todo['text'],
            'priority': _estimate_todo_priority(todo['text'])
        })
    
    # Track comments
    comments = len(analysis.get('comments', []))
    lines = analysis.get('metrics', {}).get('loc', 0)
    if lines > 0:
        summary['maintenance']['comments_ratio'] += comments / lines

def _process_structure_info(file_path: str, analysis: dict, summary: dict) -> None:
    """Process project structure information."""
    # Track directories
    dir_path = str(Path(file_path).parent)
    summary['structure']['directories'].add(dir_path)
    
    # Identify potential entry points
    if _is_potential_entry_point(file_path, analysis):
        summary['structure']['entry_points'].append(file_path)
    
    # Identify core files based on imports
    if _is_core_file(analysis):
        summary['structure']['core_files'].append(file_path)

def _calculate_final_metrics(summary: dict) -> None:
    """Calculate final averages and percentages."""
    total_files = summary['project_stats']['total_files']
    if total_files > 0:
        # Calculate average file size
        summary['project_stats']['avg_file_size'] = \
            summary['project_stats']['lines_of_code'] / total_files
        
        # Calculate documentation coverage
        funcs = summary['code_metrics']['functions']
        classes = summary['code_metrics']['classes']
        total_elements = funcs['count'] + classes['count']
        if total_elements > 0:
            documented = funcs['with_docs'] + classes['with_docs']
            summary['maintenance']['doc_coverage'] = \
                (documented / total_elements) * 100
        
        # Convert sets to lists for JSON serialization
        summary['code_metrics']['imports']['unique'] = \
            list(summary['code_metrics']['imports']['unique'])
        summary['structure']['directories'] = \
            list(summary['structure']['directories'])

def _estimate_todo_priority(text: str) -> str:
    """Estimate TODO priority based on content."""
    text = text.lower()
    if any(word in text for word in ['urgent', 'critical', 'fixme', 'bug']):
        return 'high'
    if any(word in text for word in ['important', 'needed', 'should']):
        return 'medium'
    return 'low'

def _is_potential_entry_point(file_path: str, analysis: dict) -> bool:
    """Identify if a file is a potential entry point."""
    filename = Path(file_path).name
    if filename in ['main.py', 'app.py', 'index.js', 'server.js']:
        return True
    
    # Check if file has main function or similar patterns
    for func in analysis.get('functions', []):
        if func['name'] in ['main', 'run', 'start']:
            return True
    
    return False

def _is_core_file(analysis: dict) -> bool:
    """Identify if a file is likely a core component."""
    # Files with many functions/classes are likely core files
    if (len(analysis.get('functions', [])) > 5 or 
        len(analysis.get('classes', [])) > 2):
        return True
    
    return False