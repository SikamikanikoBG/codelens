from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass
import os

@dataclass
class AnalysisResult:
    """Container for analysis results."""
    summary: dict
    insights: List[str]
    files: Dict[str, dict]
    configuration: Optional[dict] = None
    tree: Optional[str] = None

    def to_text(self) -> str:
        """Convert analysis to LLM-friendly text format."""
        from ..formatters.llm import format_analysis
        return format_analysis(self)

    def to_json(self) -> str:
        """Convert analysis to JSON format."""
        import json
        data = {
            'summary': self.summary,
            'insights': self.insights,
            'files': self.files
        }
        if self.configuration:
            data['configuration'] = self.configuration
        return json.dumps(data, indent=2)

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
        """Initialize analyzers for different file types."""
        from .python import PythonAnalyzer
        from .javascript import JavaScriptAnalyzer
        from .sql import SQLServerAnalyzer

        analyzers = {
            '.py': PythonAnalyzer(),
            '.js': JavaScriptAnalyzer(),
            '.jsx': JavaScriptAnalyzer(),
            '.ts': JavaScriptAnalyzer(),
            '.tsx': JavaScriptAnalyzer(),
            '.sql': SQLServerAnalyzer(),
        }

        return analyzers

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

        # Add configuration analysis
        config_analysis = self._analyze_project_configuration(path)
        analysis['configuration'] = config_analysis

        # Progress tracking
        if hasattr(self, 'progress'):
            file_task = self.progress.add_task("Processing files...", total=None)

        # Collect and process files
        files_to_analyze = self._collect_files(path)
        processed_files = 0

        for file_path in files_to_analyze:
            if not file_path.is_file():
                continue
                
            analyzer = self.analyzers.get(file_path.suffix.lower())
            if analyzer:
                try:
                    # Update progress
                    if hasattr(self, 'progress'):
                        self.progress.update(file_task, description=f"Analyzing: {file_path.name}")

                    file_analysis = analyzer.analyze_file(file_path)
                    str_path = str(file_path)

                    # Validate analysis
                    if not isinstance(file_analysis, dict) or 'type' not in file_analysis:
                        continue

                    # Skip files with errors unless they have partial results
                    if 'errors' in file_analysis and not file_analysis.get('metrics', {}).get('loc', 0):
                        continue

                    # Update file types count
                    ext = file_path.suffix
                    analysis['summary']['project_stats']['by_type'][ext] = \
                        analysis['summary']['project_stats']['by_type'].get(ext, 0) + 1

                    # Store file analysis
                    analysis['files'][str_path] = file_analysis

                    # Update metrics
                    self._update_metrics(analysis, file_analysis, str_path)
                    processed_files += 1

                except Exception as e:
                    if hasattr(self, 'debug') and self.debug:
                        print(f"Error analyzing {file_path}: {e}")
                    continue

        # Update final count
        analysis['summary']['project_stats']['total_files'] = processed_files

        # Generate project tree
        if hasattr(self, 'progress'):
            tree_task = self.progress.add_task("Generating project tree...", total=1)

        try:
            from ..utils.tree import ProjectTree
            tree_generator = ProjectTree(ignore_patterns=[], max_depth=4)
            project_tree = tree_generator.generate_tree(path, set())
            analysis['summary']['structure']['project_tree'] = project_tree
        except Exception:
            analysis['summary']['structure']['project_tree'] = "Project tree generation failed"

        if hasattr(self, 'progress'):
            self.progress.update(tree_task, advance=1)

        # Calculate final metrics
        self._calculate_final_metrics(analysis)

        # Generate insights
        analysis['insights'] = self._generate_insights(analysis)

        return AnalysisResult(**analysis)

    def _collect_files(self, path: Path) -> List[Path]:
        """Collect files to analyze."""
        files = []
        supported_extensions = set(self.analyzers.keys())
        
        for root, dirs, filenames in os.walk(str(path)):
            # Skip common ignored directories
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in {
                'node_modules', '__pycache__', 'venv', 'env', 'dist', 'build'
            }]
            
            root_path = Path(root)
            for filename in filenames:
                file_path = root_path / filename
                
                if file_path.suffix.lower() in supported_extensions:
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

        # Check for entry points
        if self._is_entry_point(file_path, file_analysis):
            analysis['summary']['structure']['entry_points'].append(file_path)

        # Check for core files
        if self._is_core_file(file_analysis):
            analysis['summary']['structure']['core_files'].append(file_path)

        # Update TODOs
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
        filename = Path(file_path).name.lower()
        
        # Common entry point patterns
        entry_patterns = [
            'main.py', 'app.py', 'server.py', 'cli.py', 'run.py',
            'index.js', 'app.js', 'server.js', 'main.js'
        ]
        
        if filename in entry_patterns:
            return True
        
        # Check for main functions
        functions = analysis.get('functions', [])
        if any('main' in func.get('name', '').lower() for func in functions):
            return True
            
        return False

    def _is_core_file(self, analysis: dict) -> bool:
        """Identify if a file is likely a core component."""
        metrics = analysis.get('metrics', {})
        
        # High number of functions or classes
        if metrics.get('functions', 0) > 10 or metrics.get('classes', 0) > 5:
            return True
        
        # High number of imports
        if metrics.get('imports', 0) > 15:
            return True
            
        return False

    def _estimate_todo_priority(self, text: str) -> str:
        """Estimate TODO priority based on content."""
        text_upper = text.upper()
        
        high_priority = ['CRITICAL', 'URGENT', 'ASAP', 'SECURITY', 'BUG', 'BROKEN', 'CRASH', 'FIXME']
        medium_priority = ['IMPORTANT', 'SOON', 'REFACTOR', 'OPTIMIZE', 'PERFORMANCE']
        
        if any(keyword in text_upper for keyword in high_priority):
            return 'high'
        elif any(keyword in text_upper for keyword in medium_priority):
            return 'medium'
        else:
            return 'low'

    def _generate_insights(self, analysis: dict) -> List[str]:
        """Generate insights from analysis results."""
        insights = []

        # Basic project stats
        total_files = analysis['summary']['project_stats']['total_files']
        insights.append(f"Project contains {total_files} analyzable files")

        # Documentation insights
        doc_coverage = analysis['summary']['maintenance']['doc_coverage']
        if doc_coverage < 50:
            insights.append(f"Low documentation coverage ({doc_coverage:.1f}%)")

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

    def _analyze_project_configuration(self, path: Path) -> dict:
        """Analyze project configuration files."""
        config_files = {}
        
        # Package.json
        package_file = path / 'package.json'
        if package_file.exists():
            try:
                import json
                with open(package_file, 'r') as f:
                    data = json.load(f)
                config_files['package.json'] = {
                    'name': data.get('name'),
                    'version': data.get('version'),
                    'type': 'node.js project'
                }
            except Exception:
                config_files['package.json'] = {'error': 'Failed to parse'}

        # Pyproject.toml
        pyproject_file = path / 'pyproject.toml'
        if pyproject_file.exists():
            config_files['pyproject.toml'] = {'type': 'python project'}

        # Requirements.txt
        req_file = path / 'requirements.txt'
        if req_file.exists():
            try:
                with open(req_file, 'r') as f:
                    lines = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                config_files['requirements.txt'] = {
                    'dependencies': len(lines),
                    'type': 'python requirements'
                }
            except Exception:
                config_files['requirements.txt'] = {'error': 'Failed to parse'}

        # README
        readme_files = ['README.md', 'README.rst', 'README.txt']
        for readme_name in readme_files:
            readme_file = path / readme_name
            if readme_file.exists():
                config_files['README'] = {'type': 'project readme', 'file': readme_name}
                break

        return config_files