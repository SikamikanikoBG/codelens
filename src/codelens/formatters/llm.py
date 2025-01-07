# src/codelens/formatters/llm.py
from typing import Dict
from ..analyzer.base import AnalysisResult

def format_analysis(result: AnalysisResult) -> str:
    """Format analysis results in an LLM-friendly text format."""
    sections = []
    
    # Project Overview
    sections.extend([
        "CODEBASE SUMMARY:",
        f"This project contains {result.summary['project_stats']['total_files']} files:",
        "File types: " + ", ".join(
            f"{ext}: {count}" 
            for ext, count in result.summary['project_stats']['by_type'].items()
        ),
        f"Total lines of code: {result.summary['project_stats']['lines_of_code']}",
        f"Average file size: {result.summary['project_stats']['avg_file_size']:.1f} lines",
        "",
    ])
    
    # Key Insights
    if result.insights:
        sections.extend([
            "KEY INSIGHTS:",
            *[f"- {insight}" for insight in result.insights],
            "",
        ])
    
    # Code Metrics
    sections.extend([
        "CODE METRICS:",
        f"Functions: {result.summary['code_metrics']['functions']['count']} "
        f"({result.summary['code_metrics']['functions']['with_docs']} documented)",
        f"Classes: {result.summary['code_metrics']['classes']['count']} "
        f"({result.summary['code_metrics']['classes']['with_docs']} documented)",
        f"Documentation coverage: {result.summary['maintenance']['doc_coverage']:.1f}%",
        "",
    ])
    
    # Maintenance Info
    if result.summary['maintenance']['todos']:
        sections.extend([
            "TODOS:",
            *[f"- [{todo['priority']}] {todo['file']}: {todo['text']}" 
              for todo in result.summary['maintenance']['todos']],
            "",
        ])
    
    # Structure Info
    if result.summary['structure']['entry_points']:
        sections.extend([
            "ENTRY POINTS:",
            *[f"- {entry}" for entry in result.summary['structure']['entry_points']],
            "",
        ])
    
    if result.summary['structure']['core_files']:
        sections.extend([
            "CORE FILES:",
            *[f"- {file}" for file in result.summary['structure']['core_files']],
            "",
        ])
    
    # File Analysis
    sections.append("PROJECT STRUCTURE AND CODE INSIGHTS:")
    
    # Group files by directory
    by_directory = {}
    total_by_dir = {}
    for file_path, analysis in result.files.items():
        dir_path = '/'.join(file_path.split('\\')[:-1]) or '.'
        if dir_path not in by_directory:
            by_directory[dir_path] = {}
            total_by_dir[dir_path] = 0
        by_directory[dir_path][file_path.split('\\')[-1]] = analysis
        total_by_dir[dir_path] += analysis.get('metrics', {}).get('loc', 0)
    
    # Format each directory
    for dir_path, files in by_directory.items():
        sections.extend([
            "",  # Empty line before directory
            "=" * 80,  # Separator line
            f"{dir_path}/ ({total_by_dir[dir_path]} lines)",
            "=" * 80,
        ])
        
        # Sort files by importance (non-empty before empty)
        sorted_files = sorted(
            files.items(),
            key=lambda x: (
                x[1].get('metrics', {}).get('loc', 0) == 0,
                x[0]
            )
        )
        
        for filename, analysis in sorted_files:
            # Skip empty files or show them in compact form
            if analysis.get('metrics', {}).get('loc', 0) == 0:
                sections.append(f"  {filename} (empty)")
                continue
                
            sections.extend(_format_file_analysis(filename, analysis))
            sections.append("")  # Empty line between files
    
    return '\n'.join(sections)

def _format_file_analysis(filename: str, analysis: dict) -> list:
    """Format single file analysis."""
    sections = [f"  {filename}"]
    
    metrics = analysis.get('metrics', {})
    sections.append(f"    Lines: {metrics.get('loc', 0)}")
    
    # Add imports
    if analysis.get('imports'):
        sections.append("    IMPORTS:")
        sections.extend(f"      {imp}" for imp in analysis['imports'])
    
    # Add functions
    if analysis.get('functions'):
        sections.append("    FUNCTIONS:")
        for func in analysis['functions']:
            sections.extend([
                f"      {func['name']}:",
                f"        Args: {', '.join(func.get('args', []))}",
                f"        Line: {func.get('line_number', '?')}",
            ])
            if func.get('docstring'):
                sections.append(f"        Doc: {func['docstring']}")
    
    # Add classes
    if analysis.get('classes'):
        sections.append("    CLASSES:")
        for cls in analysis['classes']:
            sections.extend([
                f"      {cls['name']}:",
                f"        Line: {cls.get('line_number', '?')}",
            ])
            if cls.get('methods'):
                sections.append(
                    f"        Methods: {', '.join(cls['methods'])}"
                )
            if cls.get('docstring'):
                sections.append(f"        Doc: {cls['docstring']}")
    
    # Add TODOs
    if analysis.get('todos'):
        sections.append("    TODOS:")
        for todo in analysis['todos']:
            sections.append(
                f"      Line {todo['line']}: {todo['text']}"
            )
    
    return sections