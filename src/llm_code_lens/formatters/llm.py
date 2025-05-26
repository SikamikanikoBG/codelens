from typing import Dict, List
from ..analyzer.base import AnalysisResult

def format_analysis(result: AnalysisResult) -> str:
    """Format analysis results with tree structure."""
    sections = []
    
    # Determine if this is a large codebase (>10K LOC)
    total_loc = result.summary['project_stats']['lines_of_code']
    is_large_codebase = total_loc > 10000

    # Add system information at the top
    import platform
    import sys
    sections.extend([
        "SYSTEM INFORMATION:",
        "="*80,
        f"Operating System: {platform.system()} {platform.release()} ({platform.version()})",
        f"Architecture: {platform.machine()}",
        f"Python Version: {sys.version}",
        f"Python Executable: {sys.executable}",
        "",
    ])

    # Project Overview (existing)
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

    # Project Tree Structure
    if 'project_tree' in result.summary.get('structure', {}):
        sections.extend([
            "PROJECT STRUCTURE:",
            "=" * 80,
            result.summary['structure']['project_tree'],
            "",
        ])

    # Configuration Summary (condensed for large codebases)
    if 'configuration' in result.summary:
        sections.extend([
            "PROJECT CONFIGURATION:",
            _format_configuration(result.summary['configuration'], is_large_codebase),
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

    # Maintenance Info (condensed for large codebases)
    if result.summary['maintenance']['todos']:
        sections.extend([
            "TODOS:",
            *_format_todos_section(result.summary['maintenance']['todos'], is_large_codebase),
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

    # File Analysis (with size-based formatting)
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
                if not is_large_codebase:  # Only show empty files for small codebases
                    sections.append(f"  {filename} (empty)")
                continue

            sections.extend(_format_file_analysis(filename, analysis, is_large_codebase))
            sections.append("")  # Empty line between files

    return '\n'.join(sections)

def _format_configuration(config: dict, is_large_codebase: bool = False) -> str:
    """Format configuration information."""
    config_lines = []

    for config_file, info in config.items():
        if info and 'error' not in info:
            config_lines.append(f"  {config_file}:")

            if config_file == 'package.json':
                if info.get('framework_indicators'):
                    config_lines.append(f"    Frameworks: {', '.join(info['framework_indicators'])}")
                if info.get('scripts') and not is_large_codebase:
                    config_lines.append(f"    Scripts: {', '.join(info['scripts'])}")
                if info.get('dependencies'):
                    config_lines.append(f"    Dependencies: {len(info['dependencies'])} packages")

            elif config_file == 'tsconfig.json':
                if info.get('target'):
                    config_lines.append(f"    Target: {info['target']}")
                if info.get('jsx') and not is_large_codebase:
                    config_lines.append(f"    JSX: {info['jsx']}")
                if info.get('strict') and not is_large_codebase:
                    config_lines.append(f"    Strict mode: {info['strict']}")

            elif config_file == 'README.md':
                summary_len = 50 if is_large_codebase else 100
                config_lines.append(f"    Summary: {info['summary'][:summary_len]}...")

        elif info and 'error' in info and not is_large_codebase:
            config_lines.append(f"  {config_file}: {info['error']}")

    return '\n'.join(config_lines) if config_lines else "  No configuration files found"

def _format_todos_section(todos: List[dict], is_large_codebase: bool = False) -> List[str]:
    """Format TODOs section with size-based condensation."""
    if is_large_codebase:
        # Condensed format for large codebases
        high_priority = [t for t in todos if t['priority'] == 'high']
        medium_priority = [t for t in todos if t['priority'] == 'medium']
        
        result = []
        if high_priority:
            result.append(f"- High priority TODOs: {len(high_priority)}")
            # Show only first 3 high priority TODOs
            for todo in high_priority[:3]:
                file_short = todo['file'].split('/')[-1]  # Just filename
                result.append(f"  * {file_short}: {todo['text'][:60]}...")
            if len(high_priority) > 3:
                result.append(f"  * ... and {len(high_priority) - 3} more high priority TODOs")
        
        if medium_priority:
            result.append(f"- Medium priority TODOs: {len(medium_priority)}")
        
        low_priority = len(todos) - len(high_priority) - len(medium_priority)
        if low_priority > 0:
            result.append(f"- Low priority TODOs: {low_priority}")
        
        return result
    else:
        # Full format for small codebases
        return [_format_todo(todo) for todo in todos]

def _format_file_analysis(filename: str, analysis: dict, is_large_codebase: bool = False) -> List[str]:
    """Format file analysis with improved error handling."""
    sections = [f"  {filename}"]
    metrics = analysis.get('metrics', {})

    # Basic metrics
    sections.append(f"    Lines: {metrics.get('loc', 0)}")
    if 'complexity' in metrics:
        sections.append(f"    Complexity: {metrics['complexity']}")

    # Handle errors with standardized format (skip for large codebases unless critical)
    if analysis.get('errors') and not is_large_codebase:
        sections.append("\n    ERRORS:")
        for error in analysis['errors']:
            if 'line' in error:
                sections.append(f"      Line {error['line']}: {error['text']}")
            else:
                sections.append(f"      {error['type'].replace('_', ' ').title()}: {error['text']}")

    # Type-specific information
    if analysis['type'] == 'python':
        sections.extend(_format_python_file(analysis, is_large_codebase))
    elif analysis['type'] == 'sql':
        sections.extend(_format_sql_file(analysis, is_large_codebase))
    elif analysis['type'] == 'javascript':
        sections.extend(_format_js_file(analysis, is_large_codebase))

    # Format imports (skip for large codebases to reduce noise)
    if analysis.get('imports') and not is_large_codebase:
        sections.append("\n    IMPORTS:")
        sections.extend(f"      {imp}" for imp in sorted(analysis['imports']))

    # Format TODOs (always show but condensed for large codebases)
    if analysis.get('todos'):
        sections.append("\n    TODOS:")
        if is_large_codebase:
            # Just count and show high priority ones
            high_priority = [t for t in analysis['todos'] if t.get('priority') == 'high']
            if high_priority:
                for todo in high_priority:
                    sections.append(f"      Line {todo['line']}: {todo['text'][:50]}...")
            else:
                sections.append(f"      {len(analysis['todos'])} TODOs present")
        else:
            for todo in sorted(analysis['todos'], key=lambda x: x['line']):
                sections.append(f"      Line {todo['line']}: {todo['text']}")

    return sections

def _format_python_file(analysis: dict, is_large_codebase: bool = False) -> List[str]:
    """Format Python-specific file information with conditional detail based on repo size."""
    sections = []

    if analysis.get('classes'):
        sections.append('\nCLASSES:')
        for cls in sorted(analysis['classes'], key=lambda x: x.get('line_number', 0)):
            if is_large_codebase:
                # Compact format for large repos
                bases_info = f" extends {', '.join(cls['bases'])}" if cls.get('bases') else ""
                sections.append(f"  {cls['name']}{bases_info}")
            else:
                # Detailed format for small repos
                sections.append(f"  {cls['name']}:")
                if 'line_number' in cls:
                    sections.append(f"    Line: {cls['line_number']}")
                if cls.get('bases'):
                    sections.append(f"    Inherits: {', '.join(cls['bases'])}")
                if cls.get('docstring'):
                    sections.append(f"    Doc: {cls['docstring'].split(chr(10))[0]}")

            # Handle different method types
            if cls.get('methods'):
                methods = cls['methods']
                if isinstance(methods[0], dict):
                    # Group methods by type
                    instance_methods = []
                    class_methods = []
                    static_methods = []
                    property_methods = []

                    for method in methods:
                        if method.get('type') == 'class' or method.get('is_classmethod'):
                            class_methods.append(method['name'])
                        elif method.get('type') == 'static' or method.get('is_staticmethod'):
                            static_methods.append(method['name'])
                        elif method.get('type') == 'property' or method.get('is_property'):
                            property_methods.append(method['name'])
                        else:
                            instance_methods.append(method['name'])

                    # Add each method type if present (condensed for large codebases)
                    if is_large_codebase:
                        all_methods = instance_methods + class_methods + static_methods + property_methods
                        if len(all_methods) > 5:
                            sections.append(f"    Methods: {', '.join(all_methods[:5])}, ... ({len(all_methods)} total)")
                        else:
                            sections.append(f"    Methods: {', '.join(all_methods)}")
                    else:
                        if instance_methods:
                            sections.append(f"    Instance methods: {', '.join(instance_methods)}")
                        if class_methods:
                            sections.append(f"    Class methods: {', '.join(class_methods)}")
                        if static_methods:
                            sections.append(f"    Static methods: {', '.join(static_methods)}")
                        if property_methods:
                            sections.append(f"    Properties: {', '.join(property_methods)}")
                else:
                    # Handle simple string method list
                    if is_large_codebase and len(methods) > 5:
                        sections.append(f"    Methods: {', '.join(methods[:5])}, ... ({len(methods)} total)")
                    else:
                        sections.append(f"    Methods: {', '.join(methods)}")

    if analysis.get('functions'):
        sections.append('\nFUNCTIONS:')
        functions_to_show = analysis['functions']
        
        # For large codebases, only show complex functions or limit to first N
        if is_large_codebase:
            complex_functions = [f for f in functions_to_show if f.get('complexity', 0) > 5]
            if complex_functions:
                functions_to_show = complex_functions
            else:
                functions_to_show = functions_to_show[:10]  # Limit to first 10
        
        for func in sorted(functions_to_show, key=lambda x: x.get('line_number', 0)):
            if is_large_codebase:
                # Compact format for large repos
                func_info = f"  {func['name']}("
                if func.get('args'):
                    if isinstance(func['args'][0], dict):
                        args = [arg['name'] for arg in func['args'][:3]]  # Max 3 args
                    else:
                        args = func['args'][:3]
                    if len(func['args']) > 3:
                        args.append("...")
                    func_info += ", ".join(args)
                func_info += ")"
                if func.get('complexity', 0) > 5:
                    func_info += f" [Complex: {func['complexity']}]"
                sections.append(func_info)
            else:
                # Detailed format for small repos
                sections.append(f"  {func['name']}:")
                if 'line_number' in func:
                    sections.append(f"    Line: {func['line_number']}")
                if func.get('args'):
                    # Handle both string and dict arguments
                    args_list = []
                    for arg in func['args']:
                        if isinstance(arg, dict):
                            arg_str = f"{arg['name']}: {arg['type']}" if 'type' in arg else arg['name']
                            args_list.append(arg_str)
                        else:
                            args_list.append(arg)
                    sections.append(f"    Args: {', '.join(args_list)}")
                if func.get('return_type'):
                    sections.append(f"    Returns: {func['return_type']}")
                if func.get('docstring'):
                    sections.append(f"    Doc: {func['docstring'].split(chr(10))[0]}")
                if func.get('decorators'):
                    sections.append(f"    Decorators: {', '.join(func['decorators'])}")
                if func.get('complexity'):
                    sections.append(f"    Complexity: {func['complexity']}")
                if func.get('is_async'):
                    sections.append("    Async: Yes")
        
        # Show summary if we truncated functions for large codebases
        if is_large_codebase and len(analysis['functions']) > len(functions_to_show):
            sections.append(f"  ... and {len(analysis['functions']) - len(functions_to_show)} more functions")

    return sections

def _format_sql_file(analysis: dict, is_large_codebase: bool = False) -> List[str]:
    """Format SQL-specific file information with enhanced object handling."""
    sections = []

    def format_metrics(obj: Dict) -> List[str]:
        """Helper to format metrics consistently."""
        result = []
        if 'lines' in obj.get('metrics', {}):
            result.append(f"      Lines: {obj['metrics']['lines']}")
        if 'complexity' in obj.get('metrics', {}):
            result.append(f"      Complexity: {obj['metrics']['complexity']}")
        return result

    # Format SQL objects (condensed for large codebases)
    sql_objects = analysis.get('objects', [])
    if sql_objects:
        if is_large_codebase:
            # Group by type and show counts
            by_type = {}
            for obj in sql_objects:
                obj_type = obj['type'].upper()
                if obj_type not in by_type:
                    by_type[obj_type] = []
                by_type[obj_type].append(obj['name'])
            
            for obj_type, names in by_type.items():
                sections.append(f"\n    {obj_type}S: {len(names)}")
                if len(names) <= 3:
                    sections.extend(f"      {name}" for name in names)
                else:
                    sections.extend(f"      {name}" for name in names[:3])
                    sections.append(f"      ... and {len(names) - 3} more")
        else:
            # Detailed format for small repos
            for obj in sorted(sql_objects, key=lambda x: x['name']):
                sections.extend([
                    f"\n    {obj['type'].upper()}:",
                    f"      Name: {obj['name']}"
                ])
                sections.extend(format_metrics(obj))

    # Format parameters (always show but limit for large codebases)
    if analysis.get('parameters'):
        sections.append("\n    PARAMETERS:")
        params = analysis['parameters']
        params_to_show = params[:5] if is_large_codebase else params
        
        for param in sorted(params_to_show, key=lambda x: x['name']):
            param_text = f"      @{param['name']} ({param['data_type']}"
            if 'default' in param:
                param_text += f", default={param['default']}"
            param_text += ")"
            if 'description' in param and not is_large_codebase:
                param_text += f" -- {param['description']}"
            sections.append(param_text)
        
        if is_large_codebase and len(params) > 5:
            sections.append(f"      ... and {len(params) - 5} more parameters")

    # Format dependencies (limit for large codebases)
    if analysis.get('dependencies'):
        sections.append("\n    DEPENDENCIES:")
        deps = analysis['dependencies']
        if is_large_codebase and len(deps) > 10:
            sections.extend(f"      {dep}" for dep in sorted(deps)[:10])
            sections.append(f"      ... and {len(deps) - 10} more dependencies")
        else:
            sections.extend(f"      {dep}" for dep in sorted(deps))

    # Format comments (skip for large codebases)
    if analysis.get('comments') and not is_large_codebase:
        sections.append("\n    COMMENTS:")
        for comment in sorted(analysis['comments'], key=lambda x: x['line']):
            sections.append(f"      Line {comment['line']}: {comment['text']}")

    return sections

def _format_js_file(analysis: dict, is_large_codebase: bool = False) -> List[str]:
    """Format JavaScript-specific file information with enhanced data."""
    sections = []

    # Skip imports/exports for large codebases to reduce noise
    if not is_large_codebase:
        if analysis.get('imports'):
            sections.append('\n    IMPORTS:')
            sections.extend(f'      {imp}' for imp in sorted(analysis['imports']))

        if analysis.get('exports'):
            sections.append('\n    EXPORTS:')
            sections.extend(f'      {exp}' for exp in sorted(analysis['exports']))

    # React Components (always show but condensed for large codebases)
    if analysis.get('components'):
        sections.append('\n    REACT COMPONENTS:')
        components = analysis['components']
        
        if is_large_codebase and len(components) > 5:
            for comp in components[:5]:
                comp_type = comp.get('type', 'function')
                sections.append(f'      {comp["name"]} ({comp_type})')
            sections.append(f'      ... and {len(components) - 5} more components')
        else:
            for comp in components:
                comp_type = comp.get('type', 'function')
                jsx_status = ' (with JSX)' if comp.get('has_jsx') else ''
                line_info = f' - Line {comp["line_number"]}' if not is_large_codebase else ''
                sections.append(f'      {comp["name"]} ({comp_type}{jsx_status}){line_info}')

    # React Hooks (condensed for large codebases)
    if analysis.get('hooks'):
        sections.append('\n    REACT HOOKS:')
        built_in_hooks = []
        custom_hooks = []

        for hook in analysis['hooks']:
            hook_name = hook["name"]
            if not is_large_codebase:
                hook_name += f' - Line {hook["line_number"]}'
            
            if hook.get('is_custom'):
                custom_hooks.append(hook_name)
            else:
                built_in_hooks.append(hook_name)

        if built_in_hooks:
            if is_large_codebase:
                sections.append(f'      Built-in hooks: {", ".join(built_in_hooks)}')
            else:
                sections.append('      Built-in hooks:')
                sections.extend(f'        {hook}' for hook in built_in_hooks)

        if custom_hooks:
            if is_large_codebase:
                sections.append(f'      Custom hooks: {", ".join(custom_hooks)}')
            else:
                sections.append('      Custom hooks:')
                sections.extend(f'        {hook}' for hook in custom_hooks)

    # TypeScript Interfaces (always show but condensed)
    if analysis.get('interfaces'):
        sections.append('\n    INTERFACES:')
        interfaces = analysis['interfaces']
        
        if is_large_codebase and len(interfaces) > 5:
            for interface in interfaces[:3]:
                extends_part = f' extends {interface["extends"]}' if interface.get('extends') else ''
                sections.append(f'      {interface["name"]}{extends_part}')
            sections.append(f'      ... and {len(interfaces) - 3} more interfaces')
        else:
            for interface in interfaces:
                extends_part = f' extends {interface["extends"]}' if interface.get('extends') else ''
                line_info = f' - Line {interface["line_number"]}' if not is_large_codebase else ''
                sections.append(f'      {interface["name"]}{extends_part}{line_info}')

    # TypeScript Types (show only for small codebases)
    if analysis.get('types') and not is_large_codebase:
        sections.append('\n    TYPE ALIASES:')
        for type_def in analysis['types']:
            sections.append(f'      {type_def["name"]} = {type_def["definition"]} - Line {type_def["line_number"]}')

    # Functions (limit for large codebases)
    if analysis.get('functions'):
        sections.append("\n    FUNCTIONS:")
        functions = analysis['functions']
        
        if is_large_codebase:
            # Show only complex functions or limit count
            complex_functions = [f for f in functions if f.get('complexity', 0) > 5]
            functions_to_show = complex_functions if complex_functions else functions[:8]
            
            for func in functions_to_show:
                func_signature = f"{func['name']}({', '.join(func.get('params', [])[:3])})"  # Limit params
                if len(func.get('params', [])) > 3:
                    func_signature = func_signature[:-1] + ", ...)"
                if func.get('is_async'):
                    func_signature = f"async {func_signature}"
                sections.append(f"      {func_signature}")
            
            if len(functions) > len(functions_to_show):
                sections.append(f"      ... and {len(functions) - len(functions_to_show)} more functions")
        else:
            for func in functions:
                func_signature = f"{func['name']}({', '.join(func.get('params', []))})"
                if func.get('return_type'):
                    func_signature += f": {func['return_type']}"
                if func.get('is_async'):
                    func_signature = f"async {func_signature}"
                sections.append(f"      {func_signature} - Line {func['line_number']}")

    # Classes (condensed for large codebases)
    if analysis.get('classes'):
        sections.append('\n    CLASSES:')
        classes = analysis['classes']
        
        if is_large_codebase and len(classes) > 3:
            for cls in classes[:3]:
                extends_part = f' extends {cls["extends"]}' if cls.get('extends') else ''
                sections.append(f'      {cls["name"]}{extends_part}')
            sections.append(f'      ... and {len(classes) - 3} more classes')
        else:
            for cls in classes:
                sections.append(f'      {cls["name"]}:')
                if 'line_number' in cls and not is_large_codebase:
                    sections.append(f'        Line: {cls["line_number"]}')
                if cls.get('extends'):
                    sections.append(f'        Extends: {cls["extends"]}')
                if cls.get('methods'):
                    if is_large_codebase and len(cls['methods']) > 5:
                        sections.append(f'        Methods: {", ".join(cls["methods"][:5])}, ... ({len(cls["methods"])} total)')
                    else:
                        sections.append(f'        Methods: {", ".join(cls["methods"])}')

    return sections

def _format_todo(todo: dict) -> str:
    """Format a TODO entry."""
    return f"- [{todo['priority']}] {todo['file']}: {todo['text']}"