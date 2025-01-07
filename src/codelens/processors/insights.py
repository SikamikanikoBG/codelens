from typing import Dict, List

def generate_insights(analysis: Dict[str, dict]) -> List[str]:
    """Generate insights from analysis results."""
    insights = []
    
    # Project-wide insights
    total_files = len(analysis)
    total_todos = sum(
        len(file_analysis.get('todos', [])) 
        for file_analysis in analysis.values()
    )
    
    if total_todos > 0:
        insights.append(f"Found {total_todos} TODOs across {total_files} files")
    
    # Complex functions
    complex_functions = []
    for file_path, file_analysis in analysis.items():
        for func in file_analysis.get('functions', []):
            if func.get('loc', 0) > 50:  # Simple complexity metric
                complex_functions.append(
                    f"{func['name']} in {file_path}"
                )
    
    if complex_functions:
        insights.append(
            f"Complex functions detected: {', '.join(complex_functions)}"
        )
    
    # File patterns
    file_patterns = {}
    for file_path in analysis:
        pattern = file_path.split('/')[-2] if '/' in file_path else ''
        if pattern:
            file_patterns[pattern] = file_patterns.get(pattern, 0) + 1
    
    common_patterns = [
        pattern for pattern, count in file_patterns.items()
        if count > 1 and pattern not in {'src', 'lib', 'test'}
    ]
    
    if common_patterns:
        insights.append(
            f"Common code organization patterns: {', '.join(common_patterns)}"
        )
    
    return insights
