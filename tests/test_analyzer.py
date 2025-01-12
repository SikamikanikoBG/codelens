import pytest
from pathlib import Path
from llm_code_lens.analyzer import ProjectAnalyzer, PythonAnalyzer, JavaScriptAnalyzer, SQLServerAnalyzer

def test_python_basic_analysis(tmp_path):
    """Test basic Python analysis functionality."""
    analyzer = PythonAnalyzer()
    test_file = tmp_path / "test.py"
    test_file.write_text('''
def test_function():
    """Test docstring."""
    return True
''')
    
    result = analyzer.analyze_file(test_file)
    assert len(result['functions']) == 1
    assert result['functions'][0]['name'] == 'test_function'
    assert result['functions'][0]['docstring'] == 'Test docstring.'

def test_python_complex_analysis(tmp_path):
    """Test complex Python features analysis."""
    analyzer = PythonAnalyzer()
    test_file = tmp_path / "test.py"
    test_file.write_text('''
from typing import List, Optional
import os.path
from pathlib import Path

class BaseClass:
    """Base class docstring."""
    pass

class TestClass(BaseClass):
    """Test class with features."""
    
    def __init__(self, value: int = 0):
        self.value = value
    
    @property
    def prop(self) -> int:
        """Property docstring."""
        return self.value
    
    @classmethod
    def create(cls) -> 'TestClass':
        return cls()
    
    @staticmethod
    def helper() -> bool:
        return True

async def async_function(param: str) -> bool:
    """Async function with complexity."""
    if param:
        for i in range(10):
            if i % 2 == 0:
                continue
            else:
                break
    return True
''')
    
    result = analyzer.analyze_file(test_file)
    
    # Check imports
    assert len(result['imports']) >= 3
    
    # Check classes
    assert len(result['classes']) == 2
    test_class = [c for c in result['classes'] if c['name'] == 'TestClass'][0]
    assert test_class['docstring'] == 'Test class with features.'
    assert 'BaseClass' in test_class['bases']
    assert len(test_class['methods']) >= 4
    
    # Check methods
    methods = {m['name']: m for m in test_class['methods']}
    assert methods['prop']['is_property']
    assert methods['create']['is_classmethod']
    assert methods['helper']['is_staticmethod']
    
    # Check async function
    async_func = [f for f in result['functions'] if f['name'] == 'async_function'][0]
    assert async_func['is_async']
    assert async_func['complexity'] > 1

def test_python_comments_todos(tmp_path):
    """Test Python comments and TODOs analysis."""
    analyzer = PythonAnalyzer()
    test_file = tmp_path / "test.py"
    test_file.write_text('''
# Regular comment
def function():
    # TODO: Implement this
    pass

"""
Module docstring.
TODO: Update documentation
"""

# FIXME: Critical bug
class TestClass:
    """Class docstring."""
    def method(self):
        # Another comment
        return True
''')
    
    result = analyzer.analyze_file(test_file)
    assert len(result['todos']) >= 2
    assert len(result['comments']) >= 2
    assert any('Critical bug' in todo['text'] for todo in result['todos'])

def test_javascript_analysis(tmp_path):
    """Test JavaScript file analysis with various features."""
    analyzer = JavaScriptAnalyzer()
    test_file = tmp_path / "test.js"
    test_file.write_text('''
import React, { useState } from 'react';
import * as utils from './utils';
export { default as Component } from './Component';
export const constant = 42;

// Regular comment
function TestComponent() {
    // TODO: Add error handling
    return null;
}

/* Multi-line
   comment */
class MyClass extends BaseClass {
    constructor() {
        super();
        this.state = {};
    }

    // FIXME: Fix this method
    method() {
        return true;
    }
}

const ArrowFunction = () => {
    return {};
};

async function asyncFunction() {
    return Promise.resolve();
}
''')
    
    result = analyzer.analyze_file(test_file)
    
    # Check imports and exports
    assert len(result['imports']) == 2
    assert len(result['exports']) == 2
    
    # Check functions
    assert len(result['functions']) >= 3
    assert any(f['name'] == 'TestComponent' for f in result['functions'])
    assert any(f['name'] == 'ArrowFunction' for f in result['functions'])
    assert any(f['name'] == 'asyncFunction' for f in result['functions'])
    
    # Check classes
    assert len(result['classes']) == 1
    assert result['classes'][0]['name'] == 'MyClass'
    assert result['classes'][0]['extends'] == 'BaseClass'
    
    # Check comments and TODOs
    assert len(result['todos']) >= 2
    assert len(result['comments']) >= 2
    assert any('error handling' in todo['text'] for todo in result['todos'])
    
    # Check metrics
    assert result['metrics']['functions'] > 0
    assert result['metrics']['classes'] > 0
    assert result['metrics']['imports'] > 0

def test_sql_analysis(tmp_path):
    """Test SQL file analysis with various features."""
    analyzer = SQLServerAnalyzer()
    test_file = tmp_path / "test.sql"
    test_file.write_text('''
-- Regular comment
/* Multi-line
   comment */

-- TODO: Add error handling
CREATE PROCEDURE dbo.TestProc
    @param1 int = NULL,               -- Input parameter
    @param2 varchar(50),              -- Name parameter
    @param3 decimal(18,2) = 0.0,      -- Amount
    @result int OUTPUT                -- Output parameter
AS
BEGIN
    SET NOCOUNT ON;
    
    -- FIXME: Add validation
    IF @param1 IS NULL
        RETURN;

    -- Complex logic with multiple dependencies
    WITH CTE AS (
        SELECT t1.Col1, t2.Col2
        FROM Table1 t1
        JOIN Table2 t2 ON t1.Id = t2.Id
        WHERE EXISTS (SELECT 1 FROM Table3)
    )
    INSERT INTO TargetTable (Col1, Col2)
    SELECT Col1, Col2 FROM CTE;
    
    -- Update related data
    UPDATE Table4
    SET Status = 'Processed'
    WHERE Id = @param1;
    
    RETURN 0;
END
GO

CREATE VIEW dbo.TestView
AS
    SELECT a.Col1, b.Col2
    FROM Table5 a
    JOIN Table6 b ON a.Id = b.Id;
GO

CREATE FUNCTION dbo.TestFunction
(
    @value int
)
RETURNS int
AS
BEGIN
    RETURN @value * 2;
END
''')
    
    result = analyzer.analyze_file(test_file)
    
    # Check objects
    assert result['objects'], "Should find SQL objects"
    assert len(result['objects']) >= 2
    assert any(obj['type'] == 'procedure' and obj['name'] == 'dbo.TestProc' for obj in result['objects'])
    assert any(obj['type'] == 'view' and obj['name'] == 'dbo.TestView' for obj in result['objects'])
    
    # Check parameters
    assert result['parameters'], "Should find parameters"
    assert len(result['parameters']) >= 4
    param_names = {p['name'] for p in result['parameters']}
    assert 'param1' in param_names, "Should find param1"
    assert 'result' in param_names, "Should find result parameter"
    
    # Check parameter details
    params = {p['name']: p for p in result['parameters']}
    assert params['param1']['data_type'] == 'int'
    assert params['param1']['default'] == 'NULL'
    assert 'Input parameter' in params['param1'].get('description', '')
    
    # Check dependencies
    assert result['dependencies'], "Should find dependencies"
    assert len(result['dependencies']) >= 6
    assert all(table in result['dependencies'] for table in ['Table1', 'Table2', 'TargetTable', 'Table4'])
    
    # Check comments and TODOs
    assert result['comments'], "Should find comments"
    assert len(result['comments']) >= 3
    assert result['todos'], "Should find TODOs"
    assert len(result['todos']) >= 2
    assert any('validation' in todo['text'] for todo in result['todos'])
    assert any('error handling' in todo['text'] for todo in result['todos'])
    
    # Check metrics
    assert 'metrics' in result, "Should include metrics"
    assert result['metrics']['complexity'] > 0, "Should calculate complexity"
    assert result['metrics'].get('loc', 0) > 0, "Should count lines of code"

def test_project_analysis(tmp_path):
    """Test project-wide analysis."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()
    
    # Create a test Python file
    py_file = project_dir / "main.py"
    py_file.write_text('def main(): pass')
    
    analyzer = ProjectAnalyzer()
    result = analyzer.analyze(project_dir)
    
    assert result.summary['project_stats']['total_files'] == 1
    assert len(result.files) == 1
    assert any('main.py' in path for path in result.files)


def test_python_nested_classes(tmp_path):
    """Test analysis of nested class definitions and methods."""
    analyzer = PythonAnalyzer()
    test_file = tmp_path / "test.py"
    test_file.write_text('''
class Outer:
    """Outer class docstring."""
    
    class Inner:
        """Inner class docstring."""
        
        def inner_method(self):
            """Inner method docstring."""
            pass
    
    def outer_method(self):
        class LocalClass:
            pass
        return LocalClass()

    @property
    def prop(self): return None

    @classmethod
    def cls_method(cls): pass

    @staticmethod
    def static_method(): pass
''')
    
    result = analyzer.analyze_file(test_file)
    # Fix: Update assertion to account for LocalClass or filter non-nested classes
    outer_class = next(c for c in result['classes'] if c['name'] == 'Outer')
    assert len(outer_class['methods']) == 4  # outer_method, prop, cls_method, static_method
    assert any(m['is_property'] for m in outer_class['methods'] if m['name'] == 'prop')
    assert any(m['is_classmethod'] for m in outer_class['methods'] if m['name'] == 'cls_method')
    assert any(m['is_staticmethod'] for m in outer_class['methods'] if m['name'] == 'static_method')


def test_function_complexity_cases(tmp_path):
    """Test various cases that affect cyclomatic complexity."""
    analyzer = PythonAnalyzer()
    test_file = tmp_path / "test.py"
    test_file.write_text('''
def complex_function(x, y):
    """Function with various complexity factors."""
    if x > 0:
        if y > 0:
            return x + y
        else:
            return x - y
    elif x < 0:
        for i in range(y):
            try:
                result = x / i
            except ZeroDivisionError:
                continue
            except ValueError:
                break
    else:
        return x if y > 0 else -x
    
    return result if 'result' in locals() else None
''')
    
    result = analyzer.analyze_file(test_file)
    func = result['functions'][0]
    assert func['complexity'] > 5  # Should have high complexity due to conditions and error handling


def test_complex_decorators(tmp_path):
    """Test handling of complex decorator patterns."""
    analyzer = PythonAnalyzer()
    test_file = tmp_path / "test.py"
    test_file.write_text('''
import functools
from typing import TypeVar, Callable

T = TypeVar('T')

def decorator_with_args(arg1: str, arg2: int = 0):
    def actual_decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            return func(*args, **kwargs)
        return wrapper
    return actual_decorator

class ClassWithComplexDecorators:
    @property
    @functools.cache
    def cached_prop(self):
        return 42

    @decorator_with_args("test", arg2=10)
    def complex_decorated(self):
        return True
''')
    
    result = analyzer.analyze_file(test_file)
    class_info = result['classes'][0]
    assert any('decorator_with_args' in str(method['decorators']) 
              for method in class_info['methods']
              if method['name'] == 'complex_decorated')
    assert any(method['is_property']
              for method in class_info['methods']
              if method['name'] == 'cached_prop')

def test_binary_and_unicode_handling(tmp_path):
    """Test handling of binary and unicode content in Python files."""
    analyzer = PythonAnalyzer()
    test_file = tmp_path / "test.py"
    
    # Test file with mixed encodings and special characters
    content = '''
# -*- coding: utf-8 -*-
"""Documentation with unicode: áéíóú."""

def test_unicode():
    """Test unicode strings: 你好, 🌍"""
    return "Hello, 世界"

# Binary content representation
BINARY_DATA = b"\\x00\\x01\\x02"
'''.encode('utf-8')
    
    test_file.write_bytes(content)
    result = analyzer.analyze_file(test_file)
    
    assert result['functions'][0]['docstring'] == 'Test unicode strings: 你好, 🌍'
    assert len(result['comments']) > 0

def test_error_recovery_and_partial_parsing(tmp_path):
    """Test analyzer's ability to recover from various error conditions."""
    analyzer = PythonAnalyzer()
    test_file = tmp_path / "test.py"
    
    # Test with syntax error
    test_file.write_text('''
def valid_function():
    pass

def invalid_function(
    # Missing closing parenthesis
    return None

def another_valid_function():
    pass
''')
    
    result = analyzer.analyze_file(test_file)
    assert 'errors' in result
    assert any(error['type'] == 'syntax_error' for error in result['errors'])
    
    # Test with encoding error
    test_file.write_bytes(b'\x80\x81\x82invalid bytes\xaa\xbb\xcc')
    result = analyzer.analyze_file(test_file)
    assert 'errors' in result