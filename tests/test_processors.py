import pytest
from llm_code_lens.processors.insights import generate_insights
from llm_code_lens.processors.summary import (
    generate_summary, _process_file_stats, _process_code_metrics,
    _process_maintenance_info, _process_structure_info,
    _calculate_final_metrics, _estimate_todo_priority,
    _is_potential_entry_point, _is_core_file
)

def test_generate_summary():
    """Test basic summary generation."""
    analysis = {
        'main.py': {
            'metrics': {
                'loc': 100,
                'complexity': 5
            },
            'functions': [
                {'name': 'main', 'docstring': 'Test', 'complexity': 2},
                {'name': 'helper', 'docstring': None, 'complexity': 3}
            ],
            'classes': [
                {'name': 'TestClass', 'docstring': 'Test class'}
            ],
            'imports': ['import os', 'from pathlib import Path'],
            'todos': [
                {'text': 'FIXME: Important', 'line': 10}
            ]
        }
    }
    
    summary = generate_summary(analysis)
    
    # Check basic structure
    assert 'project_stats' in summary
    assert 'code_metrics' in summary
    assert 'maintenance' in summary
    assert 'structure' in summary
    
    # Check metrics
    assert summary['project_stats']['total_files'] == 1
    assert summary['project_stats']['lines_of_code'] == 100
    assert summary['code_metrics']['functions']['count'] == 2
    assert summary['code_metrics']['functions']['with_docs'] == 1
    assert summary['code_metrics']['classes']['count'] == 1

def test_generate_insights():
    """Test basic insights generation."""
    analysis = {
        'main.py': {
            'todos': [
                {'text': 'FIXME: Critical bug', 'line': 10},
                {'text': 'TODO: Add tests', 'line': 20}
            ],
            'functions': [
                {'name': 'main', 'docstring': None, 'complexity': 10}
            ]
        }
    }
    
    insights = generate_insights(analysis)
    assert isinstance(insights, list)
    assert len(insights) > 0
    assert any('TODO' in insight for insight in insights)


def test_process_file_stats_empty():
    """Test file stats processing with empty analysis."""
    summary = {
        'project_stats': {
            'by_type': {},
            'lines_of_code': 0
        }
    }
    _process_file_stats('test.py', {}, summary)
    assert '.py' in summary['project_stats']['by_type']
    assert summary['project_stats']['by_type']['.py'] == 1

def test_process_code_metrics_edge_cases():
    """Test code metrics processing with edge cases."""
    summary = {
        'code_metrics': {
            'functions': {'count': 0, 'with_docs': 0, 'complex': 0},
            'classes': {'count': 0, 'with_docs': 0},
            'imports': {'count': 0, 'unique': set()}
        }
    }
    
    # Test with empty analysis
    _process_code_metrics({}, summary)
    assert summary['code_metrics']['functions']['count'] == 0
    
    # Test with None values in function data - should be treated as 0
    analysis = {
        'functions': [
            {'name': 'test', 'complexity': None, 'loc': None},
            {'name': 'test2', 'complexity': 6, 'loc': 51}
        ]
    }
    _process_code_metrics(analysis, summary)
    assert summary['code_metrics']['functions']['count'] == 2
    assert summary['code_metrics']['functions']['complex'] == 1 

def test_process_maintenance_info_edge_cases():
    """Test maintenance info processing with edge cases."""
    summary = {
        'maintenance': {
            'todos': [],
            'comments_ratio': 0
        }
    }
    
    # Test with empty analysis
    _process_maintenance_info('test.py', {}, summary)
    assert len(summary['maintenance']['todos']) == 0
    
    # Test with zero lines of code
    analysis = {
        'todos': [{'text': 'TODO: test', 'line': 1}],
        'comments': ['# comment'],
        'metrics': {'loc': 0}
    }
    _process_maintenance_info('test.py', analysis, summary)
    assert len(summary['maintenance']['todos']) == 1
    assert summary['maintenance']['comments_ratio'] == 0

def test_process_structure_info_comprehensive():
    """Test structure info processing with various cases."""
    summary = {
        'structure': {
            'directories': set(),
            'entry_points': [],
            'core_files': []
        }
    }
    
    # Test entry point detection - main.py
    _process_structure_info('main.py', {'functions': []}, summary)
    assert 'main.py' in summary['structure']['entry_points']
    
    # Test entry point detection - function names
    analysis = {
        'functions': [{'name': 'run'}, {'name': 'helper'}]
    }
    _process_structure_info('app.py', analysis, summary)
    assert 'app.py' in summary['structure']['entry_points']

def test_calculate_final_metrics_edge_cases():
    """Test final metrics calculation with edge cases."""
    # Test with zero files
    summary = {
        'project_stats': {
            'total_files': 0,
            'lines_of_code': 0,
            'avg_file_size': 0
        },
        'code_metrics': {
            'functions': {'count': 0, 'with_docs': 0},
            'classes': {'count': 0, 'with_docs': 0},
            'imports': {'unique': set()}
        },
        'maintenance': {'doc_coverage': 0},
        'structure': {'directories': set()}
    }
    _calculate_final_metrics(summary)
    assert summary['project_stats']['avg_file_size'] == 0
    assert summary['maintenance']['doc_coverage'] == 0

def test_estimate_todo_priority_variations():
    """Test TODO priority estimation with different text variations."""
    assert _estimate_todo_priority('URGENT: Fix memory leak') == 'high'
    assert _estimate_todo_priority('CRITICAL: Security issue') == 'high'
    assert _estimate_todo_priority('FIXME: Performance issue') == 'high'
    assert _estimate_todo_priority('Important: Add validation') == 'medium'
    assert _estimate_todo_priority('Should improve this later') == 'medium'
    assert _estimate_todo_priority('Add more tests') == 'low'

def test_is_potential_entry_point_variations():
    """Test entry point detection with different variations."""
    # Test common entry point filenames
    assert _is_potential_entry_point('index.js', {})
    assert _is_potential_entry_point('server.js', {})
    assert _is_potential_entry_point('cli.py', {})
    
    # Test main-like function variations
    analysis = {'functions': [{'name': 'execute'}]}
    assert _is_potential_entry_point('random.py', analysis)
    
    analysis = {'functions': [{'name': 'start'}]}
    assert _is_potential_entry_point('app.py', analysis)

def test_is_core_file_variations():
    """Test core file detection with different criteria."""
    # Test function count threshold
    analysis = {'functions': [{'name': f'func{i}'} for i in range(6)]}
    assert _is_core_file(analysis)
    
    # Test class count threshold
    analysis = {'classes': [{'name': f'Class{i}'} for i in range(3)]}
    assert _is_core_file(analysis)
    
    # Test complex functions
    analysis = {
        'functions': [
            {'name': 'complex_func', 'complexity': 6, 'loc': 45, 'args': ['a', 'b', 'c', 'd']},
        ]
    }
    assert _is_core_file(analysis)
    
    # Test file complexity
    analysis = {'metrics': {'complexity': 21}}
    assert _is_core_file(analysis)
    
    # Test non-core file
    analysis = {
        'functions': [{'name': 'simple', 'complexity': 2, 'loc': 10, 'args': ['a']}],
        'classes': [{'name': 'Simple'}],
        'metrics': {'complexity': 5}
    }
    assert not _is_core_file(analysis)

def test_generate_summary_comprehensive():
    """Test summary generation with comprehensive analysis data."""
    analysis = {
        'main.py': {
            'metrics': {'loc': 100, 'complexity': 10},
            'functions': [
                {'name': 'main', 'docstring': 'Main function', 'complexity': 5, 'loc': 30},
                {'name': 'helper', 'docstring': None, 'complexity': 2, 'loc': 20}
            ],
            'classes': [
                {'name': 'MainClass', 'docstring': 'Main class'},
                {'name': 'HelperClass', 'docstring': None}
            ],
            'imports': ['os', 'sys', 'typing'],
            'todos': [
                {'text': 'FIXME: Critical issue', 'line': 10},
                {'text': 'TODO: Add more tests', 'line': 20}
            ]
        },
        'utils.py': {
            'metrics': {'loc': 50, 'complexity': 5},
            'functions': [
                {'name': 'util_func', 'docstring': 'Utility', 'complexity': 6, 'loc': 51}
            ],
            'classes': [],
            'imports': ['os', 'pathlib'],
            'todos': []
        }
    }
    
    summary = generate_summary(analysis)
    
    # Check project stats
    assert summary['project_stats']['total_files'] == 2
    assert summary['project_stats']['lines_of_code'] == 150
    assert summary['project_stats']['avg_file_size'] == 75
    
    # Check code metrics
    assert summary['code_metrics']['functions']['count'] == 3
    assert summary['code_metrics']['functions']['with_docs'] == 2
    assert summary['code_metrics']['functions']['complex'] == 1  # Only util_func is complex
    assert summary['code_metrics']['classes']['count'] == 2
    assert summary['code_metrics']['classes']['with_docs'] == 1
    assert len(summary['code_metrics']['imports']['unique']) == 4
    
    # Check maintenance info
    assert len(summary['maintenance']['todos']) == 2
    assert summary['maintenance']['doc_coverage'] == 60  # 3 out of 5 elements documented
    
    # Check structure info
    assert len(summary['structure']['directories']) == 1
    assert 'main.py' in summary['structure']['entry_points']
    assert len(summary['structure']['core_files']) > 0
