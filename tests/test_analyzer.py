"""test_analyzer.py - Tests for analyzer components"""
import pytest
import os
from pathlib import Path
from unittest import mock
from llm_code_lens.analyzer.python import PythonAnalyzer
from llm_code_lens.analyzer.javascript import JavaScriptAnalyzer
from llm_code_lens.analyzer.sql import SQLServerAnalyzer
from llm_code_lens.analyzer.base import ProjectAnalyzer

class TestBase:
    @pytest.fixture(autouse=True)
    def setup_teardown(self, tmp_path):
        """Setup and teardown for all tests."""
        self.original_dir = os.getcwd()
        os.chdir(tmp_path)
        yield
        os.chdir(self.original_dir)

    @pytest.fixture
    def sample_project(self, tmp_path):
        """Create a sample project structure."""
        project_structure = {
            'src/main.py': '''
def main():
    """Main entry point."""
    return True

if __name__ == "__main__":
    main()
''',
            'src/utils.py': '''
from typing import List, Optional

def process_data(items: List[int]) -> List[int]:
    """Process data with validation.
    
    Args:
        items: List of numbers to process
        
    Returns:
        Processed list of numbers
    """
    # TODO: Add input validation
    return [x * 2 for x in items]

class DataProcessor:
    """Data processing utility class."""
    
    def __init__(self, multiplier: int = 2):
        self.multiplier = multiplier
    
    def process(self, value: int) -> int:
        """Process a single value."""
        return value * self.multiplier
''',
            'tests/test_utils.py': '''
def test_process_data():
    """Test data processing function."""
    assert True
'''
        }
        
        for path, content in project_structure.items():
            full_path = tmp_path / path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content)
        return tmp_path

class TestPythonAnalyzer:
    @pytest.fixture
    def complex_python_file(self, tmp_path):
        """Create a complex Python file for testing."""
        content = '''
from typing import List, Optional, Union
import os
from pathlib import Path as PathLib

class BaseClass:
    """Base class docstring."""
    def __init__(self, value: int) -> None:
        self.value = value
    
    @property
    def doubled(self) -> int:
        """Get doubled value."""
        return self.value * 2

class ComplexClass(BaseClass):
    """Complex class with various features."""
    
    def __init__(self, value: int, name: str = "default") -> None:
        super().__init__(value)
        self.name = name
    
    @classmethod
    def from_string(cls, data: str) -> "ComplexClass":
        """Create from string."""
        try:
            value = int(data)
            return cls(value)
        except ValueError:
            return cls(0, data)
    
    @staticmethod
    def helper(x: Union[int, str]) -> bool:
        """Static helper method."""
        return isinstance(x, int)

def process_data(items: List[int], threshold: Optional[int] = None) -> List[int]:
    """Process a list of integers with threshold.
    
    Args:
        items: List of numbers to process
        threshold: Optional cutoff value
    
    Returns:
        Filtered and processed list
    """
    # TODO: Add input validation
    result = []
    for item in items:
        if threshold and item > threshold:
            continue
        # FIXME: Handle negative numbers better
        if item < 0:
            item = abs(item)
        result.append(item * 2)
    return result

async def async_handler(*args, **kwargs) -> None:
    """Async function example."""
    # Process arguments
    for arg in args:
        await process_arg(arg)
    
    # Handle keyword arguments
    for key, value in kwargs.items():
        if isinstance(value, (list, tuple)):
            await process_collection(value)

def complex_function(a: int, b: int, *args: int, key: str = "", **kwargs: Any) -> dict:
    """Function with complex argument structure."""
    result = {'a': a, 'b': b, 'args': args, 'kwargs': kwargs}
    
    # Complex logic increases cyclomatic complexity
    if a > 0:
        if b > 0:
            result['sum'] = a + b
        else:
            result['product'] = a * abs(b)
    elif b > 0:
        if key:
            result['key_sum'] = sum(ord(c) for c in key)
        else:
            result['key_missing'] = True
    
    return result
'''
        file_path = tmp_path / "complex.py"
        file_path.write_text(content)
        return file_path

    def test_imports_analysis(self, complex_python_file):
        """Test import statement analysis."""
        analyzer = PythonAnalyzer()
        result = analyzer.analyze_file(complex_python_file)
        
        assert len(result['imports']) == 3
        assert any('typing' in imp for imp in result['imports'])
        assert any('pathlib' in imp and 'PathLib' in imp for imp in result['imports'])
        assert any('os' in imp for imp in result['imports'])

    def test_class_analysis(self, complex_python_file):
        """Test class definition analysis."""
        analyzer = PythonAnalyzer()
        result = analyzer.analyze_file(complex_python_file)
        
        base_class = next(c for c in result['classes'] if c['name'] == 'BaseClass')
        complex_class = next(c for c in result['classes'] if c['name'] == 'ComplexClass')
        
        # Test base class
        assert not base_class['bases']
        assert base_class['docstring']
        assert any(m['name'] == 'doubled' and m['is_property'] for m in base_class['methods'])
        
        # Test derived class
        assert 'BaseClass' in complex_class['bases']
        assert complex_class['docstring']
        assert any(m['name'] == 'from_string' and m['is_classmethod'] for m in complex_class['methods'])
        assert any(m['name'] == 'helper' and m['is_staticmethod'] for m in complex_class['methods'])

    def test_function_analysis(self, complex_python_file):
        """Test function analysis capabilities."""
        analyzer = PythonAnalyzer()
        result = analyzer.analyze_file(complex_python_file)
        
        process_data = next(f for f in result['functions'] if f['name'] == 'process_data')
        async_handler = next(f for f in result['functions'] if f['name'] == 'async_handler')
        complex_func = next(f for f in result['functions'] if f['name'] == 'complex_function')
        
        # Test regular function
        assert process_data['return_type'] == 'List[int]'
        assert process_data['docstring']
        assert len(process_data['args']) == 2
        assert process_data['args'][1].endswith('= None')
        
        # Test async function
        assert async_handler['is_async']
        assert '*args' in str(async_handler['args'])
        assert '**kwargs' in str(async_handler['args'])
        
        # Test complex function
        assert complex_func['complexity'] > 3
        assert len(complex_func['args']) == 4
        assert any('**kwargs' in arg for arg in complex_func['args'])

    def test_todo_extraction(self, complex_python_file):
        """Test TODO and FIXME comment extraction."""
        analyzer = PythonAnalyzer()
        result = analyzer.analyze_file(complex_python_file)
        
        assert len(result['todos']) == 2
        assert any('Add input validation' in todo['text'] for todo in result['todos'])
        assert any('Handle negative numbers' in todo['text'] for todo in result['todos'])

    def test_error_handling(self, tmp_path):
        """Test analyzer error handling capabilities."""
        # Test syntax error
        syntax_error_file = tmp_path / "syntax_error.py"
        syntax_error_file.write_text("def invalid_syntax(:")
        
        analyzer = PythonAnalyzer()
        result = analyzer.analyze_file(syntax_error_file)
        
        assert 'errors' in result
        assert result['errors'][0]['type'] == 'syntax_error'
        assert result['metrics']['loc'] == 0
        
        # Test encoding error
        binary_file = tmp_path / "binary.py"
        binary_file.write_bytes(b'\x80\x81')
        
        result = analyzer.analyze_file(binary_file)
        assert 'errors' in result
        
        # Test empty file
        empty_file = tmp_path / "empty.py"
        empty_file.touch()
        
        result = analyzer.analyze_file(empty_file)
        assert result['metrics']['loc'] == 0
        assert not result.get('errors')

class TestJavaScriptAnalyzer:
    @pytest.fixture
    def js_file(self, tmp_path):
        """Create a JavaScript file for testing."""
        content = '''
import React from 'react';
import { useState, useEffect } from 'react';

// Component with hooks
function DataList({ data }) {
    const [items, setItems] = useState(data);
    
    useEffect(() => {
        // TODO: Add error handling
        fetchData().then(setItems);
    }, []);
    
    return items.map(item => <div key={item.id}>{item.name}</div>);
}

class DataManager {
    constructor(source) {
        this.source = source;
    }
    
    async fetchData() {
        // FIXME: Add retry logic
        const response = await fetch(this.source);
        return response.json();
    }
}

export { DataList, DataManager };
'''
        file_path = tmp_path / "data.js"
        file_path.write_text(content)
        return file_path

    def test_js_imports(self, js_file):
        """Test JavaScript import analysis."""
        analyzer = JavaScriptAnalyzer()
        result = analyzer.analyze_file(js_file)
        
        assert len(result['imports']) == 2
        assert any('React' in imp for imp in result['imports'])
        assert any('useState' in imp and 'useEffect' in imp for imp in result['imports'])

    def test_js_exports(self, js_file):
        """Test JavaScript export analysis."""
        analyzer = JavaScriptAnalyzer()
        result = analyzer.analyze_file(js_file)
        
        assert len(result['exports']) == 1
        assert 'DataList' in result['exports'][0]
        assert 'DataManager' in result['exports'][0]

    def test_js_functions(self, js_file):
        """Test JavaScript function analysis."""
        analyzer = JavaScriptAnalyzer()
        result = analyzer.analyze_file(js_file)
        
        assert any(f['name'] == 'DataList' for f in result['functions'])
        data_list = next(f for f in result['functions'] if f['name'] == 'DataList')
        assert data_list['line_number'] > 0

    def test_js_classes(self, js_file):
        """Test JavaScript class analysis."""
        analyzer = JavaScriptAnalyzer()
        result = analyzer.analyze_file(js_file)
        
        assert len(result['classes']) == 1
        data_manager = result['classes'][0]
        assert data_manager['name'] == 'DataManager'
        assert data_manager['line_number'] > 0

    def test_js_todos(self, js_file):
        """Test JavaScript TODO extraction."""
        analyzer = JavaScriptAnalyzer()
        result = analyzer.analyze_file(js_file)
        
        assert len(result['todos']) == 2
        assert any('Add error handling' in todo['text'] for todo in result['todos'])
        assert any('Add retry logic' in todo['text'] for todo in result['todos'])

class TestSQLServerAnalyzer:
    @pytest.fixture
    def mock_sql_connection(self, mocker):
        """Mock SQL Server connection."""
        mock_conn = mocker.patch('pyodbc.connect')
        mock_conn.return_value.cursor.return_value.fetchall.return_value = []
        return mock_conn

    @pytest.fixture
    def sql_file(self, tmp_path):
        """Create a SQL file for testing."""
        content = '''
CREATE PROCEDURE ManageEmployeeData
    @Operation NVARCHAR(10), -- 'INSERT', 'UPDATE', or 'GET'
    @EmployeeID INT = NULL,
    @FirstName NVARCHAR(50) = NULL,
    @LastName NVARCHAR(50) = NULL,
    @Position NVARCHAR(50) = NULL,
    @Salary DECIMAL(18, 2) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    
    -- TODO: Add transaction handling
    
    IF @Operation = 'INSERT'
    BEGIN
        INSERT INTO Employees (FirstName, LastName, Position, Salary)
        VALUES (@FirstName, @LastName, @Position, @Salary);
    END
    ELSE IF @Operation = 'UPDATE'
    BEGIN
        UPDATE Employees
        SET
            FirstName = ISNULL(@FirstName, FirstName),
            LastName = ISNULL(@LastName, LastName),
            Position = ISNULL(@Position, Position),
            Salary = ISNULL(@Salary, Salary)
        WHERE EmployeeID = @EmployeeID;
    END
    ELSE IF @Operation = 'GET'
    BEGIN
        SELECT * FROM Employees WHERE EmployeeID = @EmployeeID;
    END
END;
GO

CREATE VIEW EmployeeSummary AS
    -- FIXME: Optimize this query
    SELECT 
        e.EmployeeID,
        e.FirstName + ' ' + e.LastName AS FullName,
        e.Position,
        e.Salary,
        d.DepartmentName
    FROM Employees e
    LEFT JOIN Departments d ON e.DepartmentID = d.DepartmentID;
GO
'''
        file_path = tmp_path / "employees.sql"
        file_path.write_text(content)
        return file_path

    def test_sql_object_extraction(self, sql_file):
        """Test SQL object extraction."""
        analyzer = SQLServerAnalyzer()
        result = analyzer.analyze_file(sql_file)
        
        assert len(result['objects']) == 2
        proc = next(obj for obj in result['objects'] if obj['type'] == 'procedure')
        view = next(obj for obj in result['objects'] if obj['type'] == 'view')
        
        assert proc['name'] == 'ManageEmployeeData'
        assert view['name'] == 'EmployeeSummary'
        assert proc['loc'] > 10
        assert view['loc'] > 5

    def test_sql_parameters(self, sql_file):
        """Test SQL parameter extraction."""
        analyzer = SQLServerAnalyzer()
    
    def test_sql_parameters(self, sql_file):
        """Test SQL parameter extraction."""
        analyzer = SQLServerAnalyzer()
        result = analyzer.analyze_file(sql_file)
        
        params = result['parameters']
        assert len(params) > 0
        
        operation_param = next(p for p in params if p['name'] == 'Operation')
        assert operation_param['data_type'] == 'NVARCHAR(10)'
        assert 'INSERT' in operation_param['description']
        
        nullable_param = next(p for p in params if p['name'] == 'EmployeeID')
        assert nullable_param['data_type'] == 'INT'
        assert nullable_param['default'] == 'NULL'

    def test_sql_dependencies(self, sql_file):
        """Test SQL dependency extraction."""
        analyzer = SQLServerAnalyzer()
        result = analyzer.analyze_file(sql_file)
        
        deps = result['dependencies']
        assert 'Employees' in deps
        assert 'Departments' in deps
        
        # Verify no false positives
        assert 'BEGIN' not in deps
        assert 'WHERE' not in deps

    def test_sql_complexity(self, sql_file):
        """Test SQL complexity calculation."""
        analyzer = SQLServerAnalyzer()
        result = analyzer.analyze_file(sql_file)
        
        proc = next(obj for obj in result['objects'] if obj['type'] == 'procedure')
        view = next(obj for obj in result['objects'] if obj['type'] == 'view')
        
        # Procedure should have higher complexity due to IF statements
        assert proc['complexity'] > view['complexity']
        assert proc['complexity'] > 5  # Multiple IF branches
        
    def test_sql_todos(self, sql_file):
        """Test SQL TODO extraction."""
        analyzer = SQLServerAnalyzer()
        result = analyzer.analyze_file(sql_file)
        
        assert len(result['todos']) == 2
        assert any('transaction' in todo['text'].lower() for todo in result['todos'])
        assert any('optimize' in todo['text'].lower() for todo in result['todos'])

    def test_sql_server_connection(self, mock_sql_connection):
        """Test SQL Server connection handling."""
        analyzer = SQLServerAnalyzer()
        
        # Test successful connection
        analyzer.connect("server=test;database=test")
        mock_sql_connection.assert_called_once()
        
        # Test database analysis
        result = analyzer.analyze_database("test_db")
        assert isinstance(result, dict)
        assert all(key in result for key in ['stored_procedures', 'views', 'functions'])

class TestCLI:
    @pytest.fixture
    def cli_runner(self):
        """Create a CLI test runner."""
        from click.testing import CliRunner
        return CliRunner()

    @pytest.fixture
    def mock_analyzers(self, mocker):
        """Mock all analyzers."""
        mocker.patch('llm_code_lens.analyzer.python.PythonAnalyzer')
        mocker.patch('llm_code_lens.analyzer.javascript.JavaScriptAnalyzer')
        mocker.patch('llm_code_lens.analyzer.sql.SQLServerAnalyzer')
        return mocker

    def test_cli_basic(self, cli_runner, sample_project):
        """Test basic CLI functionality."""
        from llm_code_lens.cli import main
        
        result = cli_runner.invoke(main, [str(sample_project)])
        assert result.exit_code == 0
        
        output_dir = sample_project / '.codelens'
        assert output_dir.exists()
        
        analysis_file = output_dir / 'analysis.txt'
        assert analysis_file.exists()
        content = analysis_file.read_text()
        assert 'CODEBASE SUMMARY:' in content
        assert 'src/main.py' in content

    def test_cli_json_output(self, cli_runner, sample_project):
        """Test CLI JSON output format."""
        from llm_code_lens.cli import main
        
        result = cli_runner.invoke(main, [str(sample_project), '--format', 'json'])
        assert result.exit_code == 0
        
        analysis_file = sample_project / '.codelens' / 'analysis.json'
        assert analysis_file.exists()
        
        import json
        content = json.loads(analysis_file.read_text())
        assert 'summary' in content
        assert 'files' in content
        assert 'insights' in content

    def test_cli_full_export(self, cli_runner, sample_project):
        """Test CLI full content export."""
        from llm_code_lens.cli import main
        
        result = cli_runner.invoke(main, [str(sample_project), '--full'])
        assert result.exit_code == 0
        
        output_dir = sample_project / '.codelens'
        full_files = list(output_dir.glob('full_*.txt'))
        assert len(full_files) > 0
        
        content = full_files[0].read_text()
        assert 'def main():' in content
        assert 'def process_data(' in content

    def test_cli_sql_config(self, cli_runner, tmp_path, mock_analyzers):
        """Test CLI SQL configuration handling."""
        from llm_code_lens.cli import main
        
        # Create SQL config file
        config_file = tmp_path / 'sql-config.json'
        config_content = {
            'server': 'test-server',
            'database': 'test-db',
            'env': {
                'MSSQL_USERNAME': 'test-user',
                'MSSQL_PASSWORD': 'test-pass'
            }
        }
        import json
        config_file.write_text(json.dumps(config_content))
        
        result = cli_runner.invoke(main, ['--sql-config', str(config_file)])
        assert result.exit_code == 0
        
        # Verify environment variables were set
        assert os.environ.get('MSSQL_USERNAME') == 'test-user'
        assert os.environ.get('MSSQL_PASSWORD') == 'test-pass'

    def test_cli_error_handling(self, cli_runner, tmp_path):
        """Test CLI error handling."""
        from llm_code_lens.cli import main
        
        # Test invalid directory
        result = cli_runner.invoke(main, ['invalid_dir'])
        assert result.exit_code != 0
        assert 'Error' in result.stderr
        
        # Test invalid SQL config
        invalid_config = tmp_path / 'invalid.json'
        invalid_config.write_text('invalid json')
        
        result = cli_runner.invoke(main, ['--sql-config', str(invalid_config)])
        assert result.exit_code != 0
        assert 'Error' in result.stderr or 'Warning' in result.stderr

class TestTokenization:
    """Test content tokenization and chunking."""
    
    def test_split_content_basic(self):
        """Test basic content splitting."""
        from llm_code_lens.cli import split_content_by_tokens
        
        content = "Hello " * 1000
        chunks = split_content_by_tokens(content)
        
        assert len(chunks) > 0
        assert all(isinstance(chunk, str) for chunk in chunks)
        assert ''.join(chunks) == content

    def test_split_content_edge_cases(self):
        """Test content splitting edge cases."""
        from llm_code_lens.cli import split_content_by_tokens
        
        test_cases = [
            '',  # Empty string
            'a',  # Single character
            'Hello\n' * 10000,  # Very long content
            '你好\n' * 1000,  # Unicode content
            '\x00\x01\x02',  # Binary content
        ]
        
        for content in test_cases:
            chunks = split_content_by_tokens(content)
            assert len(chunks) > 0
            assert ''.join(chunks) == content

    def test_split_content_failure(self, mocker):
        """Test content splitting failure handling."""
        from llm_code_lens.cli import split_content_by_tokens
        
        # Mock tiktoken to simulate failure
        mocker.patch('tiktoken.get_encoding', side_effect=Exception('Test error'))
        
        content = "Test content\n" * 1000
        chunks = split_content_by_tokens(content)
        
        assert len(chunks) > 0
        assert ''.join(chunks) == content

if __name__ == '__main__':
    pytest.main(['-v'])