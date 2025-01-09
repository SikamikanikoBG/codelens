from typing import Dict, List
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
        f"Overall complexity: {sum(f.get('metrics', {}).get('complexity', 0) for f in result.files.values())}",
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
        f"({result.summary['code_metrics']['functions']['with_docs']} documented, "
        f"{result.summary['code_metrics']['functions']['complex']} complex)",
        f"Classes: {result.summary['code_metrics']['classes']['count']} "
        f"({result.summary['code_metrics']['classes']['with_docs']} documented)",
        f"Documentation coverage: {result.summary['maintenance']['doc_coverage']:.1f}%",
        f"Total imports: {result.summary['code_metrics']['imports']['count']} "
        f"({len(result.summary['code_metrics']['imports']['unique'])} unique)",
        "",
    ])
    
    # Maintenance Info
    if result.summary['maintenance']['todos']:
        sections.extend([
            "TODOS:",
            *[_format_todo(todo) for todo in result.summary['maintenance']['todos']],
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
    for dir_path, files in sorted(by_directory.items()):
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
    """Format analysis of a single file."""
    sections = [f"  {filename}"]
    metrics = analysis.get('metrics', {})
    
    # Basic metrics
    sections.append(f"    Lines: {metrics.get('loc', 0)}")
    if 'complexity' in metrics:
        sections.append(f"    Complexity: {metrics['complexity']}")
    
    # Type-specific information
    if analysis['type'] == 'python':
        sections.extend(_format_python_file(analysis))
    elif analysis['type'] == 'sql':
        sections.extend(_format_sql_file(analysis))
    elif analysis['type'] == 'javascript':
        sections.extend(_format_js_file(analysis))
    
    # Common elements
    if analysis.get('imports'):
        sections.append("\n    IMPORTS:")
        sections.extend(f"      {imp}" for imp in sorted(analysis['imports']))
    
    if analysis.get('todos'):
        sections.append("\n    TODOS:")
        for todo in sorted(analysis['todos'], key=lambda x: x['line']):
            sections.append(f"      Line {todo['line']}: {todo['text']}")
    
    return sections

def _format_python_file(analysis: dict) -> List[str]:
    """Format Python-specific file information."""
    sections = []
    
    if analysis.get('classes'):
        sections.append("\n    CLASSES:")
        for cls in analysis['classes']:
            sections.append(f"      {cls['name']}:")
            if cls.get('bases'):
                sections.append(f"        Inherits: {', '.join(cls['bases'])}")
            if cls.get('methods'):
                method_types = {
                    'property': [m['name'] for m in cls['methods'] if m.get('is_property')],
                    'classmethod': [m['name'] for m in cls['methods'] if m.get('is_classmethod')],
                    'staticmethod': [m['name'] for m in cls['methods'] if m.get('is_staticmethod')],
                    'instance': [m['name'] for m in cls['methods'] if not any([
                        m.get('is_property'), m.get('is_classmethod'), m.get('is_staticmethod')
                    ])]
                }
                if method_types['property']:
                    sections.append(f"        Properties: {', '.join(method_types['property'])}")
                if method_types['classmethod']:
                    sections.append(f"        Class methods: {', '.join(method_types['classmethod'])}")
                if method_types['staticmethod']:
                    sections.append(f"        Static methods: {', '.join(method_types['staticmethod'])}")
                if method_types['instance']:
                    sections.append(f"        Instance methods: {', '.join(method_types['instance'])}")
            if cls.get('docstring'):
                sections.append(f"        Doc: {cls['docstring'].split(chr(10))[0]}")
    
    if analysis.get('functions'):
        sections.append("\n    FUNCTIONS:")
        for func in analysis['functions']:
            sections.append(f"      {func['name']}:")
            if func.get('args'):
                sections.append(f"        Args: {', '.join(func['args'])}")
            if func.get('return_type'):
                sections.append(f"        Returns: {func['return_type']}")
            if func.get('decorators'):
                sections.append(f"        Decorators: {', '.join(func['decorators'])}")
            if func.get('docstring'):
                sections.append(f"        Doc: {func['docstring'].split(chr(10))[0]}")
            if func.get('complexity'):
                sections.append(f"        Complexity: {func['complexity']}")
    
    return sections

def _format_sql_file(analysis: dict) -> List[str]:
    """Format SQL-specific file information."""
    sections = []
    
    for obj in analysis.get('objects', []):
        sections.extend([
            f"\n    {obj['type'].upper()}:",
            f"      Name: {obj['name']}",
            f"      Lines: {obj['loc']}",
            f"      Complexity: {obj.get('complexity', 0)}"
        ])
    
    if analysis.get('parameters'):
        sections.append("\n    PARAMETERS:")
        for param in analysis['parameters']:
            param_text = f"      @{param['name']} ({param['data_type']}"
            if 'default' in param:
                param_text += f", default={param['default']}"
            param_text += ")"
            if 'description' in param:
                param_text += f" -- {param['description']}"
            sections.append(param_text)
    
    if analysis.get('dependencies'):
        sections.append("\n    DEPENDENCIES:")
        sections.extend(f"      {dep}" for dep in sorted(analysis['dependencies']))
    
    if analysis.get('comments'):
        sections.append("\n    COMMENTS:")
        for comment in sorted(analysis['comments'], key=lambda x: x['line']):
            sections.append(f"      Line {comment['line']}: {comment['text']}")
    
    return sections

def _format_js_file(analysis: dict) -> List[str]:
    """Format JavaScript-specific file information."""
    sections = []
    
    if analysis.get('exports'):
        sections.append("\n    EXPORTS:")
        sections.extend(f"      {exp}" for exp in sorted(analysis['exports']))
    
    if analysis.get('classes'):
        sections.append("\n    CLASSES:")
        for cls in analysis['classes']:
            sections.extend([
                f"      {cls['name']}:",
                f"        Line: {cls['line_number']}"
            ])
            if cls.get('extends'):
                sections.append(f"        Extends: {cls['extends']}")
    
    if analysis.get('functions'):
        sections.append("\n    FUNCTIONS:")
        for func in analysis['functions']:
            sections.extend([
                f"      {func['name']}:",
                f"        Line: {func['line_number']}"
            ])
    
    return sections

def _format_todo(todo: dict) -> str:
    """Format a TODO entry."""
    return f"- [{todo['priority']}] {todo['file']}: {todo['text']}"