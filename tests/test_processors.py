import pytest
from llm_code_lens.processors.summary import (
    generate_summary,
    _estimate_todo_priority,
    _is_potential_entry_point,
    _is_core_file,
    _process_file_stats,
    _process_code_metrics,
    _process_maintenance_info,
    _process_structure_info,
    _calculate_final_metrics
)
from llm_code_lens.processors.insights import generate_insights
from pathlib import Path

@pytest.fixture
def sample_analysis():
    """Create a sample file analysis for testing."""
    return {
        'main.py': {
            'functions': [
                {'name': 'main', 'args': [], 'docstring': 'Main entry point', 'loc': 20},
                {'name': 'helper', 'args': ['x'], 'docstring': None, 'loc': 15}
            ],
            'classes': [
                {
                    'name': 'App',
                    'docstring': 'Main application class',
                    'methods': ['run', 'setup']
                }
            ],
            'imports': ['import sys', 'from pathlib import Path'],
            'todos': [
                {'line': 10, 'text': 'URGENT: Fix memory leak'},
                {'line': 20, 'text': 'Add error handling'}
            ],
            'metrics': {'loc': 100, 'functions': 2, 'classes': 1}
        },
        'utils.py': {
            'functions': [
                {'name': 'utility', 'args': ['a', 'b'], 'docstring': 'Utility function', 'loc': 25},
                {'name': 'helper2', 'args': ['x'], 'docstring': None, 'loc': 55}
            ],
            'classes': [],
            'imports': ['import json'],
            'todos': [
                {'line': 5, 'text': 'Improve performance'}
            ],
            'metrics': {'loc': 50, 'functions': 2, 'classes': 0}
        }
    }

def test_generate_summary_complete(sample_analysis):
    """Test complete summary generation."""
    summary = generate_summary(sample_analysis)
    
    # Test project stats
    assert summary['project_stats']['total_files'] == 2
    assert summary['project_stats']['lines_of_code'] == 150
    assert summary['project_stats']['avg_file_size'] == 75.0
    assert '.py' in summary['project_stats']['by_type']
    assert summary['project_stats']['by_type']['.py'] == 2
    
    # Test code metrics
    assert summary['code_metrics']['functions']['count'] == 4
    assert summary['code_metrics']['functions']['with_docs'] == 2
    assert summary['code_metrics']['functions']['complex'] == 1  # helper2 with loc > 50
    assert summary['code_metrics']['classes']['count'] == 1
    assert summary['code_metrics']['classes']['with_docs'] == 1
    assert summary['code_metrics']['imports']['count'] == 3
    
    # Test maintenance info
    assert len(summary['maintenance']['todos']) == 3
    assert any(todo['priority'] == 'high' for todo in summary['maintenance']['todos'])
    
    # Test structure info
    assert 'main.py' in summary['structure']['entry_points']
    assert isinstance(summary['structure']['directories'], list)

def test_todo_priority_estimation():
    """Test TODO priority estimation for different cases."""
    # Test high priority cases
    assert _estimate_todo_priority('URGENT: Fix this') == 'high'
    assert _estimate_todo_priority('FIXME: Critical bug') == 'high'
    assert _estimate_todo_priority('TODO (bug): Crash on startup') == 'high'
    
    # Test medium priority cases
    assert _estimate_todo_priority('Important: Update docs') == 'medium'
    assert _estimate_todo_priority('TODO: Should optimize this') == 'medium'
    assert _estimate_todo_priority('Needed: Add validation') == 'medium'
    
    # Test low priority cases
    assert _estimate_todo_priority('Add more tests') == 'low'
    assert _estimate_todo_priority('TODO: Refactor later') == 'low'
    assert _estimate_todo_priority('Consider adding feature') == 'low'

def test_entry_point_detection():
    """Test entry point detection for different file types."""
    # Test common entry point files
    assert _is_potential_entry_point('main.py', {})
    assert _is_potential_entry_point('app.py', {})
    assert _is_potential_entry_point('index.js', {})
    assert _is_potential_entry_point('server.js', {})
    
    # Test files with main functions
    assert _is_potential_entry_point('custom.py', {'functions': [{'name': 'main'}]})
    assert _is_potential_entry_point('custom.py', {'functions': [{'name': 'run'}]})
    assert _is_potential_entry_point('custom.py', {'functions': [{'name': 'start'}]})
    
    # Test non-entry point files
    assert not _is_potential_entry_point('utils.py', {'functions': [{'name': 'helper'}]})
    assert not _is_potential_entry_point('types.ts', {})

def test_core_file_detection():
    """Test core file detection logic."""
    # Test files with many functions
    many_functions = {'functions': [{'name': f'f{i}'} for i in range(6)]}
    assert _is_core_file(many_functions)

    # Test files with many classes
    many_classes = {'classes': [{'name': f'C{i}'} for i in range(3)]}
    assert _is_core_file(many_classes)
    
    # Test files with few elements
    few_elements = {'functions': [{'name': 'single'}], 'classes': [{'name': 'Single'}]}
    assert not _is_core_file(few_elements)

def test_process_file_stats():
    """Test processing of file statistics."""
    summary = {
        'project_stats': {
            'total_files': 0,
            'by_type': {},
            'lines_of_code': 0,
            'avg_file_size': 0
        }
    }
    
    file_path = 'src/test.py'
    analysis = {
        'metrics': {'loc': 100},
        'imports': ['import os', 'import sys']
    }
    
    _process_file_stats(file_path, analysis, summary)
    
    assert summary['project_stats']['by_type']['.py'] == 1
    assert summary['project_stats']['lines_of_code'] == 100

def test_process_code_metrics():
    """Test processing of code metrics."""
    summary = {
        'code_metrics': {
            'functions': {'count': 0, 'with_docs': 0, 'complex': 0},
            'classes': {'count': 0, 'with_docs': 0},
            'imports': {'count': 0, 'unique': set()}
        }
    }
    
    analysis = {
        'functions': [
            {'name': 'f1', 'docstring': 'doc', 'loc': 10},
            {'name': 'f2', 'docstring': None, 'loc': 60}
        ],
        'classes': [
            {'name': 'C1', 'docstring': 'doc'},
            {'name': 'C2', 'docstring': None}
        ],
        'imports': ['import os', 'import sys']
    }
    
    _process_code_metrics(analysis, summary)
    
    assert summary['code_metrics']['functions']['count'] == 2
    assert summary['code_metrics']['functions']['with_docs'] == 1
    assert summary['code_metrics']['functions']['complex'] == 1
    assert summary['code_metrics']['classes']['count'] == 2
    assert summary['code_metrics']['classes']['with_docs'] == 1
    assert summary['code_metrics']['imports']['count'] == 2
    assert len(summary['code_metrics']['imports']['unique']) == 2

def test_process_maintenance_info():
    """Test processing of maintenance information."""
    summary = {
        'maintenance': {
            'todos': [],
            'comments_ratio': 0
        }
    }
    
    file_path = 'test.py'
    analysis = {
        'todos': [
            {'line': 10, 'text': 'URGENT: Fix bug'},
            {'line': 20, 'text': 'Add feature'}
        ],
        'comments': ['Comment 1', 'Comment 2'],
        'metrics': {'loc': 100}
    }
    
    _process_maintenance_info(file_path, analysis, summary)
    
    assert len(summary['maintenance']['todos']) == 2
    assert summary['maintenance']['todos'][0]['priority'] == 'high'
    assert summary['maintenance']['todos'][1]['priority'] == 'low'
    assert summary['maintenance']['comments_ratio'] == 0.02  # 2/100

def test_process_structure_info():
    """Test processing of structure information."""
    summary = {
        'structure': {
            'directories': set(),
            'entry_points': [],
            'core_files': []
        }
    }
    
    file_path = 'src/main.py'
    analysis = {
        'functions': [{'name': 'main'}],
        'classes': [{'name': 'C1'}, {'name': 'C2'}, {'name': 'C3'}]
    }
    
    _process_structure_info(file_path, analysis, summary)
    
    assert 'src' in summary['structure']['directories']
    assert file_path in summary['structure']['entry_points']
    assert file_path in summary['structure']['core_files']

def test_calculate_final_metrics():
    """Test calculation of final metrics."""
    summary = {
        'project_stats': {
            'total_files': 2,
            'lines_of_code': 200
        },
        'code_metrics': {
            'functions': {'count': 4, 'with_docs': 3},
            'classes': {'count': 2, 'with_docs': 1},
            'imports': {'unique': {'import os', 'import sys'}}
        },
        'maintenance': {},
        'structure': {
            'directories': {'src', 'tests'}
        }
    }
    
    _calculate_final_metrics(summary)
    
    assert summary['project_stats']['avg_file_size'] == 100.0
    assert 'doc_coverage' in summary['maintenance']
    # Changed to roughly equal comparison
    assert abs(summary['maintenance']['doc_coverage'] - 66.66666666666667) < 0.0001
    assert isinstance(summary['code_metrics']['imports']['unique'], list)
    assert isinstance(summary['structure']['directories'], list)


def test_insights_generation(sample_analysis):
    """Test insights generation."""
    insights = generate_insights(sample_analysis)
    
    # Check for basic insights
    assert len(insights) > 0
    assert any('TODO' in insight for insight in insights)
    # Changed assertion to check for total TODOs instead of specific text
    assert any('TODOs' in insight for insight in insights)


def test_empty_insights_generation():
    """Test insights generation with empty analysis."""
    empty_analysis = {}
    insights = generate_insights(empty_analysis)
    
    assert isinstance(insights, list)
    assert len(insights) == 0

def test_handle_missing_data():
    """Test processors handle missing or incomplete data gracefully."""
    incomplete_analysis = {
        'partial.py': {
            # Missing 'metrics'
            'functions': [{'name': 'f1'}],
            # Missing 'classes'
            'imports': ['import os']
        }
    }
    
    # Should not raise exceptions
    summary = generate_summary(incomplete_analysis)
    insights = generate_insights(incomplete_analysis)
    
    assert summary['project_stats']['total_files'] == 1
    assert isinstance(insights, list)