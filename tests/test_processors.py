"""test_processors.py - Tests for analysis processors"""
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

class TestProcessors:
    @pytest.fixture
    def sample_analysis(self):
        """Create a sample file analysis for testing."""
        return {
            'main.py': {
                'type': 'python',
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
                'metrics': {'loc': 100, 'complexity': 5}
            },
            'utils.py': {
                'type': 'python',
                'functions': [
                    {'name': 'utility', 'args': ['a', 'b'], 'docstring': 'Utility function', 'loc': 25},
                    {'name': 'helper2', 'args': ['x'], 'docstring': None, 'loc': 55}
                ],
                'classes': [],
                'imports': ['import json'],
                'todos': [
                    {'line': 5, 'text': 'Improve performance'}
                ],
                'metrics': {'loc': 50, 'complexity': 3}
            }
        }

    def test_generate_summary_complete(self, sample_analysis):
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
        assert any(todo['priority'] == 'high' 
                  for todo in summary['maintenance']['todos'])

    def test_todo_priority_estimation(self):
        """Test TODO priority estimation."""
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

    def test_entry_point_detection(self):
        """Test entry point detection."""
        # Test common entry point files
        assert _is_potential_entry_point('main.py', {})
        assert _is_potential_entry_point('app.py', {})
        assert _is_potential_entry_point('cli.py', {})
        assert _is_potential_entry_point('server.py', {})
        
        # Test files with main functions
        assert _is_potential_entry_point('custom.py', 
                                       {'functions': [{'name': 'main'}]})
        assert _is_potential_entry_point('custom.py', 
                                       {'functions': [{'name': 'run'}]})
        
        # Test non-entry point files
        assert not _is_potential_entry_point('utils.py', 
                                           {'functions': [{'name': 'helper'}]})
        assert not _is_potential_entry_point('types.py', {})

    def test_core_file_detection(self):
        """Test core file detection."""
        # Test files with many functions
        many_functions = {
            'functions': [{'name': f'f{i}'} for i in range(6)]
        }
        assert _is_core_file(many_functions)
        
        # Test files with many classes
        many_classes = {
            'classes': [{'name': f'C{i}'} for i in range(3)]
        }
        assert _is_core_file(many_classes)
        
        # Test complex files
        complex_file = {
            'functions': [{'name': 'f1', 'complexity': 15}],
            'metrics': {'complexity': 20}
        }
        assert _is_core_file(complex_file)
        
        # Test simple files
        simple_file = {
            'functions': [{'name': 'simple'}],
            'classes': [{'name': 'Simple'}],
            'metrics': {'complexity': 2}
        }
        assert not _is_core_file(simple_file)

    def test_process_file_stats(self):
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

    def test_process_code_metrics(self):
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
                {'name': 'f1', 'docstring': 'doc', 'complexity': 2},
                {'name': 'f2', 'docstring': None, 'complexity': 8}
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

    def test_process_maintenance_info(self):
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

    def test_process_structure_info(self):
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

    def test_calculate_final_metrics(self):
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
        assert abs(summary['maintenance']['doc_coverage'] - 66.67) < 0.01
        assert isinstance(summary['code_metrics']['imports']['unique'], list)
        assert isinstance(summary['structure']['directories'], list)

    def test_insights_generation(self, sample_analysis):
        """Test insights generation."""
        insights = generate_insights(sample_analysis)
        
        # Check basic insights presence
        assert len(insights) > 0
        assert any('TODO' in insight for insight in insights)
        assert any('memory leak' in insight.lower() for insight in insights)
        
        # Check code complexity insights
        assert any('complex' in insight.lower() for insight in insights)
        assert any('helper2' in insight for insight in insights)
        
        # Check architectural insights
        assert any('entry point' in insight.lower() for insight in insights)
        assert any('main.py' in insight for insight in insights)

    def test_insights_edge_cases(self):
        """Test insights generation for edge cases."""
        # Empty project
        empty_insights = generate_insights({})
        assert isinstance(empty_insights, list)
        assert len(empty_insights) == 0
        
        # Single file project
        single_file = {
            'test.py': {
                'functions': [{'name': 'test'}],
                'metrics': {'loc': 10, 'complexity': 1}
            }
        }
        single_insights = generate_insights(single_file)
        assert len(single_insights) > 0
        assert any('1 analyzable file' in insight for insight in single_insights)
        
        # Project with only TODOs
        todos_only = {
            'file.py': {
                'todos': [
                    {'text': 'TODO 1'},
                    {'text': 'TODO 2'}
                ],
                'metrics': {'loc': 5}
            }
        }
        todo_insights = generate_insights(todos_only)
        assert any('TODO' in insight for insight in todo_insights)

    def test_process_sql_analysis(self):
        """Test processing SQL-specific analysis."""
        sql_analysis = {
            'stored_procedures': [
                {
                    'name': 'sp_test',
                    'schema': 'dbo',
                    'definition': 'CREATE PROCEDURE...',
                    'metrics': {'lines': 50, 'complexity': 8},
                    'parameters': [{'name': 'param1', 'type': 'int'}],
                    'dependencies': ['table1', 'table2']
                }
            ],
            'views': [
                {
                    'name': 'vw_test',
                    'schema': 'dbo',
                    'definition': 'CREATE VIEW...',
                    'metrics': {'lines': 20, 'complexity': 3},
                    'dependencies': ['table1']
                }
            ]
        }
        
        summary = generate_summary({'sql_analysis': sql_analysis})
        
        # Check SQL metrics
        assert 'sql_objects' in summary['code_metrics']
        assert summary['code_metrics']['sql_objects']['procedures'] == 1
        assert summary['code_metrics']['sql_objects']['views'] == 1
        
        # Check complexity metrics
        total_complexity = (
            sql_analysis['stored_procedures'][0]['metrics']['complexity'] +
            sql_analysis['views'][0]['metrics']['complexity']
        )
        assert summary['project_stats']['complexity'] >= total_complexity
        
        # Check dependencies
        assert 'table1' in summary['structure']['sql_dependencies']
        assert 'table2' in summary['structure']['sql_dependencies']

    def test_process_dependencies(self):
        """Test dependency processing."""
        analysis = {
            'file1.py': {
                'imports': ['from module1 import func1', 'import module2'],
                'metrics': {'loc': 10}
            },
            'file2.py': {
                'imports': ['import module1', 'from module2 import func2'],
                'metrics': {'loc': 20}
            }
        }
        
        summary = generate_summary(analysis)
        
        # Check import counts
        assert summary['code_metrics']['imports']['count'] == 4
        unique_imports = summary['code_metrics']['imports']['unique']
        assert len(unique_imports) == 3  # module1 appears twice
        assert 'module1' in str(unique_imports)
        assert 'module2' in str(unique_imports)

    def test_handle_missing_data(self):
        """Test handling of missing or incomplete data."""
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

if __name__ == '__main__':
    pytest.main(['-v'])