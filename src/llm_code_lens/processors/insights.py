from typing import Dict, List, Set
from pathlib import Path

def generate_insights(analysis: Dict[str, dict]) -> List[str]:
    """Generate comprehensive insights from analysis results."""
    insights = []
    
    # Project-wide metrics
    total_files = len(analysis)
    total_todos = sum(
        len(file_analysis.get('todos', [])) 
        for file_analysis in analysis.values()
    )
    
    # Basic counts
    if total_todos > 0:
        insights.append(f"Found {total_todos} TODOs across {total_files} files")
    
    # Code complexity insights
    complex_functions = []
    large_functions = []
    undocumented_items = []
    entry_points = []
    core_modules = set()
    
    for file_path, file_analysis in analysis.items():
        # Track complex functions (high LOC or many arguments)
        for func in file_analysis.get('functions', []):
            if func.get('loc', 0) > 50:
                complex_functions.append(f"{func['name']} in {file_path}")
            if len(func.get('args', [])) > 5:
                large_functions.append(f"{func['name']} in {file_path}")
            if not func.get('docstring'):
                undocumented_items.append(f"function {func['name']} in {file_path}")
        
        # Track undocumented classes
        for cls in file_analysis.get('classes', []):
            if not cls.get('docstring'):
                undocumented_items.append(f"class {cls['name']} in {file_path}")
        
        # Identify potential entry points
        if _is_entry_point(file_path, file_analysis):
            entry_points.append(file_path)
        
        # Identify core modules
        if _is_core_module(file_analysis):
            core_modules.add(file_path)
    
    # Add complex code insights
    if complex_functions:
        insights.append(f"Complex functions detected (>50 lines): {', '.join(complex_functions)}")
    if large_functions:
        insights.append(f"Functions with many parameters (>5): {', '.join(large_functions)}")
    if undocumented_items:
        insights.append(f"Undocumented items found: {', '.join(undocumented_items)}")
    
    # Add architectural insights
    if entry_points:
        insights.append(f"Potential entry points: {', '.join(entry_points)}")
    if core_modules:
        insights.append(f"Core modules with high complexity: {', '.join(core_modules)}")
    
    # Analyze dependencies
    dependency_insights = _analyze_dependencies(analysis)
    insights.extend(dependency_insights)
    
    # Code organization patterns
    pattern_insights = _analyze_code_patterns(analysis)
    insights.extend(pattern_insights)
    
    return insights

def _is_entry_point(file_path: str, analysis: dict) -> bool:
    """Identify if a file is a likely entry point."""
    file_name = Path(file_path).name
    entry_patterns = {'main.py', 'app.py', 'cli.py', 'run.py', 'server.py'}
    
    if file_name in entry_patterns:
        return True
    
    # Check for main-like functions
    for func in analysis.get('functions', []):
        if func['name'] in {'main', 'run', 'start', 'cli', 'execute'}:
            return True
    
    return False

def _is_core_module(analysis: dict) -> bool:
    """Identify if a file is a core module based on complexity metrics."""
    # Files with many functions or classes
    if len(analysis.get('functions', [])) > 5 or len(analysis.get('classes', [])) > 2:
        return True
    
    # Files with complex functions
    complex_funcs = sum(1 for f in analysis.get('functions', [])
                       if f.get('loc', 0) > 30 or len(f.get('args', [])) > 3)
    if complex_funcs >= 2:
        return True
    
    return False

def _analyze_dependencies(analysis: Dict[str, dict]) -> List[str]:
    """Analyze project dependencies and import patterns."""
    insights = []
    import_count = {}
    unique_imports = set()
    circular_deps = set()
    
    # Track imports across files
    for file_path, file_analysis in analysis.items():
        file_imports = file_analysis.get('imports', [])
        import_count[file_path] = len(file_imports)
        unique_imports.update(file_imports)
        
        # Check for potential circular imports
        for imp in file_imports:
            if imp.startswith('from .'):
                source = Path(file_path).parent
                target = source / (imp.split()[1] + '.py')
                if str(target) in analysis:
                    circular_deps.add((file_path, str(target)))
    
    # Identify highly imported modules
    popular_modules = [
        path for path, count in import_count.items()
        if count > 5  # Threshold for "many imports"
    ]
    if popular_modules:
        insights.append(f"Modules with many imports: {', '.join(popular_modules)}")
    
    # Report potential circular dependencies
    if circular_deps:
        circular_list = [f"{a} ⟷ {b}" for a, b in circular_deps]
        insights.append(f"Potential circular dependencies detected: {', '.join(circular_list)}")
    
    # Common external dependencies
    external_deps = {imp.split()[1] for imp in unique_imports 
                    if imp.startswith('import ') and not imp.startswith('import.')}
    if external_deps:
        insights.append(f"Main external dependencies: {', '.join(sorted(external_deps))}")
    
    return insights

def _analyze_code_patterns(analysis: Dict[str, dict]) -> List[str]:
    """Analyze code organization and patterns."""
    insights = []
    
    # Track file organization patterns
    directories = {}
    for file_path in analysis:
        directory = str(Path(file_path).parent)
        if directory not in directories:
            directories[directory] = []
        directories[directory].append(file_path)
    
    # Identify major code groups
    major_dirs = [
        (dir_path, files) for dir_path, files in directories.items()
        if len(files) >= 3  # Threshold for "major" directory
    ]
    
    if major_dirs:
        dir_insights = [
            f"{Path(dir_path).name} ({len(files)} files)"
            for dir_path, files in major_dirs
        ]
        insights.append(f"Major code groups: {', '.join(dir_insights)}")
    
    # Check for consistent naming patterns
    naming_patterns = _analyze_naming_patterns(analysis)
    if naming_patterns:
        insights.extend(naming_patterns)
    
    return insights

def _analyze_naming_patterns(analysis: Dict[str, dict]) -> List[str]:
    """Analyze naming patterns in the code."""
    insights = []
    
    # Collect all names
    function_names = []
    class_names = []
    
    for file_analysis in analysis.values():
        function_names.extend(f['name'] for f in file_analysis.get('functions', []))
        class_names.extend(c['name'] for c in file_analysis.get('classes', []))
    
    # Check naming conventions
    if function_names:
        snake_case = sum(1 for name in function_names if '_' in name)
        camel_case = sum(1 for name in function_names 
                        if not '_' in name and not name.isupper())
        
        if snake_case > camel_case * 2:
            insights.append("Consistent use of snake_case for function names")
        elif camel_case > snake_case * 2:
            insights.append("Consistent use of camelCase for function names")
    
    if class_names:
        pascal_case = sum(1 for name in class_names 
                         if name[0].isupper() and not '_' in name)
        if pascal_case > len(class_names) * 0.8:
            insights.append("Consistent use of PascalCase for class names")
    
    return insights