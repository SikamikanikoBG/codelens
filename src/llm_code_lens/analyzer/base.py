from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass

@dataclass
class AnalysisResult:
    """Container for analysis results."""
    summary: dict
    insights: List[str]
    files: Dict[str, dict]

    def to_text(self) -> str:
        """Convert analysis to LLM-friendly text format."""
        from ..formatters.llm import format_analysis
        return format_analysis(self)

    def to_json(self) -> str:
        """Convert analysis to JSON format."""
        import json
        return json.dumps({
            'summary': self.summary,
            'insights': self.insights,
            'files': self.files
        }, indent=2)

class BaseAnalyzer(ABC):
    """Base class for all code analyzers."""

    @abstractmethod
    def analyze_file(self, file_path: Path) -> dict:
        """
        Analyze a file and return standardized analysis results.

        Args:
            file_path: Path to the file to analyze.

        Returns:
            dict with the following structure:
            {
                'type': str,                 # Analyzer type (e.g., 'python', 'sql')
                'metrics': {
                    'loc': int,              # Lines of code
                    'classes': int,          # Number of classes
                    'functions': int,        # Number of functions
                    'imports': int,          # Number of imports
                    'complexity': int        # Complexity metric
                },
                'imports': List[str],        # List of import statements
                'functions': List[dict],     # List of function details
                'classes': List[dict],       # List of class details
                'comments': List[dict],      # List of comments
                'todos': List[dict],         # List of TODOs
                'errors': List[dict],        # Optional analysis errors
                'full_content': str,         # Optional full file content
            }

        Note:
            - All fields are optional except 'type' and 'metrics'
            - Language-specific analyzers may add additional fields
        """
        pass

class ProjectAnalyzer:
    """Main project analyzer that coordinates language-specific analyzers."""

    def __init__(self):
        self.analyzers = self._initialize_analyzers()

    def _initialize_analyzers(self) -> Dict[str, BaseAnalyzer]:
        """Initialize language-specific analyzers."""
        from .python import PythonAnalyzer
        from .javascript import JavaScriptAnalyzer
        from .sql import SQLServerAnalyzer

        return {
            '.py': PythonAnalyzer(),
            '.js': JavaScriptAnalyzer(),
            '.jsx': JavaScriptAnalyzer(),
            '.ts': JavaScriptAnalyzer(),
            '.tsx': JavaScriptAnalyzer(),
            '.sql': SQLServerAnalyzer(),
        }

    def analyze(self, path: Path) -> AnalysisResult:
        """Analyze entire project directory."""
        # Initialize analysis structure
        analysis = {
            'summary': {
                'project_stats': {
                    'total_files': 0,
                    'by_type': {},
                    'lines_of_code': 0,
                    'avg_file_size': 0
                },
                'code_metrics': {
                    'functions': {'count': 0, 'with_docs': 0, 'complex': 0},
                    'classes': {'count': 0, 'with_docs': 0},
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
                    'core_files': []
                }
            },
            'insights': [],
            'files': {}
        }

        # Collect analyzable files
        files = self._collect_files(path)
        analysis['summary']['project_stats']['total_files'] = len(files)

        # Process each file
        for file_path in files:
            if analyzer := self.analyzers.get(file_path.suffix.lower()):
                try:
                    file_analysis = analyzer.analyze_file(file_path)
                    str_path = str(file_path)

                    # Ensure file_analysis has required fields
                    if not isinstance(file_analysis, dict):
                        print(f"Error analyzing {file_path}: Invalid analysis result")
                        continue

                    if 'type' not in file_analysis:
                        file_analysis['type'] = file_path.suffix.lower().lstrip('.')

                    # Skip files with errors unless they have partial results
                    if 'errors' in file_analysis and not file_analysis.get('metrics', {}).get('loc', 0):
                        print(f"Error analyzing {file_path}: {file_analysis['errors']}")
                        continue

                    # Update file types count
                    ext = file_path.suffix
                    analysis['summary']['project_stats']['by_type'][ext] = \
                        analysis['summary']['project_stats']['by_type'].get(ext, 0) + 1

                    # Store file analysis
                    analysis['files'][str_path] = file_analysis

                    # Update metrics
                    self._update_metrics(analysis, file_analysis, str_path)

                except Exception as e:
                    print(f"Error analyzing {file_path}: {e}")
                    continue

        # Calculate final metrics
        self._calculate_final_metrics(analysis)

        # Generate insights
        if insights_gen := analysis.get('summary', {}).get('insights_generator'):
            analysis['insights'] = insights_gen(analysis)
        else:
            analysis['insights'] = self._generate_default_insights(analysis)

        return AnalysisResult(**analysis)

    def _collect_files(self, path: Path) -> List[Path]:
        """Collect all analyzable files from directory."""
        files = []

        for file_path in path.rglob('*'):
            if (file_path.is_file() and
                file_path.suffix.lower() in self.analyzers):
                files.append(file_path)

        return files

    def _update_metrics(self, analysis: dict, file_analysis: dict, file_path: str) -> None:
        """Update project metrics with file analysis results."""
        metrics = file_analysis.get('metrics', {})

        # Update basic metrics
        analysis['summary']['project_stats']['lines_of_code'] += metrics.get('loc', 0)

        # Update function metrics
        functions = file_analysis.get('functions', [])
        analysis['summary']['code_metrics']['functions']['count'] += len(functions)
        analysis['summary']['code_metrics']['functions']['with_docs'] += \
            sum(1 for f in functions if f.get('docstring'))
        analysis['summary']['code_metrics']['functions']['complex'] += \
            sum(1 for f in functions if f.get('complexity', 0) > 5)

        # Update class metrics
        classes = file_analysis.get('classes', [])
        analysis['summary']['code_metrics']['classes']['count'] += len(classes)
        analysis['summary']['code_metrics']['classes']['with_docs'] += \
            sum(1 for c in classes if c.get('docstring'))

        # Update imports
        imports = file_analysis.get('imports', [])
        analysis['summary']['code_metrics']['imports']['count'] += len(imports)
        analysis['summary']['code_metrics']['imports']['unique'].update(imports)

        # Update structure info
        dir_path = str(Path(file_path).parent)
        analysis['summary']['structure']['directories'].add(dir_path)

        # Update entry points
        if self._is_entry_point(file_path, file_analysis):
            analysis['summary']['structure']['entry_points'].append(file_path)

        # Update core files
        if self._is_core_file(file_analysis):
            analysis['summary']['structure']['core_files'].append(file_path)

        # Update maintenance info
        for todo in file_analysis.get('todos', []):
            analysis['summary']['maintenance']['todos'].append({
                'file': file_path,
                'line': todo.get('line', 0),
                'text': todo.get('text', ''),
                'priority': self._estimate_todo_priority(todo.get('text', ''))
            })

    def _calculate_final_metrics(self, analysis: dict) -> None:
        """Calculate final metrics and handle serialization."""
        total_files = analysis['summary']['project_stats']['total_files']
        if total_files > 0:
            # Calculate average file size
            analysis['summary']['project_stats']['avg_file_size'] = \
                analysis['summary']['project_stats']['lines_of_code'] / total_files

        # Calculate documentation coverage
        total_elements = (
            analysis['summary']['code_metrics']['functions']['count'] +
            analysis['summary']['code_metrics']['classes']['count']
        )
        if total_elements > 0:
            documented = (
                analysis['summary']['code_metrics']['functions']['with_docs'] +
                analysis['summary']['code_metrics']['classes']['with_docs']
            )
            analysis['summary']['maintenance']['doc_coverage'] = \
                (documented / total_elements) * 100

        # Convert sets to lists for serialization
        analysis['summary']['code_metrics']['imports']['unique'] = \
            list(analysis['summary']['code_metrics']['imports']['unique'])
        analysis['summary']['structure']['directories'] = \
            list(analysis['summary']['structure']['directories'])

    def _is_entry_point(self, file_path: str, analysis: dict) -> bool:
        """Identify if a file is a potential entry point."""
        from ..utils import is_potential_entry_point
        return is_potential_entry_point(file_path, analysis)

    def _is_core_file(self, analysis: dict) -> bool:
        """Identify if a file is likely a core component."""
        from ..utils import is_core_file
        return is_core_file(analysis)

    def _estimate_todo_priority(self, text: str) -> str:
        """Estimate TODO priority based on content."""
        from ..utils import estimate_todo_priority
        return estimate_todo_priority(text)

    def _generate_default_insights(self, analysis: dict) -> List[str]:
        """Generate default insights from analysis results."""
        insights = []

        # Basic project stats
        total_files = analysis['summary']['project_stats']['total_files']
        insights.append(f"Project contains {total_files} analyzable files")

        # Documentation insights
        doc_coverage = analysis['summary']['maintenance']['doc_coverage']
        if doc_coverage < 50:
            insights.append(f"Low documentation coverage ({doc_coverage:.1f}%)")
        elif doc_coverage > 80:
            insights.append(f"Good documentation coverage ({doc_coverage:.1f}%)")

        # Complexity insights
        complex_funcs = analysis['summary']['code_metrics']['functions']['complex']
        if complex_funcs > 0:
            insights.append(f"Found {complex_funcs} complex functions that might need attention")

        # TODO insights
        todos = analysis['summary']['maintenance']['todos']
        if todos:
            high_priority = sum(1 for todo in todos if todo['priority'] == 'high')
            if high_priority > 0:
                insights.append(f"Found {high_priority} high-priority TODOs")

        return insights
