#!/usr/bin/env python3
"""
LLM Code Lens - CLI Module
Handles command-line interface and coordination of analysis components.
"""

import click
from pathlib import Path
from typing import Dict, List, Union, Optional
from rich.console import Console
from .analyzer.base import ProjectAnalyzer, AnalysisResult
from .analyzer.sql import SQLServerAnalyzer
import tiktoken
import traceback
import os
import json
import shutil

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

def should_ignore(path: Path, ignore_patterns: Optional[List[str]] = None) -> bool:
    """Determine if a file or directory should be ignored based on patterns."""
    if ignore_patterns is None:
        ignore_patterns = []
        
    path_str = str(path)
    default_ignores = {
        '.git', '__pycache__', '.pytest_cache', '.idea', '.vscode',
        'node_modules', 'venv', 'env', 'dist', 'build', '.tox', 'htmlcov'
    }
    
    # Check default ignores
    for pattern in default_ignores:
        if pattern in path_str:
            return True
    
    # Check custom ignore patterns
    for pattern in ignore_patterns:
        if pattern in path_str:
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
    Handles large content safely by pre-chunking before tokenization.
    
    Args:
        content (str): The content to split
        chunk_size (int): Target size for each chunk in tokens
        
    Returns:
        List[str]: List of content chunks
    """
    if not content:
        return ['']
        
    try:
        # First do a rough pre-chunking by characters to avoid stack overflow
        MAX_CHUNK_CHARS = 100000  # Adjust this based on your needs
        rough_chunks = []
        
        for i in range(0, len(content), MAX_CHUNK_CHARS):
            rough_chunks.append(content[i:i + MAX_CHUNK_CHARS])
            
        encoder = tiktoken.get_encoding("cl100k_base")
        final_chunks = []
        
        # Process each rough chunk
        for rough_chunk in rough_chunks:
            tokens = encoder.encode(rough_chunk)
            
            # Split into smaller chunks based on token count
            for i in range(0, len(tokens), chunk_size):
                chunk_tokens = tokens[i:i + chunk_size]
                chunk_content = encoder.decode(chunk_tokens)
                final_chunks.append(chunk_content)
                
        return final_chunks
        
    except Exception as e:
        # Fallback to line-based splitting
        return _split_by_lines(content, max_chunk_size=chunk_size)

def _split_by_lines(content: str, max_chunk_size: int = 100000) -> List[str]:
    """Split content by lines with a maximum chunk size."""
    lines = content.splitlines(keepends=True)  # Keep line endings
    chunks = []
    current_chunk = []
    current_size = 0
    
    for line in lines:
        line_size = len(line.encode('utf-8'))
        if current_size + line_size > max_chunk_size and current_chunk:
            chunks.append(''.join(current_chunk))
            current_chunk = [line]
            current_size = line_size
        else:
            current_chunk.append(line)
            current_size += line_size
    
    if current_chunk:
        chunks.append(''.join(current_chunk))
        
    # Handle special case where we got no chunks
    if not chunks and content:
        return [content]  # Return entire content as one chunk
        
    return chunks

def delete_and_create_output_dir(output_dir: Path) -> None:
    """Delete the output directory if it exists and recreate it."""
    if output_dir.exists() and output_dir.is_dir():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

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
    chunks = split_content_by_tokens(full_content, chunk_size=100000)
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
        chunks = split_content_by_tokens(full_content, chunk_size=100000)

        for i, chunk in enumerate(chunks, 1):
            output_file = output_dir / f'sql_full_{i}.txt'
            try:
                output_file.write_text(chunk, encoding='utf-8')
                console.print(f"[green]Created SQL content file: {output_file}[/]")
            except Exception as e:
                console.print(f"[yellow]Warning: Error writing {output_file}: {str(e)}[/]")

def _combine_fs_results(combined: dict, result: Union[dict, AnalysisResult]) -> None:
    """Combine file system analysis results."""
    if isinstance(result, AnalysisResult):
        result_dict = result.dict()  # Convert AnalysisResult to dict
    else:
        result_dict = result  # Already a dict

    # Update project stats
    stats = result_dict.get('summary', {}).get('project_stats', {})
    combined['summary']['project_stats']['total_files'] += stats.get('total_files', 0)
    combined['summary']['project_stats']['lines_of_code'] += stats.get('lines_of_code', 0)

    # Update code metrics
    metrics = result_dict.get('summary', {}).get('code_metrics', {})
    for metric_type in ['functions', 'classes']:
        if metric_type in metrics:
            for key in ['count', 'with_docs', 'complex']:
                if key in metrics[metric_type]:
                    combined['summary']['code_metrics'][metric_type][key] += metrics[metric_type][key]

    # Update imports
    if 'imports' in metrics:
        combined['summary']['code_metrics']['imports']['count'] += metrics['imports'].get('count', 0)
        unique_imports = metrics['imports'].get('unique', set())
        if isinstance(unique_imports, (set, list)):
            combined['summary']['code_metrics']['imports']['unique'].update(unique_imports)

    # Update maintenance info
    maintenance = result_dict.get('summary', {}).get('maintenance', {})
    combined['summary']['maintenance']['todos'].extend(maintenance.get('todos', []))
    
    # Update structure info
    structure = result_dict.get('summary', {}).get('structure', {})
    if 'directories' in structure:
        dirs = structure['directories']
        if isinstance(dirs, (set, list)):
            combined['summary']['structure']['directories'].update(dirs)

    # Update insights and files
    if 'insights' in result_dict:
        combined['insights'].extend(result_dict['insights'])
    if 'files' in result_dict:
        combined['files'].update(result_dict['files'])

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
                'functions': {'count': 0, 'with_docs': 0, 'complex': 0},
                'classes': {'count': 0, 'with_docs': 0},
                'sql_objects': {'procedures': 0, 'views': 0, 'functions': 0},
                'imports': {'count': 0, 'unique': set()}
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
        if isinstance(result, dict) and ('stored_procedures' in result or 'views' in result):
            _combine_sql_results(combined, result)
        else:
            # If result is AnalysisResult, convert to dict using to_json and json.loads
            if isinstance(result, AnalysisResult):
                import json
                result_dict = json.loads(result.to_json())
            else:
                result_dict = result
            _combine_fs_results(combined, result_dict)

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

    return AnalysisResult(**combined)


def _combine_sql_results(combined: dict, sql_result: dict) -> None:
    """Combine SQL results with proper object counting."""
    # Count objects
    proc_count = len(sql_result.get('stored_procedures', []))
    view_count = len(sql_result.get('views', []))
    func_count = len(sql_result.get('functions', []))
    
    # Update stats
    combined['summary']['project_stats']['total_sql_objects'] += proc_count + view_count + func_count
    combined['summary']['code_metrics']['sql_objects']['procedures'] += proc_count
    combined['summary']['code_metrics']['sql_objects']['views'] += view_count
    combined['summary']['code_metrics']['sql_objects']['functions'] += func_count
    
    # Add objects to files
    for proc in sql_result.get('stored_procedures', []):
        key = f"stored_proc_{proc['name']}"
        combined['files'][key] = proc
    for view in sql_result.get('views', []):
        key = f"view_{view['name']}"
        combined['files'][key] = view




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
@click.option('--interactive', '-i', is_flag=True, help='Launch interactive selection menu before analysis')
def main(path: str, output: str, format: str, full: bool, debug: bool,
         sql_server: str, sql_database: str, sql_config: str, exclude: tuple, interactive: bool):
    try:
        # Convert to absolute paths
        path = Path(path).resolve()
        output_path = Path(output).resolve()
        
        # Initialize include/exclude paths
        include_paths = []
        exclude_paths = []

        # Launch interactive menu if requested
        if interactive:
            try:
                # Import here to avoid circular imports
                from .menu import run_menu
                console.print("[bold blue]🖥️ Launching interactive file selection menu...[/]")
                settings = run_menu(Path(path))
                
                # Update paths based on user selection
                path = settings.get('path', path)
                include_paths = settings.get('include_paths', [])
                exclude_paths = settings.get('exclude_paths', [])
                
                if debug:
                    console.print(f"[blue]Selected path: {path}[/]")
                    console.print(f"[blue]Included paths: {len(include_paths)}[/]")
                    console.print(f"[blue]Excluded paths: {len(exclude_paths)}[/]")
            except Exception as e:
                console.print(f"[yellow]Warning: Interactive menu failed: {str(e)}[/]")
                if debug:
                    console.print(traceback.format_exc())
                console.print("[yellow]Continuing with default path selection...[/]")

        # Ensure output directory exists
        try:
            delete_and_create_output_dir(output_path)
        except Exception as e:
            console.print(f"[red]Error creating output directory: {str(e)}[/]")
            return 1

        if debug:
            console.print(f"[blue]Output directory: {output_path}[/]")

        # Rest of the main function remains unchanged
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
        
        # Pass include/exclude paths to analyzer if they were set in interactive mode
        if interactive and (include_paths or exclude_paths):
            # Modify the analyzer's _collect_files method to respect include/exclude paths
            original_collect_files = analyzer._collect_files
            
            def filtered_collect_files(self, path: Path) -> List[Path]:
                files = original_collect_files(path)
                filtered_files = []
                
                for file_path in files:
                    # Check if file should be included based on interactive selection
                    should_include = True
                    
                    # If we have explicit include paths, file must be in one of them
                    if include_paths:
                        should_include = False
                        for include_path in include_paths:
                            if str(file_path).startswith(str(include_path)):
                                should_include = True
                                break
                    
                    # Check if file is in exclude paths
                    for exclude_path in exclude_paths:
                        if str(file_path).startswith(str(exclude_path)):
                            should_include = False
                            break
                    
                    if should_include:
                        filtered_files.append(file_path)
                
                return filtered_files
            
            # Replace the method
            analyzer._collect_files = filtered_collect_files.__get__(analyzer, ProjectAnalyzer)
            
            if debug:
                console.print(f"[blue]Using custom file collection with filters[/]")
        
        fs_results = analyzer.analyze(path)
        results.append(fs_results)

        # Combine results
        combined_results = _combine_results(results)

        if debug:
            console.print("[blue]Analysis complete, writing results...[/]")

        # Write results
        result_file = output_path / f'analysis.{format}'
        try:
            # Ensure output directory exists
            output_path.mkdir(parents=True, exist_ok=True)
            
            content = combined_results.to_json() if format == 'json' else combined_results.to_text()
            result_file.write_text(content, encoding='utf-8')
        except Exception as e:
            console.print(f"[red]Error writing results: {str(e)}[/]")
            return 1

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

        # Friendly message to prompt users to give a star
        console.print("\n [bold yellow] ⭐⭐⭐⭐⭐ If you like this tool, please consider giving it a star on GitHub![/]")
        console.print("[bold blue]Visit: https://github.com/SikamikanikoBG/codelens.git[/]")

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
