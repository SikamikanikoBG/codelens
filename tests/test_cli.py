"""test_cli.py - Comprehensive tests for CLI functionality"""
import pytest
import os
import json
from pathlib import Path
from click.testing import CliRunner
from unittest import mock
from llm_code_lens.cli import (
    main, 
    split_content_by_tokens, 
    should_ignore,
    export_full_content,
    export_sql_content,
    _combine_results,
    _combine_fs_results,
    _combine_sql_results
)

class TestCLI:
    @pytest.fixture
    def cli_runner(self):
        """Create a CLI test runner."""
        return CliRunner()

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
from typing import List

def process_data(items: List[int]) -> List[int]:
    """Process data with validation."""
    # TODO: Add input validation
    return [x * 2 for x in items]
''',
            'tests/test_main.py': '''
def test_main():
    """Test main function."""
    assert True
'''
        }
        
        for path, content in project_structure.items():
            full_path = tmp_path / path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content)
        return tmp_path

    @pytest.fixture
    def mock_analyzers(self, mocker):
        """Mock all analyzers."""
        mocker.patch('llm_code_lens.analyzer.python.PythonAnalyzer')
        mocker.patch('llm_code_lens.analyzer.javascript.JavaScriptAnalyzer')
        mocker.patch('llm_code_lens.analyzer.sql.SQLServerAnalyzer')
        return mocker

    def test_basic_analysis(self, cli_runner, sample_project):
        """Test basic project analysis."""
        result = cli_runner.invoke(main, [str(sample_project)])
        assert result.exit_code == 0
        
        output_dir = sample_project / '.codelens'
        assert output_dir.exists()
        
        analysis_file = output_dir / 'analysis.txt'
        assert analysis_file.exists()
        
        content = analysis_file.read_text()
        assert 'CODEBASE SUMMARY:' in content
        assert 'src/main.py' in content
        assert 'src/utils.py' in content
        assert 'process_data' in content
        assert 'TODO: Add input validation' in content

    def test_json_output(self, cli_runner, sample_project):
        """Test JSON output format."""
        result = cli_runner.invoke(main, [str(sample_project), '--format', 'json'])
        assert result.exit_code == 0
        
        analysis_file = sample_project / '.codelens' / 'analysis.json'
        assert analysis_file.exists()
        
        content = json.loads(analysis_file.read_text())
        assert 'summary' in content
        assert 'files' in content
        assert 'insights' in content
        
        # Check JSON structure
        assert 'project_stats' in content['summary']
        assert 'code_metrics' in content['summary']
        assert isinstance(content['insights'], list)
        assert isinstance(content['files'], dict)

    def test_full_export(self, cli_runner, sample_project):
        """Test full content export functionality."""
        result = cli_runner.invoke(main, [str(sample_project), '--full'])
        assert result.exit_code == 0
        
        output_dir = sample_project / '.codelens'
        full_files = list(output_dir.glob('full_*.txt'))
        assert len(full_files) > 0
        
        # Check content of exported files
        content = full_files[0].read_text()
        assert 'def main():' in content
        assert 'def process_data(' in content
        assert 'TODO: Add input validation' in content

    def test_sql_integration(self, cli_runner, tmp_path, mock_analyzers):
        """Test SQL Server integration."""
        # Create SQL config
        sql_config = {
            'server': 'test-server',
            'database': 'test-db',
            'env': {
                'MSSQL_USERNAME': 'test-user',
                'MSSQL_PASSWORD': 'test-pass'
            }
        }
        config_file = tmp_path / 'sql-config.json'
        config_file.write_text(json.dumps(sql_config))
        
        # Test with SQL config
        result = cli_runner.invoke(main, ['--sql-config', str(config_file)])
        assert result.exit_code == 0
        
        # Verify environment variables were set
        assert os.environ.get('MSSQL_USERNAME') == 'test-user'
        assert os.environ.get('MSSQL_PASSWORD') == 'test-pass'
        
        # Test direct SQL parameters
        result = cli_runner.invoke(main, [
            '--sql-server', 'test-server',
            '--sql-database', 'test-db'
        ])
        assert result.exit_code == 0

    def test_debug_output(self, cli_runner, sample_project):
        """Test debug output functionality."""
        result = cli_runner.invoke(main, [str(sample_project), '--debug'])
        assert result.exit_code == 0
        
        # Check debug information in output
        assert 'Analyzing path:' in result.output
        assert 'Starting File System Analysis' in result.output
        assert 'Analysis complete' in result.output

    def test_error_handling(self, cli_runner, tmp_path):
        """Test CLI error handling."""
        # Test invalid directory
        result = cli_runner.invoke(main, ['nonexistent_dir'])
        assert result.exit_code != 0
        assert 'Error' in result.stderr
        
        # Test invalid SQL config
        invalid_config = tmp_path / 'invalid.json'
        invalid_config.write_text('invalid json')
        
        result = cli_runner.invoke(main, ['--sql-config', str(invalid_config)])
        assert result.exit_code != 0
        assert 'Error' in result.stderr or 'Warning' in result.stderr
        
        # Test permission error
        if os.name != 'nt':  # Skip on Windows
            read_only_dir = tmp_path / 'readonly'
            read_only_dir.mkdir()
            os.chmod(read_only_dir, 0o444)
            
            result = cli_runner.invoke(main, [str(read_only_dir)])
            assert result.exit_code != 0
            assert 'Error' in result.stderr

class TestContentSplitting:
    """Test content splitting functionality."""
    
    def test_split_content_basic(self):
        """Test basic content splitting."""
        content = "Hello " * 1000
        chunks = split_content_by_tokens(content)
        
        assert len(chunks) > 0
        assert all(isinstance(chunk, str) for chunk in chunks)
        assert ''.join(chunks) == content

    def test_split_content_edge_cases(self):
        """Test content splitting edge cases."""
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

    @mock.patch('tiktoken.get_encoding')
    def test_split_content_fallback(self, mock_encoding):
        """Test fallback behavior when token splitting fails."""
        mock_encoding.side_effect = Exception('Test error')
        
        content = "Test content\n" * 1000
        chunks = split_content_by_tokens(content)
        
        assert len(chunks) > 0
        assert ''.join(chunks) == content

class TestIgnorePatterns:
    """Test file/directory ignore patterns."""
    
    def test_should_ignore_patterns(self):
        """Test should_ignore function with various patterns."""
        # Directories that should be ignored
        assert should_ignore(Path('.git/config'))
        assert should_ignore(Path('venv/lib/python3.8'))
        assert should_ignore(Path('node_modules/package'))
        assert should_ignore(Path('.idea/workspace.xml'))
        assert should_ignore(Path('__pycache__/module.cpython-38.pyc'))
        
        # Files that should not be ignored
        assert not should_ignore(Path('src/main.py'))
        assert not should_ignore(Path('tests/test_main.py'))
        assert not should_ignore(Path('README.md'))

class TestResultsCombining:
    """Test results combining functionality."""
    
    @pytest.fixture
    def fs_result(self):
        """Create a file system analysis result."""
        return {
            'summary': {
                'project_stats': {
                    'total_files': 2,
                    'by_type': {'.py': 2},
                    'lines_of_code': 100
                },
                'code_metrics': {
                    'functions': {'count': 3, 'with_docs': 2, 'complex': 1},
                    'classes': {'count': 1, 'with_docs': 1},
                    'imports': {'count': 5, 'unique': set(['os', 'sys'])}
                },
                'maintenance': {
                    'todos': [{'file': 'test.py', 'text': 'TODO'}],
                },
                'structure': {
                    'directories': set(['src', 'tests']),
                    'entry_points': ['main.py']
                }
            },
            'insights': ['Found 2 Python files'],
            'files': {
                'test.py': {'metrics': {'loc': 50}},
                'main.py': {'metrics': {'loc': 50}}
            }
        }

    @pytest.fixture
    def sql_result(self):
        """Create a SQL analysis result."""
        return {
            'stored_procedures': [
                {
                    'name': 'sp_test',
                    'schema': 'dbo',
                    'definition': 'CREATE PROCEDURE...',
                    'metrics': {'lines': 50, 'complexity': 5},
                    'parameters': [{'name': 'param1', 'type': 'int'}],
                    'dependencies': ['table1'],
                    'todos': [],
                    'comments': []
                }
            ],
            'views': [
                {
                    'name': 'vw_test',
                    'schema': 'dbo',
                    'definition': 'CREATE VIEW...',
                    'metrics': {'lines': 20, 'complexity': 2},
                    'dependencies': ['table2'],
                    'todos': [],
                    'comments': []
                }
            ],
            'functions': []
        }

    def test_combine_fs_results(self, fs_result):
        """Test combining file system results."""
        combined = {'summary': {'project_stats': {'total_files': 0, 'by_type': {}, 'lines_of_code': 0}}}
        _combine_fs_results(combined, fs_result)
        
        assert combined['summary']['project_stats']['total_files'] == 2
        assert combined['summary']['project_stats']['lines_of_code'] == 100
        assert combined['summary']['project_stats']['by_type']['.py'] == 2

    def test_combine_sql_results(self, sql_result):
        """Test combining SQL results."""
        combined = {
            'summary': {
                'project_stats': {'total_sql_objects': 0},
                'code_metrics': {'sql_objects': {'procedures': 0, 'views': 0, 'functions': 0}},
                'structure': {'sql_dependencies': []},
                'insights': []
            },
            'files': {}
        }
        
        _combine_sql_results(combined, sql_result)
        
        assert combined['summary']['project_stats']['total_sql_objects'] == 2
        assert combined['summary']['code_metrics']['sql_objects']['procedures'] == 1
        assert combined['summary']['code_metrics']['sql_objects']['views'] == 1
        assert len(combined['files']) == 2

    def test_combine_all_results(self, fs_result, sql_result):
        """Test combining all types of results."""
        combined = _combine_results([fs_result, sql_result])
        
        # Check combined metrics
        assert combined.summary['project_stats']['total_files'] == 2
        assert combined.summary['project_stats']['total_sql_objects'] == 2
        assert len(combined.files) == 4  # 2 Python files + 2 SQL objects
        
        # Check insights
        assert any('Python files' in insight for insight in combined.insights)
        assert any('procedures' in insight for insight in combined.insights)

if __name__ == '__main__':
    pytest.main(['-v'])