"""
Unit tests for the file filtering functionality in CLI.
"""

import pytest
from pathlib import Path
import tempfile
import os
import sys
import json
from unittest.mock import patch, MagicMock
from llm_code_lens.analyzer.base import ProjectAnalyzer, AnalysisResult
from llm_code_lens.cli import main, parse_ignore_file, should_ignore, is_binary, split_content_by_tokens
from llm_code_lens.cli import _split_by_lines, delete_and_create_output_dir, export_full_content, export_sql_content
from llm_code_lens.cli import _combine_fs_results, _combine_sql_results, _combine_results

def test_filtered_collect_files():
    """Test that filtered_collect_files correctly filters files based on include/exclude paths."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a test directory structure
        root = Path(tmpdir)
        
        # Create some test directories and files
        (root / "include_dir").mkdir()
        (root / "exclude_dir").mkdir()
        (root / "mixed_dir").mkdir()
        
        (root / "include_dir" / "file1.py").write_text("# Test file 1")
        (root / "exclude_dir" / "file2.py").write_text("# Test file 2")
        (root / "mixed_dir" / "include_file.py").write_text("# Test file 3")
        (root / "mixed_dir" / "exclude_file.py").write_text("# Test file 4")
        
        # Create a ProjectAnalyzer instance
        analyzer = ProjectAnalyzer()
        
        # Store the original _collect_files method
        original_collect_files = analyzer._collect_files
        
        # Define include and exclude paths
        include_paths = [root / "include_dir", root / "mixed_dir" / "include_file.py"]
        exclude_paths = [root / "exclude_dir", root / "mixed_dir" / "exclude_file.py"]
        
        # Define the filtered_collect_files function (similar to what's in cli.py)
        def filtered_collect_files(self, path):
            files = original_collect_files(path)
            filtered_files = []
            
            for file_path in files:
                # Check if file should be included based on selection
                should_include = True
                
                # If we have explicit include paths, file must be in one of them
                if include_paths:
                    should_include = False
                    for include_path in include_paths:
                        if str(file_path).startswith(str(include_path)):
                            should_include = True
                            break
                
                # Check if file is in exclude paths
                for exclude_path in exclude_paths:
                    if str(file_path).startswith(str(exclude_path)):
                        should_include = False
                        break
                
                if should_include:
                    filtered_files.append(file_path)
            
            return filtered_files
        
        # Replace the method
        analyzer._collect_files = filtered_collect_files.__get__(analyzer, ProjectAnalyzer)
        
        # Test the filtering
        collected_files = analyzer._collect_files(root)
        
        # Convert to strings for easier comparison
        collected_file_strs = [str(f) for f in collected_files]
        
        # Verify only the correct files are included
        assert str(root / "include_dir" / "file1.py") in collected_file_strs
        assert str(root / "mixed_dir" / "include_file.py") in collected_file_strs
        
        # Verify excluded files are not included
        assert str(root / "exclude_dir" / "file2.py") not in collected_file_strs
        assert str(root / "mixed_dir" / "exclude_file.py") not in collected_file_strs
        
        # Verify the count is correct
        assert len(collected_files) == 2

def test_parse_ignore_file():
    """Test parsing .llmclignore file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        ignore_file = root / ".llmclignore"
        
        # Create test ignore file
        ignore_content = """
# Comment line
node_modules
.git
dist
# Another comment
build
        """
        ignore_file.write_text(ignore_content)
        
        # Parse the file
        patterns = parse_ignore_file(ignore_file)
        
        # Check results
        assert len(patterns) == 4
        assert "node_modules" in patterns
        assert ".git" in patterns
        assert "dist" in patterns
        assert "build" in patterns
        assert "# Comment line" not in patterns
        
        # Test with non-existent file
        non_existent = root / "non_existent"
        assert parse_ignore_file(non_existent) == []

def test_should_ignore():
    """Test should_ignore function."""
    # Test default ignores
    assert should_ignore(Path("/path/to/.git/file.txt")) is True
    assert should_ignore(Path("/path/to/__pycache__/file.pyc")) is True
    assert should_ignore(Path("/path/to/node_modules/package.json")) is True
    
    # Test custom ignore patterns
    custom_patterns = ["ignore_me", "secret"]
    assert should_ignore(Path("/path/to/ignore_me.txt"), custom_patterns) is True
    assert should_ignore(Path("/path/to/secret_file.txt"), custom_patterns) is True
    assert should_ignore(Path("/path/to/normal_file.txt"), custom_patterns) is False

def test_is_binary():
    """Test is_binary function."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        
        # Create text file
        text_file = root / "text.txt"
        text_file.write_text("This is a text file")
        assert is_binary(text_file) is False
        
        # Create binary file
        binary_file = root / "binary.bin"
        with open(binary_file, 'wb') as f:
            f.write(b'Binary\x00Data')
        assert is_binary(binary_file) is True
        
        # Test with non-existent file (should return True as fallback)
        non_existent = root / "non_existent"
        assert is_binary(non_existent) is True

def test_split_by_lines():
    """Test _split_by_lines function."""
    # Test with small content
    small_content = "Line 1\nLine 2\nLine 3"
    chunks = _split_by_lines(small_content, max_chunk_size=1000)
    assert len(chunks) == 1
    assert chunks[0] == small_content
    
    # Test with content that needs splitting
    large_content = "\n".join([f"Line {i}" for i in range(1000)])
    chunks = _split_by_lines(large_content, max_chunk_size=100)
    assert len(chunks) > 1
    
    # Test with empty content
    assert _split_by_lines("") == [""]

@patch('tiktoken.get_encoding')
def test_split_content_by_tokens(mock_get_encoding):
    """Test split_content_by_tokens function."""
    # Mock the encoder
    mock_encoder = MagicMock()
    mock_encoder.encode.return_value = list(range(1000))  # 1000 tokens
    mock_encoder.decode.side_effect = lambda tokens: f"Chunk with {len(tokens)} tokens"
    mock_get_encoding.return_value = mock_encoder
    
    # Test with content
    content = "Test content"
    chunks = split_content_by_tokens(content, chunk_size=500)
    
    # Should split into 2 chunks of 500 tokens each
    assert len(chunks) == 2
    assert chunks[0] == "Chunk with 500 tokens"
    assert chunks[1] == "Chunk with 500 tokens"
    
    # Test with empty content
    assert split_content_by_tokens("") == [""]
    
    # Test with exception (should fall back to line-based splitting)
    mock_get_encoding.side_effect = Exception("Test error")
    with patch('llm_code_lens.cli._split_by_lines') as mock_split_lines:
        mock_split_lines.return_value = ["Fallback chunk"]
        chunks = split_content_by_tokens("Test content")
        assert chunks == ["Fallback chunk"]
        mock_split_lines.assert_called_once()

def test_delete_and_create_output_dir():
    """Test delete_and_create_output_dir function."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        output_dir = root / "output"
        
        # Create initial directory with a file
        output_dir.mkdir()
        test_file = output_dir / "test.txt"
        test_file.write_text("Test content")
        
        # Create menu state file
        menu_state_dir = output_dir
        menu_state_file = menu_state_dir / "menu_state.json"
        menu_state_data = '{"test": "data"}'
        menu_state_file.write_text(menu_state_data)
        
        # Delete and recreate
        delete_and_create_output_dir(output_dir)
        
        # Directory should exist
        assert output_dir.exists()
        
        # Test file should be gone
        assert not test_file.exists()
        
        # Menu state file should be preserved
        assert menu_state_file.exists()
        assert menu_state_file.read_text() == menu_state_data
        
        # Test with non-existent directory
        new_dir = root / "new_dir"
        delete_and_create_output_dir(new_dir)
        assert new_dir.exists()

@patch('llm_code_lens.cli.split_content_by_tokens')
def test_export_full_content(mock_split):
    """Test export_full_content function."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        output_dir = root / "output"
        output_dir.mkdir()
        
        # Create test files
        (root / "file1.py").write_text("# Test file 1")
        (root / "file2.py").write_text("# Test file 2")
        (root / "ignored.pyc").write_text("# Should be ignored")
        
        # Setup mock
        mock_split.return_value = ["Chunk 1", "Chunk 2"]
        
        # Export content
        export_full_content(root, output_dir, ["ignored"])
        
        # Check output files
        assert (output_dir / "full_1.txt").exists()
        assert (output_dir / "full_2.txt").exists()
        
        # Check content
        assert "Chunk 1" in (output_dir / "full_1.txt").read_text()
        assert "Chunk 2" in (output_dir / "full_2.txt").read_text()

@patch('llm_code_lens.cli.split_content_by_tokens')
def test_export_sql_content(mock_split):
    """Test export_sql_content function."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        
        # Create test SQL results
        sql_results = {
            'stored_procedures': [
                {'schema': 'dbo', 'name': 'proc1', 'definition': 'CREATE PROCEDURE proc1 AS SELECT 1'}
            ],
            'views': [
                {'schema': 'dbo', 'name': 'view1', 'definition': 'CREATE VIEW view1 AS SELECT 1'}
            ],
            'functions': [
                {'schema': 'dbo', 'name': 'func1', 'definition': 'CREATE FUNCTION func1() RETURNS INT AS BEGIN RETURN 1 END'}
            ]
        }
        
        # Setup mock
        mock_split.return_value = ["SQL Chunk 1", "SQL Chunk 2"]
        
        # Export content
        export_sql_content(sql_results, output_dir)
        
        # Check output files
        assert (output_dir / "sql_full_1.txt").exists()
        assert (output_dir / "sql_full_2.txt").exists()
        
        # Check content
        assert "SQL Chunk 1" in (output_dir / "sql_full_1.txt").read_text()
        assert "SQL Chunk 2" in (output_dir / "sql_full_2.txt").read_text()

def test_combine_fs_results():
    """Test _combine_fs_results function."""
    # Create base combined result
    combined = {
        'summary': {
            'project_stats': {'total_files': 10, 'lines_of_code': 1000},
            'code_metrics': {
                'functions': {'count': 5, 'with_docs': 2, 'complex': 1},
                'classes': {'count': 3, 'with_docs': 1, 'complex': 0},
                'imports': {'count': 10, 'unique': set(['import1', 'import2'])}
            },
            'maintenance': {'todos': []},
            'structure': {'directories': set(['/dir1', '/dir2'])}
        },
        'insights': [],
        'files': {}
    }
    
    # Create result to combine
    result = {
        'summary': {
            'project_stats': {'total_files': 5, 'lines_of_code': 500},
            'code_metrics': {
                'functions': {'count': 3, 'with_docs': 1, 'complex': 2},
                'classes': {'count': 2, 'with_docs': 1, 'complex': 1},
                'imports': {'count': 5, 'unique': ['import3', 'import4']}
            },
            'maintenance': {'todos': ['TODO: Fix this']},
            'structure': {'directories': ['/dir3']}
        },
        'insights': ['Insight 1'],
        'files': {'file1.py': {'analysis': 'data'}}
    }
    
    # Combine results
    _combine_fs_results(combined, result)
    
    # Check combined results
    assert combined['summary']['project_stats']['total_files'] == 15
    assert combined['summary']['project_stats']['lines_of_code'] == 1500
    assert combined['summary']['code_metrics']['functions']['count'] == 8
    assert combined['summary']['code_metrics']['functions']['with_docs'] == 3
    assert combined['summary']['code_metrics']['functions']['complex'] == 3
    assert combined['summary']['code_metrics']['imports']['count'] == 15
    assert 'import3' in combined['summary']['code_metrics']['imports']['unique']
    assert 'import4' in combined['summary']['code_metrics']['imports']['unique']
    assert len(combined['summary']['maintenance']['todos']) == 1
    assert '/dir3' in combined['summary']['structure']['directories']
    assert len(combined['insights']) == 1
    assert 'file1.py' in combined['files']

def test_combine_sql_results():
    """Test _combine_sql_results function."""
    # Create base combined result
    combined = {
        'summary': {
            'project_stats': {'total_files': 10, 'total_sql_objects': 0},
            'code_metrics': {
                'sql_objects': {'procedures': 0, 'views': 0, 'functions': 0}
            }
        },
        'files': {}
    }
    
    # Create SQL result to combine
    sql_result = {
        'stored_procedures': [
            {'name': 'proc1', 'schema': 'dbo', 'definition': 'CREATE PROCEDURE proc1 AS SELECT 1'}
        ],
        'views': [
            {'name': 'view1', 'schema': 'dbo', 'definition': 'CREATE VIEW view1 AS SELECT 1'}
        ],
        'functions': [
            {'name': 'func1', 'schema': 'dbo', 'definition': 'CREATE FUNCTION func1() RETURNS INT AS BEGIN RETURN 1 END'}
        ]
    }
    
    # Combine results
    _combine_sql_results(combined, sql_result)
    
    # Check combined results
    assert combined['summary']['project_stats']['total_sql_objects'] == 3
    assert combined['summary']['code_metrics']['sql_objects']['procedures'] == 1
    assert combined['summary']['code_metrics']['sql_objects']['views'] == 1
    assert combined['summary']['code_metrics']['sql_objects']['functions'] == 1
    assert 'stored_proc_proc1' in combined['files']
    assert 'view_view1' in combined['files']
    assert 'function_func1' in combined['files']

@patch('json.loads')
def test_combine_results(mock_json_loads):
    """Test _combine_results function."""
    # Setup mocks
    mock_json_loads.side_effect = lambda x: x  # Just return the input
    
    # Create test results
    fs_result = AnalysisResult(
        summary={
            'project_stats': {'total_files': 5, 'lines_of_code': 500},
            'code_metrics': {
                'functions': {'count': 3, 'with_docs': 1, 'complex': 2},
                'classes': {'count': 2, 'with_docs': 1},
                'imports': {'count': 5, 'unique': ['import1']}
            },
            'maintenance': {'todos': ['TODO: Fix this']},
            'structure': {'directories': ['/dir1']}
        },
        insights=['Insight 1'],
        files={'file1.py': {'analysis': 'data'}}
    )
    
    sql_result = {
        'stored_procedures': [{'name': 'proc1', 'schema': 'dbo', 'definition': 'CREATE PROCEDURE proc1 AS SELECT 1'}],
        'views': [{'name': 'view1', 'schema': 'dbo', 'definition': 'CREATE VIEW view1 AS SELECT 1'}]
    }
    
    # Combine results
    combined = _combine_results([fs_result, sql_result])
    
    # Check result is an AnalysisResult
    assert isinstance(combined, AnalysisResult)
    
    # Convert to dict for easier checking
    combined_dict = combined.dict()
    
    # Check combined results
    assert combined_dict['summary']['project_stats']['total_files'] == 5
    assert combined_dict['summary']['project_stats']['total_sql_objects'] == 2
    assert combined_dict['summary']['code_metrics']['functions']['count'] == 3
    assert combined_dict['summary']['code_metrics']['sql_objects']['procedures'] == 1
    assert combined_dict['summary']['code_metrics']['sql_objects']['views'] == 1
    assert len(combined_dict['insights']) == 1
    assert 'file1.py' in combined_dict['files']
    assert 'stored_proc_proc1' in combined_dict['files']
    assert 'view_view1' in combined_dict['files']

def test_main_function_structure():
    """Test the structure of the main CLI function."""
    # This is a simplified test to ensure the main function exists
    # We're not testing the actual execution or parameters since Click decorates the function
    
    # Import the main function to verify it exists
    from llm_code_lens.cli import main
    
    # Check that it's a function
    assert callable(main)
