"""test_formatters.py - Tests for output formatters"""
import pytest
from llm_code_lens.analyzer.base import AnalysisResult
from llm_code_lens.formatters.llm import format_analysis, _format_file_analysis
from llm_code_lens.formatters.llm import _format_python_file, _format_sql_file, _format_js_file

class TestFormatters:
    @pytest.fixture
    def sample_analysis(self):
        """Create a sample analysis result for testing."""
        return AnalysisResult(
            summary={
                'project_stats': {
                    'total_files': 2,
                    'by_type': {'.py': 1, '.js': 1},
                    'lines_of_code': 100,
                    'avg_file_size': 50.0
                },
                'code_metrics': {
                    'functions': {'count': 3, 'with_docs': 2, 'complex': 1},
                    'classes': {'count': 2, 'with_docs': 2},
                    'imports': {'count': 5, 'unique': ['import os', 'from pathlib import Path']}
                },
                'maintenance': {
                    'todos': [
                        {'file': 'test.py', 'text': 'Add tests', 'priority': 'high', 'line': 10},
                        {'file': 'app.js', 'text': 'Improve error handling', 'priority': 'medium', 'line': 20}
                    ],
                    'doc_coverage': 80.0,
                    'comments_ratio': 0.15
                },
                'structure': {
                    'entry_points': ['main.py'],
                    'core_files': ['core.py'],
                    'directories': ['src', 'tests']
                }
            },
            insights=[
                'Found 2 TODOs across 2 files',
                'Documentation coverage is good at 80%',
                'Complex function detected: process_data in data.py'
            ],
            files={
                'test.py': {
                    'type': 'python',
                    'imports': ['import pytest', 'from pathlib import Path'],
                    'functions': [
                        {
                            'name': 'test_func',
                            'args': ['x: int'],
                            'docstring': 'Test function',
                            'line_number': 5,
                            'loc': 10,
                            'complexity': 2
                        }
                    ],
                    'classes': [
                        {
                            'name': 'TestClass',
                            'docstring': 'Test class',
                            'methods': ['test_method'],
                            'line_number': 15,
                            'complexity': 3
                        }
                    ],
                    'metrics': {'loc': 50, 'classes': 1, 'functions': 1},
                    'todos': [{'line': 10, 'text': 'Add more tests'}]
                },
                'app.js': {
                    'type': 'javascript',
                    'imports': ['import React from "react"'],
                    'exports': ['export default App'],
                    'functions': [
                        {
                            'name': 'App',
                            'line_number': 3
                        }
                    ],
                    'metrics': {'loc': 50},
                    'todos': [{'line': 20, 'text': 'Add error handling'}]
                }
            }
        )

    def test_format_analysis_structure(self, sample_analysis):
        """Test the overall structure of formatted analysis."""
        output = format_analysis(sample_analysis)
        
        # Test main sections
        assert 'CODEBASE SUMMARY:' in output
        assert 'KEY INSIGHTS:' in output
        assert 'CODE METRICS:' in output
        assert 'TODOS:' in output
        assert 'PROJECT STRUCTURE AND CODE INSIGHTS:' in output
        
        # Test ordering
        summary_pos = output.find('CODEBASE SUMMARY:')
        insights_pos = output.find('KEY INSIGHTS:')
        metrics_pos = output.find('CODE METRICS:')
        
        assert summary_pos < insights_pos < metrics_pos

    def test_format_analysis_content(self, sample_analysis):
        """Test the content of formatted analysis."""
        output = format_analysis(sample_analysis)
        
        # Test summary content
        assert 'This project contains 2 files' in output
        assert '.py: 1, .js: 1' in output
        assert 'Total lines of code: 100' in output
        assert 'Average file size: 50.0 lines' in output
        
        # Test metrics content
        assert 'Functions: 3 (2 documented, 1 complex)' in output
        assert 'Classes: 2 (2 documented)' in output
        assert 'Documentation coverage: 80.0%' in output
        
        # Test insights
        assert 'Found 2 TODOs across 2 files' in output
        assert 'Documentation coverage is good at 80%' in output

    def test_format_python_file(self, sample_analysis):
        """Test Python file formatting."""
        output = _format_python_file(sample_analysis.files['test.py'])
        formatted = '\n'.join(output)
        
        assert 'FUNCTIONS:' in formatted
        assert 'test_func:' in formatted
        assert 'Args: x: int' in formatted
        assert 'Line: 5' in formatted
        
        assert 'CLASSES:' in formatted
        assert 'TestClass:' in formatted
        assert 'Methods: test_method' in formatted
        assert 'Line: 15' in formatted

    def test_format_js_file(self, sample_analysis):
        """Test JavaScript file formatting."""
        output = _format_js_file(sample_analysis.files['app.js'])
        formatted = '\n'.join(output)
        
        assert 'EXPORTS:' in formatted
        assert 'export default App' in formatted
        assert 'FUNCTIONS:' in formatted
        assert 'App:' in formatted

        assert 'Line: 3' in formatted
        assert 'import React from "react"' in formatted

    def test_format_sql_file(self):
        """Test SQL file formatting."""
        sql_analysis = {
            'type': 'sql',
            'objects': [
                {
                    'type': 'procedure',
                    'name': 'ManageEmployeeData',
                    'definition': 'CREATE PROCEDURE...',
                    'loc': 50,
                    'complexity': 8
                },
                {
                    'type': 'view',
                    'name': 'EmployeeSummary',
                    'definition': 'CREATE VIEW...',
                    'loc': 20,
                    'complexity': 3
                }
            ],
            'parameters': [
                {
                    'name': 'Operation',
                    'data_type': 'NVARCHAR(10)',
                    'description': 'Operation type (INSERT, UPDATE, DELETE)'
                },
                {
                    'name': 'EmployeeID',
                    'data_type': 'INT',
                    'default': 'NULL'
                }
            ],
            'dependencies': ['Employees', 'Departments'],
            'todos': [
                {'line': 10, 'text': 'Add transaction handling'}
            ],
            'metrics': {'loc': 70}
        }
        
        output = _format_sql_file(sql_analysis)
        formatted = '\n'.join(output)
        
        assert 'PROCEDURE:' in formatted
        assert 'ManageEmployeeData' in formatted
        assert 'VIEW:' in formatted
        assert 'EmployeeSummary' in formatted
        assert 'PARAMETERS:' in formatted
        assert '@Operation (NVARCHAR(10))' in formatted
        assert 'DEPENDENCIES:' in formatted
        assert 'Employees' in formatted
        assert 'Departments' in formatted

    def test_format_empty_analysis(self):
        """Test formatting of empty analysis."""
        empty_analysis = AnalysisResult(
            summary={
                'project_stats': {
                    'total_files': 0,
                    'by_type': {},
                    'lines_of_code': 0,
                    'avg_file_size': 0
                },
                'code_metrics': {
                    'functions': {'count': 0, 'with_docs': 0, 'complex': 0},
                    'classes': {'count': 0, 'with_docs': 0},
                    'imports': {'count': 0, 'unique': []}
                },
                'maintenance': {
                    'todos': [],
                    'doc_coverage': 0,
                    'comments_ratio': 0
                },
                'structure': {
                    'entry_points': [],
                    'core_files': [],
                    'directories': []
                }
            },
            insights=[],
            files={}
        )
        
        output = format_analysis(empty_analysis)
        assert 'This project contains 0 files' in output
        assert 'Documentation coverage: 0.0%' in output
        assert 'Functions: 0 (0 documented, 0 complex)' in output

    def test_format_file_with_special_chars(self):
        """Test formatting file with special characters."""
        analysis = {
            'type': 'python',
            'imports': ['from special import *'],
            'functions': [
                {
                    'name': 'special_func',
                    'args': ['x'],
                    'docstring': 'Test with special chars: @#$%^&*()',
                    'line_number': 1,
                    'loc': 5
                }
            ],
            'metrics': {'loc': 10},
            'todos': [{'line': 1, 'text': 'Fix: <script>alert("xss")</script>'}]
        }
        
        output = _format_file_analysis('special.py', analysis)
        formatted = '\n'.join(output)
        
        assert 'special chars: @#$%^&*()' in formatted
        assert '<script>alert("xss")</script>' in formatted

    def test_format_large_file(self):
        """Test formatting of large files."""
        large_analysis = {
            'type': 'python',
            'imports': ['import ' + f'lib{i}' for i in range(100)],
            'functions': [
                {
                    'name': f'func{i}',
                    'args': ['x'],
                    'docstring': f'Function {i}',
                    'line_number': i,
                    'loc': 5
                }
                for i in range(100)
            ],
            'classes': [
                {
                    'name': f'Class{i}',
                    'docstring': f'Class {i}',
                    'methods': [f'method{j}' for j in range(10)],
                    'line_number': i * 100
                }
                for i in range(10)
            ],
            'metrics': {'loc': 10000}
        }
        
        output = _format_file_analysis('large.py', large_analysis)
        formatted = '\n'.join(output)
        
        assert 'IMPORTS:' in formatted
        assert 'FUNCTIONS:' in formatted
        assert 'CLASSES:' in formatted
        assert 'Lines: 10000' in formatted
        assert 'func0:' in formatted
        assert 'func99:' in formatted
        assert 'Class0:' in formatted
        assert 'Class9:' in formatted

    def test_directory_grouping(self, sample_analysis):
        """Test directory-based grouping in formatted output."""
        # Add files in different directories
        sample_analysis.files.update({
            'src/core/main.py': {
                'type': 'python',
                'metrics': {'loc': 30},
                'functions': [{'name': 'main', 'line_number': 1}]
            },
            'src/utils/helpers.py': {
                'type': 'python',
                'metrics': {'loc': 20},
                'functions': [{'name': 'helper', 'line_number': 1}]
            },
            'tests/test_main.py': {
                'type': 'python',
                'metrics': {'loc': 40},
                'functions': [{'name': 'test_main', 'line_number': 1}]
            }
        })
        
        output = format_analysis(sample_analysis)
        
        # Check directory grouping
        assert 'src/core/' in output
        assert 'src/utils/' in output
        assert 'tests/' in output
        
        # Check order and hierarchy
        src_pos = output.find('src/')
        tests_pos = output.find('tests/')
        assert src_pos < tests_pos

    def test_format_with_errors(self):
        """Test formatting of analysis with errors."""
        analysis_with_errors = {
            'type': 'python',
            'errors': [
                {
                    'type': 'syntax_error',
                    'line': 10,
                    'text': 'invalid syntax'
                },
                {
                    'type': 'import_error',
                    'text': 'module not found'
                }
            ],
            'metrics': {'loc': 0}
        }
        
        output = _format_file_analysis('error.py', analysis_with_errors)
        formatted = '\n'.join(output)
        
        assert 'ERRORS:' in formatted
        assert 'Line 10: invalid syntax' in formatted
        assert 'Import Error: module not found' in formatted

    def test_format_with_unicode(self):
        """Test formatting of content with Unicode characters."""
        unicode_analysis = {
            'type': 'python',
            'functions': [
                {
                    'name': 'unicode_func',
                    'args': ['x'],
                    'docstring': '测试函数 - テスト関数',
                    'line_number': 1
                }
            ],
            'todos': [
                {'line': 1, 'text': '完善这个功能 🚀'}
            ],
            'metrics': {'loc': 10}
        }
        
        output = _format_file_analysis('unicode.py', unicode_analysis)
        formatted = '\n'.join(output)
        
        assert '测试函数' in formatted
        assert 'テスト関数' in formatted
        assert '完善这个功能 🚀' in formatted

if __name__ == '__main__':
    pytest.main(['-v'])