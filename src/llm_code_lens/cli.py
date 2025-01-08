import click
import traceback
from pathlib import Path
from typing import Dict, List, Union
from rich.console import Console
from .analyzer.base import ProjectAnalyzer
import tiktoken

console = Console()

def count_tokens(text: str) -> int:
    """Count tokens in text using tiktoken."""
    enc = tiktoken.get_encoding("cl100k_base")
    return len(enc.encode(text))

def split_content_by_tokens(content: str, max_tokens: int = 100000) -> List[str]:
    """Split content into chunks of approximately max_tokens."""
    enc = tiktoken.get_encoding("cl100k_base")
    tokens = enc.encode(content)
    chunks = []
    current_chunk = []
    current_count = 0
    
    for token in tokens:
        current_chunk.append(token)
        current_count += 1
        
        if current_count >= max_tokens:
            # Decode current chunk
            chunks.append(enc.decode(current_chunk))
            current_chunk = []
            current_count = 0
    
    # Add remaining content
    if current_chunk:
        chunks.append(enc.decode(current_chunk))
    
    return chunks

def export_full_content(path: Path, output_dir: Path) -> None:
    """Export full content of all files in separate token-limited files."""
    file_content = []
    
    # Collect all files
    for file_path in path.rglob('*'):
        if file_path.is_file() and not should_ignore(file_path):
            try:
                content = file_path.read_text(encoding='utf-8')
                file_content.append(f"\nFILE: {file_path}\n{'='*80}\n{content}\n")
            except Exception as e:
                console.print(f"[yellow]Warning: Error reading {file_path}: {str(e)}[/]")
                continue
    
    # Combine all content
    full_content = "\n".join(file_content)
    
    # Split into chunks based on token count
    chunks = split_content_by_tokens(full_content)
    
    # Write each chunk to a separate file
    for i, chunk in enumerate(chunks, 1):
        output_file = output_dir / f'full_{i}.txt'
        try:
            output_file.write_text(chunk, encoding='utf-8')
            console.print(f"[green]Created full content file: {output_file}[/]")
        except Exception as e:
            console.print(f"[yellow]Warning: Error writing {output_file}: {str(e)}[/]")

def should_ignore(path: Path) -> bool:
    """Check if path should be ignored."""
    ignore_patterns = {
        '.git', '__pycache__', 'venv', 'env',
        'node_modules', '.idea', '.vscode', '.codelens',
        'dist', 'build', '_build', 'site-packages',
        '.pytest_cache', '.mypy_cache', '.coverage', 'htmlcov'
    }
    return any(part in ignore_patterns for part in path.parts)

@click.command()
@click.argument('path', type=click.Path(exists=True), default='.')
@click.option('--output', '-o', help='Output directory', default='.codelens')
@click.option('--format', '-f', type=click.Choice(['txt', 'json']), default='txt')
@click.option('--full', is_flag=True, help='Export full file contents in separate files')
@click.option('--debug', is_flag=True, help='Enable debug output')
def main(path: str, output: str, format: str, full: bool, debug: bool):
    """Analyze code and generate LLM-friendly context."""
    try:
        console.print("[bold blue]🔍 CodeLens Analysis Starting...[/]")
        
        if debug:
            console.print(f"Analyzing path: {path}")
        
        # Convert paths
        path = Path(path).resolve()
        output_path = Path(output).resolve()
        
        # Create output directory
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Run analysis
        analyzer = ProjectAnalyzer()
        results = analyzer.analyze(path)
        
        if debug:
            console.print("Analysis complete, writing results...")
        
        # Write results
        result_file = output_path / f'analysis.{format}'
        with open(result_file, 'w', encoding='utf-8') as f:
            if format == 'txt':
                content = results.to_text()
            else:
                content = results.to_json()
            f.write(content)
        
        console.print(f"[bold green]✨ Analysis saved to {result_file}[/]")
        
        # Handle full content export
        if full:
            console.print("[bold blue]📦 Exporting full file contents...[/]")
            try:
                export_full_content(path, output_path)
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