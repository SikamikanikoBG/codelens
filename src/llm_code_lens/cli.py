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
from .version import check_for_newer_version
import tiktoken
import traceback
import os
import json
import shutil
import webbrowser
import subprocess
import sys

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
        # Version control and cache directories
        '.git', '__pycache__', '.pytest_cache', '.idea', '.vscode',
        '.vscode-test', '.nyc_output', '.ipynb_checkpoints', '.tox',

        # Language/framework specific directories
        'node_modules', 'venv', 'env', 'dist', 'build', 'htmlcov',
        '.next', 'next-env.d.ts', 'bin', 'obj', 'DerivedData',
        'vendor', '.bundle', 'target', 'blib', 'pm_to_blib',
        '.dart_tool', 'pkg', 'out', 'coverage',

        # Package lock files
        'package-lock.json', 'yarn.lock', 'pnpm-lock.yaml',
        'Gemfile.lock', 'composer.lock', 'composer.json',

        # Config files
        'tsconfig.json', 'jsconfig.json',

        # System files
        '.DS_Store',

        # Log files
        '*.log', 'npm-debug.log', 'yarn-error.log',

        # Temp/backup files
        '*.tmp', '*.bak', '*.swp', '*.swo', '*.orig',

        # Binary and compiled files
        '*.exe', '*.dll', '*.so', '*.dylib', '*.a', '*.o', '*.obj',
        '*.pdb', '*.idb', '*.ilk', '*.map', '*.ncb', '*.sdf', '*.opensdf',
        '*.lib', '*.class', '*.jar', '*.war', '*.ear', '*.pyc', '*.pyo', '*.pyd',
        '*.py[cod]', '*$py.class', '*.whl', '*.mexw64', '*.test', '*.out',
        '*.rs.bk', '*.build',

        # Document build files
        '*.aux', '*.toc', '*.out', '*.dvi', '*.ps', '*.pdf', '*.lof', '*.lot',
        '*.fls', '*.fdb_latexmk', '*.synctex.gz',

        # Source files that shouldn't normally be ignored
        '*.go',

        # Project files
        '*.csproj', '*.user', '*.suo', '*.sln.docstates', '*.xcodeproj', '*.xcworkspace',

        # CSS files
        '*.css.map', '*.min.css',

        # R files
        '.Rhistory', '.RData', '*.Rout',

        # Utility files
        'pnp.loader.mjs'
    }

    # Check if the path is a directory and should be ignored
    if path.is_dir():
        for pattern in default_ignores:
            if pattern in path.name or any(pattern in part for part in path.parts):
                return True

    # Check default ignores
    for pattern in default_ignores:
        if pattern in path_str or any(pattern in part for part in path.parts):
            return True

    # Check custom ignore patterns
    for pattern in ignore_patterns:
        if pattern in path_str or any(pattern in part for part in path.parts):
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
    # Handle empty content case first
    if not content:
        return [""]

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
    if not chunks:
        return [content]  # Return entire content as one chunk

    return chunks

def delete_and_create_output_dir(output_dir: Path) -> None:
    """Delete the output directory if it exists and recreate it."""
    if output_dir.exists() and output_dir.is_dir():
        # Preserve the menu state file if it exists
        menu_state_file = output_dir / 'menu_state.json'
        menu_state_data = None
        if menu_state_file.exists():
            try:
                with open(menu_state_file, 'r') as f:
                    menu_state_data = f.read()
            except Exception:
                pass

        # Delete the directory
        shutil.rmtree(output_dir)

        # Recreate the directory
        output_dir.mkdir(parents=True, exist_ok=True)

        # Restore the menu state file if we had one
        if menu_state_data:
            try:
                with open(menu_state_file, 'w') as f:
                    f.write(menu_state_data)
            except Exception:
                pass
    else:
        output_dir.mkdir(parents=True, exist_ok=True)

def export_full_content(path: Path, output_dir: Path, ignore_patterns: List[str], exclude_paths: List[Path] = None, include_samples: bool = True) -> None:
    """Export full content of all files with optional sample snippets."""
    file_content = []
    exclude_paths = exclude_paths or []

    # Add configuration summary at the top
    config_summary = _generate_config_summary(path)
    if config_summary:
        file_content.append(f"\nPROJECT CONFIGURATION:\n{'='*80}\n{config_summary}\n")

    # Export file system content
    for file_path in path.rglob('*'):
        # Skip if file should be ignored based on patterns
        if should_ignore(file_path, ignore_patterns) or is_binary(file_path):
            continue

        # Skip if file is in excluded paths from interactive selection
        should_exclude = False
        for exclude_path in exclude_paths:
            if str(file_path).startswith(str(exclude_path)):
                should_exclude = True
                break

        if should_exclude:
            continue

        try:
            content = file_path.read_text(encoding='utf-8')
            file_content.append(f"\nFILE: {file_path}\n{'='*80}\n{content}\n")
        except Exception as e:
            console.print(f"[yellow]Warning: Error reading {file_path}: {str(e)}[/]")
            continue

    # Add sample content from representative files
    if include_samples:
        sample_content = _extract_sample_content(path, ignore_patterns, exclude_paths)
        if sample_content:
            file_content.append(f"\nSAMPLE CODE SNIPPETS:\n{'='*80}\n{sample_content}\n")

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

def _generate_config_summary(path: Path) -> str:
    """Generate a summary of project configuration."""
    from .analyzer.config import analyze_package_json, analyze_tsconfig, extract_readme_summary

    summary_parts = []

    # Package.json summary
    pkg_info = analyze_package_json(path / 'package.json')
    if pkg_info and 'error' not in pkg_info:
        summary_parts.append(f"Project: {pkg_info.get('name', 'Unknown')} v{pkg_info.get('version', '0.0.0')}")
        if pkg_info.get('description'):
            summary_parts.append(f"Description: {pkg_info['description']}")
        if pkg_info.get('framework_indicators'):
            summary_parts.append(f"Frameworks: {', '.join(pkg_info['framework_indicators'])}")
        if pkg_info.get('scripts'):
            summary_parts.append(f"Available scripts: {', '.join(pkg_info['scripts'])}")

    # README summary
    readme_info = extract_readme_summary(path)
    if readme_info:
        summary_parts.append(f"README Summary:\n{readme_info['summary']}")

    return '\n'.join(summary_parts)

def _extract_sample_content(path: Path, ignore_patterns: List[str], exclude_paths: List[Path]) -> str:
    """Extract small samples from different file types."""
    samples = []
    sample_files = {}

    # Collect representative files
    for file_path in path.rglob('*'):
        if should_ignore(file_path, ignore_patterns) or is_binary(file_path):
            continue

        ext = file_path.suffix.lower()
        if ext in ['.js', '.jsx', '.ts', '.tsx', '.py', '.css', '.scss']:
            if ext not in sample_files or len(str(file_path)) < len(str(sample_files[ext])):
                sample_files[ext] = file_path

    # Extract samples
    for ext, file_path in sample_files.items():
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()[:20]  # First 20 lines
                content = ''.join(lines)
                samples.append(f"Sample {ext} ({file_path.name}):\n{content}\n")
        except Exception:
            continue

    return '\n'.join(samples)

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

def _combine_fs_results(combined: dict, result: dict) -> None:
    """Combine file system analysis results."""
    # Update project stats
    stats = result.get('summary', {}).get('project_stats', {})
    combined['summary']['project_stats']['total_files'] += stats.get('total_files', 0)
    combined['summary']['project_stats']['lines_of_code'] += stats.get('lines_of_code', 0)

    # Update code metrics
    metrics = result.get('summary', {}).get('code_metrics', {})
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
    maintenance = result.get('summary', {}).get('maintenance', {})
    combined['summary']['maintenance']['todos'].extend(maintenance.get('todos', []))

    # Update structure info
    structure = result.get('summary', {}).get('structure', {})
    if 'directories' in structure:
        dirs = structure['directories']
        if isinstance(dirs, (set, list)):
            combined['summary']['structure']['directories'].update(dirs)

    # Update insights and files
    if 'insights' in result:
        combined['insights'].extend(result['insights'])
    if 'files' in result:
        combined['files'].update(result['files'])

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
        # Handle SQL results
        if isinstance(result, dict) and ('stored_procedures' in result or 'views' in result):
            _combine_sql_results(combined, result)
        # Handle AnalysisResult objects
        elif isinstance(result, AnalysisResult):
            # Convert AnalysisResult to a simple dict for easier processing
            result_dict = {
                'summary': result.summary,
                'insights': result.insights,
                'files': result.files
            }
            _combine_fs_results(combined, result_dict)
        # Handle plain dictionaries
        else:
            _combine_fs_results(combined, result)

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
    for func in sql_result.get('functions', []):
        key = f"function_{func['name']}"
        combined['files'][key] = func

def open_in_llm_provider(provider: str, output_path: Path, debug: bool = False) -> bool:
    """
    Open the analysis results in a browser with the specified LLM provider.

    Args:
        provider: The LLM provider to use (claude, chatgpt, gemini, none, etc.)
        output_path: Path to the output directory containing analysis files
        debug: Enable debug output

    Returns:
        bool: True if successful, False otherwise
    """
    # Handle 'none' option - return success without opening anything
    if provider and provider.lower() == 'none':
        console.print("[green]Skipping browser opening as requested.[/]")
        return True

    try:
        # Import pyperclip for clipboard operations
        try:
            import pyperclip
            import urllib.parse
        except ImportError:
            console.print("[yellow]Error: The pyperclip package is required for LLM integration.[/]")
            console.print("[yellow]Please install it with: pip install pyperclip[/]")
            return False

        # Define the system prompt
        system_prompt = """You are an experienced developer and software architect.
I'm sharing a codebase (or summary of a codebase) with you.

Your task is to analyze this codebase and be able to convert any question or new feature request into very concrete, actionable, and detailed file-by-file instructions for my developer.

IMPORTANT: All your instructions must be provided in a single, unformatted line for each file. Do not use multiple lines, bullet points, or any other formatting. My developer relies on this specific format to process your instructions correctly.

Your instructions should specify exactly what needs to be done in which file and why, so the developer can implement them with a full understanding of the changes required. Do not skip any information - include all details, just format them as a continuous line of text for each file.

In my next message, I'll tell you about a new request or question about this code.
"""

        # Prepare the complete message with files included
        full_message = system_prompt + "\n\n"

        # Add the analysis file
        analysis_file = output_path / 'analysis.txt'
        if analysis_file.exists():
            full_message += f"# Code Analysis\n\n```\n{analysis_file.read_text(encoding='utf-8')}\n```\n\n"

        # Check if full export is enabled by looking for full_*.txt files
        full_files = list(output_path.glob('full_*.txt'))

        # If full export is enabled, add the content of all full files
        if full_files:
            for file in sorted(full_files):
                full_message += f"# {file.name}\n\n```\n{file.read_text(encoding='utf-8')}\n```\n\n"

            # Add SQL content files if they exist
            sql_files = list(output_path.glob('sql_full_*.txt'))
            for file in sorted(sql_files):
                full_message += f"# {file.name}\n\n```sql\n{file.read_text(encoding='utf-8')}\n```\n\n"

        # Copy the full message to clipboard (for all providers as backup)
        pyperclip.copy(full_message)

        # Open the appropriate provider
        if provider.lower() == 'claude':
            # Open Claude in a new chat
            webbrowser.open("https://claude.ai/new")

            console.print("[green]Claude opened in browser.[/]")
            console.print("[green]The complete analysis with all files has been copied to your clipboard.[/]")
            console.print("[green]Just press Ctrl+V in Claude to paste everything at once![/]")
            return True

        elif provider.lower() == 'chatgpt':
            # For ChatGPT, try to use the query parameter approach
            try:
                # Encode the message for URL
                encoded_message = urllib.parse.quote(full_message)

                # Check if the URL would be too long (most browsers have limits around 2000-8000 chars)
                # We'll use a conservative limit of 2000 characters
                if len(encoded_message) <= 2000:
                    # Use the query parameter approach
                    chatgpt_url = f"https://chatgpt.com/?q={encoded_message}"
                    webbrowser.open(chatgpt_url)

                    console.print("[green]ChatGPT opened in browser with content pre-loaded.[/]")
                    console.print("[green]The content has also been copied to your clipboard as a backup.[/]")
                    console.print("[green]If the content doesn't appear automatically, press Ctrl+V to paste it.[/]")
                else:
                    # Fallback to regular URL if content is too large
                    webbrowser.open("https://chat.openai.com/")

                    console.print("[green]ChatGPT opened in browser.[/]")
                    console.print("[green]The content is too large for URL parameters (browser limitations).[/]")
                    console.print("[green]The complete analysis has been copied to your clipboard.[/]")
                    console.print("[green]Just press Ctrl+V in ChatGPT to paste everything at once![/]")

                if debug:
                    console.print(f"[blue]URL parameter length: {len(encoded_message)} characters[/]")
                    if len(encoded_message) > 2000:
                        console.print("[blue]URL parameter too long, using clipboard only[/]")

                return True
            except Exception as e:
                # Fallback to regular approach if URL encoding fails
                if debug:
                    console.print(f"[yellow]Error with URL parameter approach: {str(e)}[/]")
                    console.print("[yellow]Falling back to clipboard approach[/]")

                webbrowser.open("https://chat.openai.com/")

                console.print("[green]ChatGPT opened in browser.[/]")
                console.print("[green]The complete analysis with all files has been copied to your clipboard.[/]")
                console.print("[green]Just press Ctrl+V in ChatGPT to paste everything at once![/]")
                return True

        elif provider.lower() == 'gemini':
            # Open Gemini
            webbrowser.open("https://gemini.google.com/")

            console.print("[green]Gemini opened in browser.[/]")
            console.print("[green]The complete analysis with all files has been copied to your clipboard.[/]")
            console.print("[green]Just press Ctrl+V in Gemini to paste everything at once![/]")
            return True

        else:
            console.print(f"[yellow]Unsupported LLM provider: {provider}[/]")
            return False

    except Exception as e:
        console.print(f"[red]Error opening in LLM: {str(e)}[/]")
        if debug:
            console.print(traceback.format_exc())
        return False

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
@click.option('--interactive', '-i', is_flag=True, help='Launch interactive selection menu before analysis', default=True, show_default=False)
@click.option('--open-in-llm', help='Open results in LLM provider (claude, chatgpt, gemini, none)', default=None)
@click.option('--respect-gitignore/--ignore-gitignore', default=True, help='Respect .gitignore file patterns (default: enabled)')  # NEW OPTION
def main(path: str, output: str, format: str, full: bool, debug: bool,
         sql_server: str, sql_database: str, sql_config: str, exclude: tuple,
         interactive: bool = True, open_in_llm: str = None, respect_gitignore: bool = True):  # NEW PARAMETER
    """
    Main entry point for the CLI with gitignore support.
    """
    try:
        # Convert to absolute paths
        path = Path(path).resolve()
        output_path = Path(output).resolve()

        # Parse gitignore if enabled
        gitignore_patterns = []
        if respect_gitignore:
            from .utils.gitignore import GitignoreParser  # Import here to avoid circular imports
            gitignore_parser = GitignoreParser(path)
            gitignore_parser.load_gitignore()
            gitignore_patterns = gitignore_parser.get_ignore_patterns()

            if debug and gitignore_patterns:
                console.print(f"[blue]Loaded {len(gitignore_patterns)} patterns from .gitignore[/]")

        # Combine gitignore patterns with custom exclude patterns
        all_ignore_patterns = list(exclude) + gitignore_patterns

        # Update initial settings for menu
        initial_settings = {
            'format': format,
            'full': full,
            'debug': debug,
            'sql_server': sql_server or '',
            'sql_database': sql_database or '',
            'sql_config': sql_config or '',
            'exclude_patterns': all_ignore_patterns,
            'open_in_llm': open_in_llm or '',
            'respect_gitignore': respect_gitignore  # NEW SETTING
        }

        # Launch interactive menu (default behavior)
        try:
            # Import here to avoid circular imports
            from .menu import run_menu
            console.print("[bold blue]🖥️ Launching interactive file selection menu...[/]")
            settings = run_menu(Path(path), initial_settings)

            # Check if user cancelled
            if settings.get('cancelled', False):
                console.print("[yellow]Operation cancelled by user[/]")
                return 0

            # Update paths based on user selection
            path = settings.get('path', path)
            include_paths = settings.get('include_paths', [])
            exclude_paths = settings.get('exclude_paths', [])

            # Update other settings from menu
            format = settings.get('format', format)
            full = settings.get('full', full)
            debug = settings.get('debug', debug)
            sql_server = settings.get('sql_server', sql_server)
            sql_database = settings.get('sql_database', sql_database)
            sql_config = settings.get('sql_config', sql_config)
            exclude = settings.get('exclude', exclude)
            open_in_llm = settings.get('open_in_llm', open_in_llm)

            if debug:
                console.print(f"[blue]Selected path: {path}[/]")
                console.print(f"[blue]Included paths: {len(include_paths)}[/]")
                console.print(f"[blue]Excluded paths: {len(exclude_paths)}[/]")
                console.print(f"[blue]Output format: {format}[/]")
                console.print(f"[blue]Full export: {full}[/]")
                console.print(f"[blue]Debug mode: {debug}[/]")
                console.print(f"[blue]SQL Server: {sql_server}[/]")
                console.print(f"[blue]SQL Database: {sql_database}[/]")
                console.print(f"[blue]Exclude patterns: {exclude}[/]")
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
            try:
                from .analyzer import SQLServerAnalyzer
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
                    console.print("[yellow]SQL analysis will be skipped, but file analysis will continue.[/]")

            except Exception as e:
                console.print(f"[yellow]SQL Server analysis is not available: {str(e)}[/]")
                console.print("[yellow]Install pyodbc and required ODBC drivers to enable this feature.[/]")
                console.print("[yellow]Continuing with file analysis only.[/]")

        # Check for newer version (non-blocking)
        check_for_newer_version()

        # Run file system analysis
        console.print("[bold blue]📁 Starting File System Analysis...[/]")
        analyzer = ProjectAnalyzer()

        # Pass include/exclude paths to analyzer if they were set in interactive mode
        if interactive and (include_paths or exclude_paths):
            # Create a custom file collection function that respects include/exclude paths
            def custom_collect_files(path: Path) -> List[Path]:
                # Get all files that match the analyzer's supported extensions
                files = []
                for file_path in path.rglob('*'):
                    if (file_path.is_file() and
                        file_path.suffix.lower() in analyzer.analyzers):
                        files.append(file_path)

                # Apply include/exclude filters
                filtered_files = []
                excluded_files = []

                for file_path in files:
                    # Check if file should be included based on interactive selection
                    should_include = True
                    exclusion_reason = None

                    # If we have explicit include paths, file must be in one of them
                    if include_paths:
                        should_include = False
                        for include_path in include_paths:
                            if str(file_path).startswith(str(include_path)):
                                should_include = True
                                break
                        if not should_include:
                            exclusion_reason = "Not in include paths"

                    # Check if file is in exclude paths
                    for exclude_path in exclude_paths:
                        if str(file_path).startswith(str(exclude_path)):
                            should_include = False
                            exclusion_reason = f"Excluded by path: {exclude_path}"
                            break

                    if should_include:
                        filtered_files.append(file_path)
                    else:
                        excluded_files.append((str(file_path), exclusion_reason))

                # Log verification information if debug mode is enabled
                if debug:
                    console.print(f"[blue]File collection verification:[/]")
                    console.print(f"[blue]- Total files found: {len(files)}[/]")
                    console.print(f"[blue]- Files included: {len(filtered_files)}[/]")
                    console.print(f"[blue]- Files excluded: {len(excluded_files)}[/]")

                    # Log a sample of excluded files (up to 5) with reasons
                    if excluded_files and len(excluded_files) > 0:
                        console.print("[blue]Sample of excluded files:[/]")
                        for i, (file, reason) in enumerate(excluded_files[:5]):
                            console.print(f"[blue]  {i+1}. {file} - {reason}[/]")
                        if len(excluded_files) > 5:
                            console.print(f"[blue]  ... and {len(excluded_files) - 5} more[/]")

                return filtered_files

            # Replace the method
            analyzer._collect_files = custom_collect_files

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
                export_full_content(path, output_path, ignore_patterns, exclude_paths)
                console.print("[bold green]✨ Full content export complete![/]")
            except Exception as e:
                console.print(f"[yellow]Warning during full export: {str(e)}[/]")
                if debug:
                    console.print(traceback.format_exc())

        # Open in LLM if requested and not 'none'
        if open_in_llm and open_in_llm.lower() != 'none':
            console.print(f"[bold blue]🌐 Opening results in {open_in_llm}...[/]")
            if open_in_llm_provider(open_in_llm, output_path, debug):
                console.print(f"[bold green]✨ Results opened in {open_in_llm}![/]")
            else:
                console.print(f"[yellow]Failed to open results in {open_in_llm}[/]")

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
