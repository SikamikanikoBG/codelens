import pytest
from llm_code_lens.analyzer.base import AnalysisResult
from llm_code_lens.formatters.llm import format_analysis, _format_file_analysis

@pytest.fixture
def sample_analysis():
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
                'imports': ['import pytest', 'from pathlib import Path'],
                'functions': [
                    {
                        'name': 'test_func',
                        'args': ['x'],
                        'docstring': 'Test function',
                        'line_number': 5,
                        'loc': 10
                    }
                ],
                'classes': [
                    {
                        'name': 'TestClass',
                        'docstring': 'Test class',
                        'methods': ['test_method'],
                        'line_number': 15
                    }
                ],
                'metrics': {'loc': 50, 'classes': 1, 'functions': 1},
                'todos': [{'line': 10, 'text': 'Add more tests'}]
            }
        }
    )

def test_format_analysis_structure(sample_analysis):
    """Test the overall structure of formatted analysis."""
    output = format_analysis(sample_analysis)
    
    # Test main sections
    assert 'CODEBASE SUMMARY:' in output
    assert 'KEY INSIGHTS:' in output
    assert 'CODE METRICS:' in output
    assert 'TODOS:' in output
    assert 'PROJECT STRUCTURE AND CODE INSIGHTS:' in output

def test_format_analysis_summary(sample_analysis):
    """Test summary section formatting."""
    output = format_analysis(sample_analysis)
    
    # Test summary content
    assert 'This project contains 2 files' in output
    assert '.py: 1, .js: 1' in output
    assert 'Total lines of code: 100' in output
    assert 'Average file size: 50.0 lines' in output

def test_format_analysis_metrics(sample_analysis):
    """Test metrics section formatting."""
    output = format_analysis(sample_analysis)
    
    # Test metrics content
    assert 'Functions: 3 (2 documented)' in output
    assert 'Classes: 2 (2 documented)' in output
    assert 'Documentation coverage: 80.0%' in output

def test_format_analysis_todos(sample_analysis):
    """Test TODOs section formatting."""
    output = format_analysis(sample_analysis)
    
    # Test TODOs content
    assert '[high] test.py: Add tests' in output
    assert '[medium] app.js: Improve error handling' in output

def test_format_file_analysis_basic(sample_analysis):
    """Test basic file analysis formatting."""
    filename = 'test.py'
    analysis = sample_analysis.files['test.py']
    output = _format_file_analysis(filename, analysis)
    formatted = '\n'.join(output)
    
    # Test basic file info
    assert filename in formatted
    assert 'Lines: 50' in formatted

def test_format_file_analysis_imports(sample_analysis):
    """Test imports section formatting."""
    output = _format_file_analysis('test.py', sample_analysis.files['test.py'])
    formatted = '\n'.join(output)
    
    # Test imports section
    assert 'IMPORTS:' in formatted
    assert 'import pytest' in formatted
    assert 'from pathlib import Path' in formatted

def test_format_file_analysis_functions(sample_analysis):
    """Test functions section formatting."""
    output = _format_file_analysis('test.py', sample_analysis.files['test.py'])
    formatted = '\n'.join(output)
    
    # Test functions section
    assert 'FUNCTIONS:' in formatted
    assert 'test_func:' in formatted
    assert 'Args: x' in formatted
    assert 'Line: 5' in formatted
    assert 'Doc: Test function' in formatted

def test_format_file_analysis_classes(sample_analysis):
    """Test classes section formatting."""
    output = _format_file_analysis('test.py', sample_analysis.files['test.py'])
    formatted = '\n'.join(output)
    
    # Test classes section
    assert 'CLASSES:' in formatted
    assert 'TestClass:' in formatted
    assert 'Line: 15' in formatted
    assert 'Methods: test_method' in formatted
    assert 'Doc: Test class' in formatted

def test_format_empty_analysis():
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
    assert 'Functions: 0 (0 documented)' in output

def test_format_file_with_special_chars():
    """Test formatting file with special characters."""
    analysis = {
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