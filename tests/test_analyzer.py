import pytest
from pathlib import Path
from llm_code_lens.analyzer.base import ProjectAnalyzer, AnalysisResult
from llm_code_lens.analyzer.python import PythonAnalyzer
from llm_code_lens.analyzer.javascript import JavaScriptAnalyzer

@pytest.fixture
def python_file(tmp_path):
    """Create a sample Python file for testing."""
    file_path = tmp_path / "test.py"
    content = '''
import os
from pathlib import Path
import sys as system

def simple_function(arg1, arg2):
    """This is a simple function."""
    return arg1 + arg2

def complex_function():
    # This is a long function
    x = 1
    y = 2
    z = 3
    return x + y + z

class TestClass:
    """Test class documentation."""
    def __init__(self):
        self.value = 0
    
    def method(self):
        """Method documentation."""
        return self.value

# TODO: Add more test cases
# FIXME: This needs attention
'''
    file_path.write_text(content)
    return file_path

@pytest.fixture
def js_file(tmp_path):
    """Create a sample JavaScript file for testing."""
    file_path = tmp_path / "test.js"
    content = '''
import { Component } from 'react';
import * as utils from './utils';

function simpleFunction(arg1, arg2) {
    return arg1 + arg2;
}

const arrowFunction = (x) => {
    return x * 2;
};

class TestClass {
    constructor() {
        this.value = 0;
    }
    
    method() {
        return this.value;
    }
}

// TODO: Implement error handling
/* This is a multiline
   comment */
'''
    file_path.write_text(content)
    return file_path

def test_python_analyzer_imports(python_file):
        """Test Python import analysis."""
        analyzer = PythonAnalyzer()
        result = analyzer.analyze_file(python_file)
        
        assert len(result['imports']) == 3
        assert 'import os' in result['imports']
        assert 'from pathlib import Path' in result['imports']
        assert 'import sys' in result['imports']  # Changed from 'import sys as system'

def test_python_analyzer_functions(python_file):
    """Test Python function analysis."""
    analyzer = PythonAnalyzer()
    result = analyzer.analyze_file(python_file)
    
    # Count only top-level functions (excluding methods)
    top_level_funcs = [f for f in result['functions'] 
                        if not any(c['methods'] for c in result.get('classes', [])
                            if f['name'] in c['methods'])]
    assert len(top_level_funcs) == 2

def test_python_analyzer_classes(python_file):
    """Test Python class analysis."""
    analyzer = PythonAnalyzer()
    result = analyzer.analyze_file(python_file)
    
    assert len(result['classes']) == 1
    test_class = result['classes'][0]
    assert test_class['name'] == 'TestClass'
    assert test_class['docstring'] == 'Test class documentation.'
    assert set(test_class['methods']) == {'__init__', 'method'}

def test_python_analyzer_todos(python_file):
    """Test Python TODO analysis."""
    analyzer = PythonAnalyzer()
    result = analyzer.analyze_file(python_file)
    
    assert len(result['todos']) == 2
    assert any('Add more test cases' in todo['text'] for todo in result['todos'])
    assert any('This needs attention' in todo['text'] for todo in result['todos'])

def test_javascript_analyzer_imports(js_file):
    """Test JavaScript import analysis."""
    analyzer = JavaScriptAnalyzer()
    result = analyzer.analyze_file(js_file)
    
    assert len(result['imports']) == 2
    assert any('Component' in imp for imp in result['imports'])
    assert any('utils' in imp for imp in result['imports'])

def test_javascript_analyzer_functions(js_file):
    """Test JavaScript function analysis."""
    analyzer = JavaScriptAnalyzer()
    result = analyzer.analyze_file(js_file)
    
    assert len(result['functions']) == 2
    assert any(f['name'] == 'simpleFunction' for f in result['functions'])
    assert any(f['name'] == 'arrowFunction' for f in result['functions'])

def test_javascript_analyzer_classes(js_file):
    """Test JavaScript class analysis."""
    analyzer = JavaScriptAnalyzer()
    result = analyzer.analyze_file(js_file)
    
    assert len(result['classes']) == 1
    test_class = result['classes'][0]
    assert test_class['name'] == 'TestClass'

def test_javascript_analyzer_comments(js_file):
    """Test JavaScript comment analysis."""
    analyzer = JavaScriptAnalyzer()
    result = analyzer.analyze_file(js_file)
    
    assert len(result['comments']) >= 1
    assert any('multiline' in comment['text'] for comment in result['comments'])

def test_javascript_analyzer_todos(js_file):
    """Test JavaScript TODO analysis."""
    analyzer = JavaScriptAnalyzer()
    result = analyzer.analyze_file(js_file)
    
    assert len(result['todos']) == 1
    assert 'Implement error handling' in result['todos'][0]['text']

def test_project_analyzer_empty_directory(tmp_path):
    """Test ProjectAnalyzer with empty directory."""
    analyzer = ProjectAnalyzer()
    result = analyzer.analyze(tmp_path)
    
    assert isinstance(result, AnalysisResult)
    assert result.summary['project_stats']['total_files'] == 0
    assert len(result.files) == 0

def test_project_analyzer_mixed_files(python_file, js_file):
    """Test ProjectAnalyzer with mixed file types."""
    analyzer = ProjectAnalyzer()
    result = analyzer.analyze(python_file.parent)
    
    assert isinstance(result, AnalysisResult)
    assert result.summary['project_stats']['total_files'] == 2
    assert len(result.files) == 2
    
    # Check file extensions are properly counted
    assert result.summary['project_stats']['by_type']['.py'] == 1
    assert result.summary['project_stats']['by_type']['.js'] == 1

def test_analyzer_error_handling(tmp_path):
    """Test analyzer error handling with invalid files."""
    # Create invalid Python file
    invalid_py = tmp_path / "invalid.py"
    invalid_py.write_text("def invalid_syntax(:")
    
    # Create invalid Python file
    invalid_py = tmp_path / "invalid.py"
    invalid_py.write_text("def invalid_syntax(:")
    
    # Create invalid JavaScript file
    invalid_js = tmp_path / "invalid.js"
    invalid_js.write_text("function invalid_syntax { console.log('missing parentheses'")
    
    analyzer = ProjectAnalyzer()
    result = analyzer.analyze(tmp_path)
    
    # Analysis should complete despite errors
    assert isinstance(result, AnalysisResult)
    assert len(result.files) == 2  # Both files should be included
    
    # Check for error indicators in results
    py_analysis = result.files[str(invalid_py)]
    assert 'errors' in py_analysis
    
    js_analysis = result.files[str(invalid_js)]
    assert js_analysis['metrics']['loc'] > 0  # Basic metrics should still work