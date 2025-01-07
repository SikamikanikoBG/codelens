# src/codelens/cli.py
import click
from pathlib import Path
from rich.console import Console
from .analyzer.base import ProjectAnalyzer
import traceback

console = Console()

@click.command()
@click.argument('path', type=click.Path(exists=True), default='.')
@click.option('--output', '-o', help='Output directory', default='.codelens')
@click.option('--format', '-f', type=click.Choice(['txt', 'json']), default='txt')
@click.option('--debug', is_flag=True, help='Enable debug output')
def main(path: str, output: str, format: str, debug: bool):
    """Analyze code and generate LLM-friendly context."""
    try:
        console.print("[bold blue]🔍 CodeLens Analysis Starting...[/]")
        
        if debug:
            console.print(f"Analyzing path: {path}")
        
        analyzer = ProjectAnalyzer()
        results = analyzer.analyze(Path(path))
        
        if debug:
            console.print("Analysis results:", results)
        
        output_path = Path(output)
        output_path.mkdir(exist_ok=True)
        
        result_file = output_path / f'analysis.{format}'
        
        if debug:
            console.print(f"Writing results to: {result_file}")
        
        with open(result_file, 'w') as f:
            if format == 'txt':
                content = results.to_text()
            else:
                content = results.to_json()
            f.write(content)
        
        console.print(f"[bold green]✨ Analysis complete! Results saved to {result_file}[/]")
        
    except Exception as e:
        console.print("[bold red]Error occurred:[/]")
        if debug:
            console.print(traceback.format_exc())
        else:
            console.print(f"[bold red]Error: {str(e)}[/]")
        raise click.Abort()

if __name__ == '__main__':
    main()