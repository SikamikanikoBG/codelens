from typing import Dict, List
from ..analyzer.base import AnalysisResult

def format_analysis(result: AnalysisResult) -> str:
    """Format analysis results with tree structure."""
    sections = []

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

    # NEW: Configuration Summary
    if 'configuration' in result.summary:
        sections.extend([
            "PROJECT CONFIGURATION:",
            _format_configuration(result.summary['configuration']),
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

def _format_configuration(config: dict) -> str:
    """Format configuration information."""
    config_lines = []

    for config_file, info in config.items():
        if info and 'error' not in info:
            config_lines.append(f"  {config_file}:")

            if config_file == 'package.json':
                if info.get('framework_indicators'):
                    config_lines.append(f"    Frameworks: {', '.join(info['framework_indicators'])}")
                if info.get('scripts'):
                    config_lines.append(f"    Scripts: {', '.join(info['scripts'])}")
                if info.get('dependencies'):
                    config_lines.append(f"    Dependencies: {len(info['dependencies'])} packages")

            elif config_file == 'tsconfig.json':
                if info.get('target'):
                    config_lines.append(f"    Target: {info['target']}")
                if info.get('jsx'):
                    config_lines.append(f"    JSX: {info['jsx']}")
                if info.get('strict'):
                    config_lines.append(f"    Strict mode: {info['strict']}")

            elif config_file == 'README.md':
                config_lines.append(f"    Summary: {info['summary'][:100]}...")

        elif info and 'error' in info:
            config_lines.append(f"  {config_file}: {info['error']}")

    return '\n'.join(config_lines) if config_lines else "  No configuration files found"

def _format_file_analysis(filename: str, analysis: dict) -> List[str]:
    """Format file analysis with improved error handling."""
    sections = [f"  {filename}"]
    metrics = analysis.get('metrics', {})

    # Basic metrics
    sections.append(f"    Lines: {metrics.get('loc', 0)}")
    if 'complexity' in metrics:
        sections.append(f"    Complexity: {metrics['complexity']}")

    # Handle errors with standardized format
    if analysis.get('errors'):
        sections.append("\n    ERRORS:")
        for error in analysis['errors']:
            if 'line' in error:
                sections.append(f"      Line {error['line']}: {error['text']}")
            else:
                sections.append(f"      {error['type'].replace('_', ' ').title()}: {error['text']}")

    # Type-specific information
    if analysis['type'] == 'python':
        sections.extend(_format_python_file(analysis))
    elif analysis['type'] == 'sql':
        sections.extend(_format_sql_file(analysis))
    elif analysis['type'] == 'javascript':
        sections.extend(_format_js_file(analysis))

    # Format imports
    if analysis.get('imports'):
        sections.append("\n    IMPORTS:")
        sections.extend(f"      {imp}" for imp in sorted(analysis['imports']))

    # Format TODOs
    if analysis.get('todos'):
        sections.append("\n    TODOS:")
        for todo in sorted(analysis['todos'], key=lambda x: x['line']):
            sections.append(f"      Line {todo['line']}: {todo['text']}")

    return sections

def _format_python_file(analysis: dict) -> List[str]:
    """Format Python-specific file information with conditional detail based on repo size."""
    sections = []

    # Check if this is a large repo (>10K LOC total) - skip detailed code snippets
    total_loc = analysis.get('_repo_total_loc', 0)
    skip_details = total_loc > 10000

    if analysis.get('classes'):
        sections.append('\nCLASSES:')
        for cls in sorted(analysis['classes'], key=lambda x: x.get('line_number', 0)):
            if skip_details:
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

                    # Add each method type if present
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
                    sections.append(f"    Methods: {', '.join(methods)}")

    if analysis.get('functions'):
        sections.append('\nFUNCTIONS:')
        for func in sorted(analysis['functions'], key=lambda x: x.get('line_number', 0)):
            if skip_details:
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

    return sections

def _format_sql_file(analysis: dict) -> List[str]:
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

    # Format SQL objects
    for obj in sorted(analysis.get('objects', []), key=lambda x: x['name']):
        sections.extend([
            f"\n    {obj['type'].upper()}:",
            f"      Name: {obj['name']}"
        ])
        sections.extend(format_metrics(obj))

    # Format parameters with improved handling
    if analysis.get('parameters'):
        sections.append("\n    PARAMETERS:")
        for param in sorted(analysis['parameters'], key=lambda x: x['name']):
            param_text = f"      @{param['name']} ({param['data_type']}"
            if 'default' in param:
                param_text += f", default={param['default']}"
            param_text += ")"
            if 'description' in param:
                param_text += f" -- {param['description']}"
            sections.append(param_text)

    # Format dependencies
    if analysis.get('dependencies'):
        sections.append("\n    DEPENDENCIES:")
        sections.extend(f"      {dep}" for dep in sorted(analysis['dependencies']))

    # Format comments
    if analysis.get('comments'):
        sections.append("\n    COMMENTS:")
        for comment in sorted(analysis['comments'], key=lambda x: x['line']):
            sections.append(f"      Line {comment['line']}: {comment['text']}")

    return sections

def _format_js_file(analysis: dict) -> List[str]:
    """Format JavaScript-specific file information with enhanced data."""
    sections = []

    # Existing imports/exports
    if analysis.get('imports'):
        sections.append('\n    IMPORTS:')
        sections.extend(f'      {imp}' for imp in sorted(analysis['imports']))

    if analysis.get('exports'):
        sections.append('\n    EXPORTS:')
        sections.extend(f'      {exp}' for exp in sorted(analysis['exports']))

    # Enhanced: React Components
    if analysis.get('components'):
        sections.append('\n    REACT COMPONENTS:')
        for comp in analysis['components']:
            comp_type = comp.get('type', 'function')
            jsx_status = ' (with JSX)' if comp.get('has_jsx') else ''
            sections.append(f'      {comp["name"]} ({comp_type}{jsx_status}) - Line {comp["line_number"]}')

    # Enhanced: React Hooks
    if analysis.get('hooks'):
        sections.append('\n    REACT HOOKS:')
        built_in_hooks = []
        custom_hooks = []

        for hook in analysis['hooks']:
            hook_info = f'{hook["name"]} - Line {hook["line_number"]}'
            if hook.get('is_custom'):
                custom_hooks.append(hook_info)
            else:
                built_in_hooks.append(hook_info)

        if built_in_hooks:
            sections.append('      Built-in hooks:')
            sections.extend(f'        {hook}' for hook in built_in_hooks)

        if custom_hooks:
            sections.append('      Custom hooks:')
            sections.extend(f'        {hook}' for hook in custom_hooks)

    # Enhanced: TypeScript Interfaces
    if analysis.get('interfaces'):
        sections.append('\n    INTERFACES:')
        for interface in analysis['interfaces']:
            extends_part = f' extends {interface["extends"]}' if interface.get('extends') else ''
            sections.append(f'      {interface["name"]}{extends_part} - Line {interface["line_number"]}')

    # Enhanced: TypeScript Types
    if analysis.get('types'):
        sections.append('\n    TYPE ALIASES:')
        for type_def in analysis['types']:
            sections.append(f'      {type_def["name"]} = {type_def["definition"]} - Line {type_def["line_number"]}')

    # Enhanced functions with more details
    if analysis.get('functions'):
        sections.append("\n    FUNCTIONS:")
        for func in analysis['functions']:
            func_signature = f"{func['name']}({', '.join(func.get('params', []))})"
            if func.get('return_type'):
                func_signature += f": {func['return_type']}"
            if func.get('is_async'):
                func_signature = f"async {func_signature}"
            sections.append(f"      {func_signature} - Line {func['line_number']}")

    # Existing classes with enhancements
    if analysis.get('classes'):
        sections.append('\n    CLASSES:')
        for cls in analysis['classes']:
            sections.append(f'      {cls["name"]}:')
            if 'line_number' in cls:
                sections.append(f'        Line: {cls["line_number"]}')
            if cls.get('extends'):
                sections.append(f'        Extends: {cls["extends"]}')
            if cls.get('methods'):
                sections.append(f'        Methods: {", ".join(cls["methods"])}')

    return sections

def _format_todo(todo: dict) -> str:
    """Format a TODO entry."""
    return f"- [{todo['priority']}] {todo['file']}: {todo['text']}"
