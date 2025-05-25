from .base import ProjectAnalyzer, AnalysisResult, BaseAnalyzer
from .python import PythonAnalyzer
from .javascript import JavaScriptAnalyzer
from .config import (
    analyze_package_json,
    analyze_tsconfig,
    extract_readme_summary
)

# Create a lazy-loading proxy for SQLServerAnalyzer
class SQLServerAnalyzerProxy:
    def __new__(cls, *args, **kwargs):
        try:
            from .sql import SQLServerAnalyzer as RealSQLServerAnalyzer
            return RealSQLServerAnalyzer(*args, **kwargs)
        except ImportError as e:
            import warnings
            warnings.warn(f"SQL Server analysis functionality is not available: {e}. "
                         "Install pyodbc and required ODBC drivers to enable this feature.")

            # Return a dummy analyzer that provides the same interface but does nothing
            class DummySQLServerAnalyzer(BaseAnalyzer):
                def __init__(self, *args, **kwargs):
                    pass

                def analyze_file(self, file_path):
                    return {"type": "sql", "metrics": {"loc": 0}, "errors": ["SQL analysis not available"]}

                def connect(self, connection_string=None):
                    pass

                def list_databases(self):
                    return []

                def analyze_database(self, database):
                    return {"stored_procedures": [], "views": [], "functions": []}

                def __del__(self):
                    pass

            return DummySQLServerAnalyzer(*args, **kwargs)

# Use the proxy instead of direct import
SQLServerAnalyzer = SQLServerAnalyzerProxy

__all__ = [
    'ProjectAnalyzer',
    'AnalysisResult',
    'BaseAnalyzer',
    'PythonAnalyzer',
    'JavaScriptAnalyzer',
    'SQLServerAnalyzer',
    'analyze_package_json',
    'analyze_tsconfig',
    'extract_readme_summary'
]
