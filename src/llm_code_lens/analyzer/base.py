from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass
from .python import PythonAnalyzer
from .javascript import JavaScriptAnalyzer

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

class ProjectAnalyzer:
    """Main project analyzer that coordinates language-specific analyzers."""
    
    def __init__(self):
        self.analyzers = {
            '.py': PythonAnalyzer(),
            '.js': JavaScriptAnalyzer(),
            '.jsx': JavaScriptAnalyzer(),
            '.ts': JavaScriptAnalyzer(),
            '.tsx': JavaScriptAnalyzer(),
        }
    
    def analyze(self, path: Path) -> AnalysisResult:
        """Analyze entire project directory."""
        # Collect files
        files = self._collect_files(path)
        
        # Analyze each file
        analysis = {}
        for file_path in files:
            if analyzer := self.analyzers.get(file_path.suffix.lower()):
                try:
                    analysis[str(file_path)] = analyzer.analyze_file(file_path)
                except Exception as e:
                    print(f"Error analyzing {file_path}: {e}")
        
        # Generate insights
        from ..processors.insights import generate_insights
        insights = generate_insights(analysis)
        
        # Generate summary
        from ..processors.summary import generate_summary
        summary = generate_summary(analysis)
        
        return AnalysisResult(
            summary=summary,
            insights=insights,
            files=analysis
        )
    
    def _collect_files(self, path: Path) -> List[Path]:
        """Collect all analyzable files from directory."""
        files = []
        
        def should_ignore(path: Path) -> bool:
            ignore_patterns = {
                '.git', '__pycache__', 'venv', 'env',
                'node_modules', '.idea', '.vscode'
            }
            return any(part in ignore_patterns for part in path.parts)
        
        for file_path in path.rglob('*'):
            if (file_path.is_file() and 
                file_path.suffix.lower() in self.analyzers and 
                not should_ignore(file_path)):
                files.append(file_path)
        
        return files
