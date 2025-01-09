#!/usr/bin/env python3
"""
LLM Code Lens - CLI Module
Handles command-line interface and coordination of analysis components.
"""

import click
from pathlib import Path
from typing import Dict, List, Union
from rich.console import Console
from .analyzer.base import ProjectAnalyzer, AnalysisResult
from .analyzer.sql import SQLServerAnalyzer
import tiktoken
import traceback
import os
import json

console = Console()

def parse_ignore_file(ignore_file: Path) -> List[str]:
    """Parse .llmclignore file and return list of patterns."""
    if not ignore_file.exists():
        return []

    patterns = []
    try:
        with ignore_file.open() as f:
            for line in f:
                line = line.strip()
                # Skip empty lines and comments
                if line and not line.startswith('#'):
                    patterns.append(line)
    except Exception as e:
        print(f"Warning: Error reading {ignore_file}: {e}")

    return patterns

def should_ignore(path: Path, ignore_patterns: List[str]) -> bool:
    """Determine if a file or directory should be ignored based on patterns."""
    for pattern in ignore_patterns:
        if pattern in str(path):
            return True
    return False

def is_binary(file_path: Path) -> bool:
    """Check if a file is binary."""
    try:
        with file_path.open('rb') as f:
            for block in iter(lambda: f.read(1024), b''):
                if b'\0' in block:
                    return True
    except Exception:
        return True
    return False

def split_content_by_tokens(content: str, chunk_size: int = 100000) -> List[str]:
    """
    Split content into chunks based on token count.
    Falls back to line-based splitting if token splitting fails.
    """
    try:
        encoder = tiktoken.get_encoding("cl100k_base")
        tokens = encoder.encode(content)

        # Split into chunks
        chunks = []
        for i in range(0, len(tokens), chunk_size):
            chunk_tokens = tokens[i:i + chunk_size]
            chunk_content = encoder.decode(chunk_tokens)
            chunks.append(chunk_content)

        return chunks
    except Exception as e:
        console.print(f"[yellow]Warning during token splitting: {str(e)}[/]")
        # Fallback to simple line-based splitting
        lines = content.splitlines()
        chunks = []
        current_chunk = []
        current_size = 0

        for line in lines:
            line_size = len(line.encode('utf-8'))
            if current_size + line_size > 4000:
                chunks.append('\n'.join(current_chunk))
                current_chunk = [line]
                current_size = line_size
            else:
                current_chunk.append(line)
                current_size += line_size

        if current_chunk:
            chunks.append('\n'.join(current_chunk))

        return chunks

def export_full_content(path: Path, output_dir: Path, ignore_patterns: List[str]) -> None:
    """Export full content of all files in separate token-limited files."""
    file_content = []

    # Export file system content
    for file_path in path.rglob('*'):
        if file_path.is_file() and not should_ignore(file_path, ignore_patterns) and not is_binary(file_path):
            try:
                content = file_path.read_text(encoding='utf-8')
                file_content.append(f"\nFILE: {file_path}\n{'='*80}\n{content}\n")
            except Exception as e:
                console.print(f"[yellow]Warning: Error reading {file_path}: {str(e)}[/]")
                continue

    # Combine all content
    full_content = "\n".join(file_content)

    # Split and write content
    chunks = split_content_by_tokens(full_content)
    for i, chunk in enumerate(chunks, 1):
        output_file = output_dir / f'full_{i}.txt'
        try:
            output_file.write_text(chunk, encoding='utf-8')
            console.print(f"[green]Created full content file: {output_file}[/]")
        except Exception as e:
            console.print(f"[yellow]Warning: Error writing {output_file}: {str(e)}[/]")

def export_sql_content(sql_results: dict, output_dir: Path) -> None:
    """Export full content of SQL objects in separate token-limited files."""
    file_content = []

    # Process stored procedures
    for proc in sql_results.get('stored_procedures', []):
        content = f"""
STORED PROCEDURE: [{proc['schema']}].[{proc['name']}]
{'='*80}
{proc['definition']}
"""
        file_content.append(content)

    # Process views
    for view in sql_results.get('views', []):
        content = f"""
VIEW: [{view['schema']}].[{view['name']}]
{'='*80}
{view['definition']}
"""
        file_content.append(content)

    # Process functions
    for func in sql_results.get('functions', []):
        content = f"""
FUNCTION: [{func['schema']}].[{func['name']}]
{'='*80}
{func['definition']}
"""
        file_content.append(content)

    # Split and write content
    if file_content:
        full_content = "\n".join(file_content)
        chunks = split_content_by_tokens(full_content)

        for i, chunk in enumerate(chunks, 1):
            output_file = output_dir / f'sql_full_{i}.txt'
            try:
                output_file.write_text(chunk, encoding='utf-8')
                console.print(f"[green]Created SQL content file: {output_file}[/]")
            except Exception as e:
                console.print(f"[yellow]Warning: Error writing {output_file}: {str(e)}[/]")

def _combine_results(results: List[Union[dict, AnalysisResult]]) -> AnalysisResult:
    """Combine multiple analysis results into a single result."""
    combined = {
        'summary': {
            'project_stats': {
                'total_files': 0,
                'total_sql_objects': 0,
                'by_type': {},
                'lines_of_code': 0,
                'avg_file_size': 0
            },
            'code_metrics': {
                'functions': {
                    'count': 0,
                    'with_docs': 0,
                    'complex': 0
                },
                'classes': {
                    'count': 0,
                    'with_docs': 0
                },
                'sql_objects': {
                    'procedures': 0,
                    'views': 0,
                    'functions': 0
                },
                'imports': {
                    'count': 0,
                    'unique': set()
                }
            },
            'maintenance': {
                'todos': [],
                'comments_ratio': 0,
                'doc_coverage': 0
            },
            'structure': {
                'directories': set(),
                'entry_points': [],
                'core_files': [],
                'sql_dependencies': []
            }
        },
        'insights': [],
        'files': {}
    }

    for result in results:
        if isinstance(result, AnalysisResult):
            _combine_fs_results(combined, result)
        else:
            _combine_sql_results(combined, result)

    # Calculate final metrics
    total_items = (combined['summary']['project_stats']['total_files'] +
                  combined['summary']['project_stats']['total_sql_objects'])

    if total_items > 0:
        combined['summary']['project_stats']['avg_file_size'] = (
            combined['summary']['project_stats']['lines_of_code'] / total_items
        )

    # Convert sets to lists for JSON serialization
    combined['summary']['code_metrics']['imports']['unique'] = list(
        combined['summary']['code_metrics']['imports']['unique']
    )
    combined['summary']['structure']['directories'] = list(
        combined['summary']['structure']['directories']
    )

    # Calculate documentation coverage
    total_items = (combined['summary']['code_metrics']['functions']['count'] +
                  combined['summary']['code_metrics']['classes']['count'])
    if total_items > 0:
        docs = (combined['summary']['code_metrics']['functions']['with_docs'] +
               combined['summary']['code_metrics']['classes']['with_docs'])
        combined['summary']['maintenance']['doc_coverage'] = (docs / total_items) * 100

    return AnalysisResult(**combined)

def _combine_fs_results(combined: dict, result: AnalysisResult) -> None:
    """Combine file system analysis results."""
    # Update project stats
    combined['summary']['project_stats']['total_files'] += (
        result.summary['project_stats']['total_files']
    )
    combined['summary']['project_stats']['lines_of_code'] += (
        result.summary['project_stats']['lines_of_code']
    )

    # Merge file types
    for ext, count in result.summary['project_stats']['by_type'].items():
        combined['summary']['project_stats']['by_type'][ext] = (
            combined['summary']['project_stats']['by_type'].get(ext, 0) + count
        )

    # Update code metrics
    metrics = result.summary.get('code_metrics', {})
    for metric_type in ['functions', 'classes']:
        if metric_type in metrics:
            # Update counts
            combined['summary']['code_metrics'][metric_type]['count'] += (
                metrics[metric_type].get('count', 0)
            )
            # Update documented counts
            combined['summary']['code_metrics'][metric_type]['with_docs'] += (
                metrics[metric_type].get('with_docs', 0)
            )
            # Handle complex metric for functions
            if metric_type == 'functions':
                combined['summary']['code_metrics']['functions']['complex'] += (
                    metrics[metric_type].get('complex', 0)
                )

    # Update imports
    if 'imports' in metrics:
        combined['summary']['code_metrics']['imports']['count'] += metrics['imports'].get('count', 0)
        if 'unique' in metrics['imports']:
            combined['summary']['code_metrics']['imports']['unique'].update(
                metrics['imports']['unique']
            )

    # Update maintenance info
    if 'maintenance' in result.summary:
        if 'todos' in result.summary['maintenance']:
            combined['summary']['maintenance']['todos'].extend(
                result.summary['maintenance']['todos']
            )

    # Update structure info
    if 'structure' in result.summary:
        structure = result.summary['structure']
        if 'directories' in structure:
            combined['summary']['structure']['directories'].update(
                structure['directories']
            )
        if 'entry_points' in structure:
            combined['summary']['structure']['entry_points'].extend(
                structure['entry_points']
            )
        if 'core_files' in structure:
            combined['summary']['structure']['core_files'].extend(
                structure['core_files']
            )

    # Merge insights and files
    combined['insights'].extend(result.insights)
    combined['files'].update(result.files)

def _combine_sql_results(combined: dict, result: dict) -> None:
    """Combine SQL analysis results."""
    # Update SQL object counts
    proc_count = len(result.get('stored_procedures', []))
    view_count = len(result.get('views', []))
    func_count = len(result.get('functions', []))

    combined['summary']['project_stats']['total_sql_objects'] += (
        proc_count + view_count + func_count
    )

    combined['summary']['code_metrics']['sql_objects']['procedures'] += proc_count
    combined['summary']['code_metrics']['sql_objects']['views'] += view_count
    combined['summary']['code_metrics']['sql_objects']['functions'] += func_count

    # Update total lines of code
    total_sql_lines = sum(
        obj.get('metrics', {}).get('lines', 0)
        for obj_type in ['stored_procedures', 'views', 'functions']
        for obj in result.get(obj_type, [])
    )
    combined['summary']['project_stats']['lines_of_code'] += total_sql_lines

    # Add SQL-specific insights
    if proc_count > 0:
        combined['insights'].append(f"Found {proc_count} stored procedures")
    if view_count > 0:
        combined['insights'].append(f"Found {view_count} views")
    if func_count > 0:
        combined['insights'].append(f"Found {func_count} SQL functions")

    # Add high-complexity SQL objects to insights
    complex_objects = [
        f"{obj['name']} ({obj['type']})"
        for obj_type in ['stored_procedures', 'views', 'functions']
        for obj in result.get(obj_type, [])
        if obj.get('metrics', {}).get('complexity', 0) > 5
    ]
    if complex_objects:
        combined['insights'].append(
            f"Complex SQL objects detected: {', '.join(complex_objects)}"
        )

    # Collect SQL dependencies
    deps = set()
    for obj_type in ['stored_procedures', 'views', 'functions']:
        for obj in result.get(obj_type, []):
            deps.update(obj.get('dependencies', []))

    if deps:
        combined['summary']['structure']['sql_dependencies'].extend(deps)

    # Add SQL objects to files dict
    for proc in result.get('stored_procedures', []):
        key = f"sql://{proc['schema']}.{proc['name']}"
        combined['files'][key] = {
            'type': 'stored_procedure',
            'content': proc['definition'],
            'metrics': proc['metrics'],
            'todos': proc['todos'],
            'comments': proc['comments'],
            'parameters': proc['parameters'],
            'dependencies': proc['dependencies']
        }

    for view in result.get('views', []):
        key = f"sql://{view['schema']}.{view['name']}"
        combined['files'][key] = {
            'type': 'view',
            'content': view['definition'],
            'metrics': view['metrics'],
            'todos': view['todos'],
            'comments': view['comments'],
            'dependencies': view['dependencies']
        }

    for func in result.get('functions', []):
        key = f"sql://{func['schema']}.{func['name']}"
        combined['files'][key] = {
            'type': 'function',
            'content': func['definition'],
            'metrics': func['metrics'],
            'todos': func['todos'],
            'comments': func['comments'],
            'parameters': func['parameters'],
            'dependencies': func['dependencies']
        }

def _format_sql_parameters(params: List[dict]) -> str:
    """Format SQL parameters for full content export."""
    if not params:
        return "None"

    formatted_params = []
    for param in params:
        param_str = f"@{param['name']} {param['data_type']}"
        if 'default' in param:
            param_str += f" = {param['default']}"
        if 'description' in param:
            param_str += f" -- {param['description']}"
        formatted_params.append(param_str)

    return "\n".join(formatted_params)

def _format_sql_dependencies(dependencies: List[str]) -> str:
    """Format SQL dependencies for full content export."""
    if not dependencies:
        return "None"
    return "\n".join(f"- {dep}" for dep in dependencies)

@click.command()
@click.argument('path', type=click.Path(exists=True), default='.')
@click.option('--output', '-o', help='Output directory', default='.codelens')
@click.option('--format', '-f', type=click.Choice(['txt', 'json']), default='txt')
@click.option('--full', is_flag=True, help='Export full file/object contents in separate files')
@click.option('--debug', is_flag=True, help='Enable debug output')
@click.option('--sql-server', help='SQL Server connection string')
@click.option('--sql-database', help='SQL Database to analyze')
@click.option('--sql-config', help='Path to SQL configuration file')
@click.option('--exclude', '-e', multiple=True, help='Patterns to exclude (can be used multiple times)')
def main(path: str, output: str, format: str, full: bool, debug: bool,
         sql_server: str, sql_database: str, sql_config: str, exclude: tuple):
    """Analyze code and generate LLM-friendly context."""
    try:
        console.print("[bold blue]🔍 CodeLens Analysis Starting...[/]")

        if debug:
            console.print(f"Analyzing path: {path}")

        # Convert paths
        path = Path(path).resolve()
        output_path = Path(output).resolve()

        # Clean and create output directory
        if output_path.exists():
            try:
                # Remove old output directory and its contents
                for item in output_path.iterdir():
                    if item.is_file():
                        item.unlink()
                    elif item.is_dir():
                        import shutil
                        shutil.rmtree(item)
                output_path.rmdir()
            except Exception as e:
                console.print(f"[yellow]Warning: Could not fully clean output directory: {str(e)}[/]")
                if debug:
                    console.print(traceback.format_exc())

        # Create fresh output directory
        output_path.mkdir(parents=True, exist_ok=True)

        results = []

        # Load SQL configuration if provided
        if sql_config:
            try:
                with open(sql_config) as f:
                    sql_settings = json.load(f)
                sql_server = sql_settings.get('server')
                sql_database = sql_settings.get('database')

                # Set environment variables if provided in config
                for key, value in sql_settings.get('env', {}).items():
                    os.environ[key] = value
            except Exception as e:
                console.print(f"[yellow]Warning: Error loading SQL config: {str(e)}[/]")
                if debug:
                    console.print(traceback.format_exc())

        # Run SQL analysis if requested
        if sql_server or sql_database or os.getenv('MSSQL_SERVER'):
            console.print("[bold blue]📊 Starting SQL Analysis...[/]")
            analyzer = SQLServerAnalyzer()
            try:
                analyzer.connect(sql_server)  # Will use env vars if not provided
                if sql_database:
                    console.print(f"[blue]Analyzing database: {sql_database}[/]")
                    sql_result = analyzer.analyze_database(sql_database)
                    results.append(sql_result)

                    if full:
                        console.print("[blue]Exporting SQL content...[/]")
                        export_sql_content(sql_result, output_path)
                else:
                    # Get all databases the user has access to
                    databases = analyzer.list_databases()
                    for db in databases:
                        console.print(f"[blue]Analyzing database: {db}[/]")
                        sql_result = analyzer.analyze_database(db)
                        results.append(sql_result)

                        if full:
                            console.print(f"[blue]Exporting SQL content for {db}...[/]")
                            export_sql_content(sql_result, output_path)

            except Exception as e:
                console.print(f"[yellow]Warning during SQL analysis: {str(e)}[/]")
                if debug:
                    console.print(traceback.format_exc())

        # Run file system analysis
        console.print("[bold blue]📁 Starting File System Analysis...[/]")
        analyzer = ProjectAnalyzer()
        fs_results = analyzer.analyze(path)
        results.append(fs_results)

        # Combine results
        combined_results = _combine_results(results)

        if debug:
            console.print("[blue]Analysis complete, writing results...[/]")

        # Write results
        result_file = output_path / f'analysis.{format}'
        with open(result_file, 'w', encoding='utf-8') as f:
            if format == 'txt':
                content = combined_results.to_text()
            else:
                content = combined_results.to_json()
            f.write(content)

        console.print(f"[bold green]✨ Analysis saved to {result_file}[/]")

        # Handle full content export
        if full:
            console.print("[bold blue]📦 Exporting full contents...[/]")
            try:
                ignore_patterns = parse_ignore_file(Path('.llmclignore')) + list(exclude)
                export_full_content(path, output_path, ignore_patterns)
                console.print("[bold green]✨ Full content export complete![/]")
            except Exception as e:
                console.print(f"[yellow]Warning during full export: {str(e)}[/]")
                if debug:
                    console.print(traceback.format_exc())

        return 0

    except Exception as e:
        console.print("[bold red]Error occurred:[/]")
        if debug:
            console.print(traceback.format_exc())
        else:
            console.print(f"[bold red]Error: {str(e)}[/]")
        return 1

if __name__ == '__main__':
    main()
