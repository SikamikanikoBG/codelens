# File: R:\Projects\codelens\src\codelens\processor\summary.py
"""
LLM Code Lens - Summary Processor
Generates project summaries from analysis results.
"""

from typing import Dict, List
from pathlib import Path
from ..utils import estimate_todo_priority, is_potential_entry_point, is_core_file

# src/llm_code_lens/processors/summary.py

def generate_summary(analysis: Dict[str, dict]) -> dict:
    """Generate summary with improved metrics handling."""
    summary = {
        'project_stats': {
            'total_files': len(analysis),
            'by_type': {},
            'lines_of_code': 0,
            'avg_file_size': 0
        },
        'code_metrics': {
            'functions': {'count': 0, 'with_docs': 0, 'complex': 0},
            'classes': {'count': 0, 'with_docs': 0},
            'imports': {'count': 0, 'unique': set()},  # Changed to set()
            'sql_objects': {'procedures': 0, 'views': 0, 'functions': 0}
        },
        'maintenance': {
            'todos': [],
            'comments_ratio': 0,
            'doc_coverage': 0
        },
        'structure': {
            'directories': set(),
            'entry_points': [],
            'core_files': [],  # Added missing key
            'sql_dependencies': []
        }
    }

    # Process each file
    for file_path, file_analysis in analysis.items():
        _process_file_stats(file_path, file_analysis, summary)
        _process_code_metrics(file_analysis, summary)
        _process_maintenance_info(file_path, file_analysis, summary)
        _process_structure_info(file_path, file_analysis, summary)
    
    # Calculate final metrics
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

def _process_code_metrics(file_analysis: dict, summary: dict) -> None:
    """Process code metrics from analysis."""
    if not isinstance(file_analysis, dict):
        return
    
    # Process functions
    for func in file_analysis.get('functions', []):
        if not isinstance(func, dict):
            continue
            
        summary['code_metrics']['functions']['count'] += 1
        
        if func.get('docstring'):
            summary['code_metrics']['functions']['with_docs'] += 1
        
        # Safely handle complexity and loc values that might be None
        complexity = func.get('complexity')
        loc = func.get('loc')
        
        if (complexity is not None and complexity > 5) or \
           (loc is not None and loc > 50):
            summary['code_metrics']['functions']['complex'] += 1

    # Process classes
    for cls in file_analysis.get('classes', []):
        if not isinstance(cls, dict):
            continue
            
        summary['code_metrics']['classes']['count'] += 1
        if cls.get('docstring'):
            summary['code_metrics']['classes']['with_docs'] += 1

    # Process imports
    imports = file_analysis.get('imports', [])
    if isinstance(imports, list):
        summary['code_metrics']['imports']['count'] += len(imports)
        summary['code_metrics']['imports']['unique'].update(
            set(imp for imp in imports if isinstance(imp, str))
        )




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
    return estimate_todo_priority(text)

def _is_potential_entry_point(file_path: str, analysis: dict) -> bool:
    """Identify if a file is a potential entry point."""
    return is_potential_entry_point(file_path, analysis)

def _is_core_file(analysis: dict) -> bool:
    """Identify if a file is likely a core component."""
    return is_core_file(analysis)

def generate_insights(analysis: Dict[str, dict]) -> List[str]:
    """Generate insights with improved handling of file analysis."""
    from .insights import generate_insights as gen_insights
    return gen_insights(analysis)


