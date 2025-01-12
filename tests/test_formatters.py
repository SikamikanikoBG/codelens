import pytest
from llm_code_lens.formatters.llm import (
    format_analysis, _format_file_analysis, _format_python_file,
    _format_js_file, _format_sql_file, _format_todo
)
from llm_code_lens.analyzer.base import AnalysisResult


def test_basic_format():
    """Test basic analysis formatting."""
    analysis = AnalysisResult(
        summary={
            'project_stats': {
                'total_files': 1,
                'by_type': {'.py': 1},
                'lines_of_code': 10,
                'avg_file_size': 10
            },
            'code_metrics': {
                'functions': {'count': 1, 'with_docs': 1, 'complex': 0},
                'classes': {'count': 0, 'with_docs': 0},
                'imports': {'count': 0, 'unique': []}
            },
            'maintenance': {'todos': [], 'doc_coverage': 100},
            'structure': {
                'directories': ['.'],
                'entry_points': [],
                'core_files': []
            }
        },
        insights=['Test insight'],
        files={'test.py': {'type': 'python', 'metrics': {'loc': 10, 'complexity': 1}}}
    )
    
    result = format_analysis(analysis)
    assert isinstance(result, str)
    assert 'CODEBASE SUMMARY:' in result
    assert 'Test insight' in result
    assert 'CODE METRICS:' in result

def test_python_format():
    """Test Python-specific formatting."""
    analysis = {
        'type': 'python',
        'functions': [{
            'name': 'test_func',
            'line_number': 1,
            'docstring': 'Test function',
            'args': ['arg1', 'arg2'],
            'return_type': 'str'
        }],
        'classes': [{
            'name': 'TestClass',
            'line_number': 10,
            'docstring': 'Test class',
            'methods': ['method1']
        }]
    }
    
    result = _format_python_file(analysis)
    formatted = '\n'.join(result)
    assert 'test_func' in formatted
    assert 'TestClass' in formatted

def test_js_format():
    """Test JavaScript-specific formatting."""
    analysis = {
        'type': 'javascript',
        'imports': ['import React from "react"'],
        'exports': ['export default App'],
        'functions': [{
            'name': 'App',
            'line_number': 1
        }]
    }
    
    result = _format_js_file(analysis)
    formatted = '\n'.join(result)
    assert 'import React' in formatted
    assert 'App' in formatted

def test_sql_format():
    """Test SQL-specific formatting."""
    analysis = {
        'type': 'sql',
        'objects': [{
            'type': 'procedure',
            'name': 'test_proc',
            'metrics': {'lines': 10, 'complexity': 2}
        }],
        'parameters': [{
            'name': 'param1',
            'data_type': 'int',
            'description': 'Test parameter'
        }]
    }
    
    result = _format_sql_file(analysis)
    formatted = '\n'.join(result)
    assert 'test_proc' in formatted
    assert 'param1' in formatted


def test_format_analysis_empty_result():
    """Test formatting with minimal/empty analysis result."""
    empty_result = AnalysisResult(
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
                'imports': {'count': 0, 'unique': set()}
            },
            'maintenance': {'todos': [], 'doc_coverage': 0},
            'structure': {
                'directories': [],
                'entry_points': [],
                'core_files': []
            }
        },
        insights=[],
        files={}
    )
    
    result = format_analysis(empty_result)
    assert isinstance(result, str)
    assert 'CODEBASE SUMMARY:' in result
    assert 'Total lines of code: 0' in result
    assert 'Overall complexity: 0' in result

def test_format_file_analysis_with_errors():
    """Test formatting file analysis with various error types."""
    analysis = {
        'type': 'python',
        'metrics': {'loc': 100, 'complexity': 5},
        'errors': [
            {'line': 10, 'text': 'Syntax error', 'type': 'syntax_error'},
            {'text': 'Import error', 'type': 'import_error'}
        ]
    }
    
    result = _format_file_analysis('test.py', analysis)
    formatted = '\n'.join(result)
    assert 'ERRORS:' in formatted
    assert 'Line 10: Syntax error' in formatted
    assert 'Import Error: Import error' in formatted

def test_format_python_file_complex_methods():
    """Test Python file formatting with complex method structures."""
    analysis = {
        'type': 'python',
        'classes': [{
            'name': 'TestClass',
            'line_number': 1,
            'bases': ['BaseClass'],
            'docstring': 'Test class docstring',
            'methods': [
                {'name': 'regular_method', 'type': 'instance'},
                {'name': 'class_method', 'type': 'class', 'is_classmethod': True},
                {'name': 'static_method', 'type': 'static', 'is_staticmethod': True},
                {'name': 'property_method', 'type': 'property', 'is_property': True}
            ]
        }],
        'functions': [{
            'name': 'test_func',
            'line_number': 50,
            'args': [{'name': 'arg1', 'type': 'str'}, {'name': 'arg2', 'type': 'int'}],
            'return_type': 'bool',
            'docstring': 'Test function docstring',
            'decorators': ['@decorator1', '@decorator2'],
            'complexity': 5,
            'is_async': True
        }]
    }
    
    result = _format_python_file(analysis)
    formatted = '\n'.join(result)
    
    # Check class formatting
    assert 'TestClass:' in formatted
    assert 'Inherits: BaseClass' in formatted
    assert 'Instance methods: regular_method' in formatted
    assert 'Class methods: class_method' in formatted
    assert 'Static methods: static_method' in formatted
    assert 'Properties: property_method' in formatted
    
    # Check function formatting
    assert 'test_func:' in formatted
    assert 'Args: arg1: str, arg2: int' in formatted
    assert 'Returns: bool' in formatted
    assert 'Decorators: @decorator1, @decorator2' in formatted
    assert 'Complexity: 5' in formatted
    assert 'Async: Yes' in formatted

def test_format_js_file_complete():
    """Test JavaScript file formatting with all possible elements."""
    analysis = {
        'type': 'javascript',
        'imports': [
            'import React from "react"',
            'import { useState } from "react"'
        ],
        'exports': [
            'export default App',
            'export const helper'
        ],
        'classes': [{
            'name': 'Component',
            'line_number': 10,
            'extends': 'React.Component',
            'methods': ['render', 'componentDidMount']
        }],
        'functions': [{
            'name': 'useCustomHook',
            'line_number': 30,
            'params': ['initialValue', 'options']
        }]
    }
    
    result = _format_js_file(analysis)
    formatted = '\n'.join(result)
    
    assert 'IMPORTS:' in formatted
    assert 'import React from "react"' in formatted
    assert 'EXPORTS:' in formatted
    assert 'export default App' in formatted
    assert 'Component:' in formatted
    assert 'Extends: React.Component' in formatted
    assert 'Methods: render, componentDidMount' in formatted
    assert 'useCustomHook:' in formatted
    assert 'Parameters: initialValue, options' in formatted

def test_format_sql_file_complete():
    """Test SQL file formatting with all possible elements."""
    analysis = {
        'type': 'sql',
        'objects': [{
            'type': 'procedure',
            'name': 'dbo.ProcessData',
            'metrics': {'lines': 50, 'complexity': 8}
        }],
        'parameters': [
            {'name': 'InputData', 'data_type': 'varchar(max)', 'default': 'NULL', 
             'description': 'Input JSON data'},
            {'name': 'Debug', 'data_type': 'bit', 'default': '0'}
        ],
        'dependencies': ['dbo.Users', 'dbo.Logs'],
        'comments': [
            {'line': 1, 'text': 'Main processing procedure'},
            {'line': 10, 'text': 'Validation section'}
        ]
    }
    
    result = _format_sql_file(analysis)
    formatted = '\n'.join(result)
    
    assert 'PROCEDURE:' in formatted
    assert 'Name: dbo.ProcessData' in formatted
    assert 'Lines: 50' in formatted
    assert 'Complexity: 8' in formatted
    assert 'PARAMETERS:' in formatted
    assert '@InputData (varchar(max), default=NULL) -- Input JSON data' in formatted
    assert 'DEPENDENCIES:' in formatted
    assert 'dbo.Users' in formatted
    assert 'COMMENTS:' in formatted
    assert 'Line 1: Main processing procedure' in formatted

def test_format_todo():
    """Test TODO formatting with various priorities."""
    todos = [
        {'priority': 'HIGH', 'file': 'main.py', 'text': 'Fix critical bug'},
        {'priority': 'LOW', 'file': 'utils.py', 'text': 'Add documentation'}
    ]
    
    for todo in todos:
        result = _format_todo(todo)
        assert f"[{todo['priority']}]" in result
        assert todo['file'] in result
        assert todo['text'] in result