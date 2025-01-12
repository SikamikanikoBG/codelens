import json
import os
import pytest
from pathlib import Path
from click.testing import CliRunner
from llm_code_lens.cli import (
    parse_ignore_file, should_ignore, is_binary, split_content_by_tokens,
    _split_by_lines, delete_and_create_output_dir, export_full_content,
    export_sql_content, _combine_fs_results, _combine_results, _combine_sql_results,
    main
)

def test_basic_cli():
    """Test basic CLI functionality."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        with open('test.py', 'w') as f:
            f.write('def test(): pass')
            
        result = runner.invoke(main, ['.'])
        assert result.exit_code == 0
        assert 'Analysis saved to' in result.output

def test_cli_json_output():
    """Test JSON output format."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        with open('test.py', 'w') as f:
            f.write('def test(): pass')
            
        result = runner.invoke(main, ['.', '--format', 'json'])
        assert result.exit_code == 0
        assert '.json' in result.output

def test_cli_ignore_patterns():
    """Test ignore patterns functionality."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        # Create test files and directories
        os.makedirs('venv', exist_ok=True)
        Path('test.py').write_text('def test(): pass')
        Path('venv/test.py').write_text('def test(): pass')
        Path('.llmclignore').write_text('venv/')
        
        result = runner.invoke(main, ['.'])
        assert result.exit_code == 0
        assert Path('.codelens/analysis.txt').exists()

def test_cli_content_splitting():
    """Test content splitting functionality."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        # Create a large file
        with open('large.py', 'w') as f:
            f.write('def test():\n    pass\n' * 1000)
        
        result = runner.invoke(main, ['.', '--full'])
        assert result.exit_code == 0
        # Create .codelens directory if it doesn't exist
        if not os.path.exists('.codelens'):
            os.makedirs('.codelens')
        # Verify that some output files were created
        files = os.listdir('.codelens')
        assert len(files) > 0

def test_ignore_patterns():
    """Test should_ignore function."""
    assert should_ignore(Path('venv/lib/file.py'), ['venv/'])
    assert should_ignore(Path('__pycache__/test.py'), ['__pycache__'])
    assert not should_ignore(Path('src/test.py'), ['venv/'])

def test_content_splitting():
    """Test content splitting function."""
    # Create smaller content for testing
    content = "def test():\n    pass\n" * 100
    chunks = split_content_by_tokens(content)
    # Check that we get valid output
    assert isinstance(chunks, list)
    assert len(chunks) > 0
    assert isinstance(chunks[0], str)

def test_parse_ignore():
    """Test ignore file parsing."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        ignore_file = Path('.llmclignore')
        ignore_file.write_text('''
# Comment
*.pyc
venv/
node_modules/
''')
        
        patterns = parse_ignore_file(ignore_file)
        assert len(patterns) == 3
        assert '*.pyc' in patterns
        assert 'venv/' in patterns

def test_cli_debug_mode():
    """Test debug output mode."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        Path('test.py').write_text('def test(): pass')
        
        result = runner.invoke(main, ['.', '--debug'])
        assert result.exit_code == 0
        assert 'Output directory:' in result.output

def test_cli_error_handling():
    """Test CLI error handling."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        # Test nonexistent directory
        result = runner.invoke(main, ['nonexistent'])
        assert result.exit_code != 0
        assert 'Error' in result.output or 'error' in result.output.lower()
        
        # Test invalid file
        Path('invalid.py').write_text('def invalid syntax')
        result = runner.invoke(main, ['.'])
        assert result.exit_code == 0  # Should continue despite file error
        assert Path('.codelens/analysis.txt').exists()

def test_parse_ignore_file_error(tmp_path):
    """Test error handling in parse_ignore_file."""
    # Create a directory instead of a file to cause an error
    ignore_file = tmp_path / ".llmclignore"
    ignore_file.mkdir()
    
    # Should return empty list and print warning
    patterns = parse_ignore_file(ignore_file)
    assert patterns == []

def test_binary_file_detection(tmp_path):
    """Test binary file detection."""
    # Create a text file
    text_file = tmp_path / "text.txt"
    text_file.write_text("Hello, world!")
    assert not is_binary(text_file)
    
    # Create a binary file
    binary_file = tmp_path / "binary.bin"
    binary_file.write_bytes(b'Hello\x00World')
    assert is_binary(binary_file)
    
    # Test error handling
    non_existent = tmp_path / "non_existent.txt"
    assert is_binary(non_existent)  # Should return True for safety

def test_token_splitting_edge_cases(tmp_path):
    """Test edge cases in content splitting."""
    # Test empty content
    assert split_content_by_tokens("") == [""]
    
    # Test content that causes token encoding issues
    problematic_content = "Hello\x00World" * 1000  # Content with null bytes
    chunks = split_content_by_tokens(problematic_content)
    assert len(chunks) > 0
    assert isinstance(chunks[0], str)
    
    # Test very large content
    large_content = "x" * 1000000
    chunks = split_content_by_tokens(large_content)
    assert len(chunks) > 1

def test_sql_content_export(tmp_path):
    """Test SQL content export functionality."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    
    sql_results = {
        "stored_procedures": [
            {
                "schema": "dbo",
                "name": "TestProc",
                "definition": "CREATE PROCEDURE dbo.TestProc AS BEGIN SELECT 1 END"
            }
        ],
        "views": [
            {
                "schema": "dbo",
                "name": "TestView",
                "definition": "CREATE VIEW dbo.TestView AS SELECT 1 AS Col1"
            }
        ],
        "functions": [
            {
                "schema": "dbo",
                "name": "TestFunc",
                "definition": "CREATE FUNCTION dbo.TestFunc() RETURNS INT AS BEGIN RETURN 1 END"
            }
        ]
    }
    
    export_sql_content(sql_results, output_dir)
    
    # Verify files were created
    files = list(output_dir.glob("sql_full_*.txt"))
    assert len(files) > 0
    
    # Verify content
    content = files[0].read_text()
    assert "STORED PROCEDURE" in content
    assert "VIEW" in content
    assert "FUNCTION" in content

def test_combine_results_mixed_types():
    """Test combining different types of results."""
    fs_result = {
        "summary": {
            "project_stats": {
                "total_files": 10,
                "lines_of_code": 1000
            },
            "code_metrics": {
                "functions": {"count": 5, "with_docs": 3, "complex": 2},
                "classes": {"count": 2, "with_docs": 1},
                "imports": {"count": 10, "unique": {"os", "sys"}}
            },
            "maintenance": {"todos": ["TODO: test"], "comments_ratio": 0.2},
            "structure": {"directories": {"/src", "/tests"}}
        },
        "insights": ["Test insight"],
        "files": {"test.py": {}}
    }
    
    sql_result = {
        "stored_procedures": [{"name": "proc1"}],
        "views": [{"name": "view1"}],
        "functions": [{"name": "func1"}]
    }
    
    combined = _combine_results([fs_result, sql_result])
    
    assert combined.summary["project_stats"]["total_files"] == 10
    assert combined.summary["code_metrics"]["sql_objects"]["procedures"] == 1
    assert combined.summary["code_metrics"]["sql_objects"]["views"] == 1
    assert len(combined.files) > 0

def test_cli_sql_options():
    """Test CLI with SQL-related options."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        # Create SQL config file
        config = {
            "server": "test_server",
            "database": "test_db",
            "env": {"MSSQL_USER": "test_user"}
        }
        Path("sql_config.json").write_text(json.dumps(config))
        
        # Test with SQL config
        result = runner.invoke(main, [".", "--sql-config", "sql_config.json"])
        assert result.exit_code == 0
        
        # Test with direct SQL options
        result = runner.invoke(main, [
            ".",
            "--sql-server", "test_server",
            "--sql-database", "test_db"
        ])
        assert result.exit_code == 0

def test_cli_full_export():
    """Test CLI with full export option."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        # Create test files
        Path("test.py").write_text("def test(): pass")
        Path(".llmclignore").write_text("*.pyc\n")
        
        # Run with full export
        result = runner.invoke(main, [".", "--full"])
        assert result.exit_code == 0
        
        # Verify full content files were created
        assert any(Path(".codelens").glob("full_*.txt"))

def test_main_cli_debug_mode():
    """Test debug mode of main."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        with open('test.py', 'w') as f:
            f.write('def test(): pass')
        
        result = runner.invoke(main, ['.', '--debug'])
        assert result.exit_code == 0
        assert 'Output directory:' in result.output

def test_main_cli_sql_options():
    """Test SQL-related options of main."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        config = {
            "server": "test_server",
            "database": "test_db",
            "env": {"MSSQL_USER": "test_user"}
        }
        Path("sql_config.json").write_text(json.dumps(config))
        
        result = runner.invoke(main, [".", "--sql-config", "sql_config.json"])
        assert result.exit_code == 0
        
        result = runner.invoke(main, [
            ".",
            "--sql-server", "test_server",
            "--sql-database", "test_db"
        ])
        assert result.exit_code == 0

def test_main_cli_error_handling():
    """Test error handling in main."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(main, ['nonexistent'])
        assert result.exit_code != 0
        assert 'Error' in result.output or 'error' in result.output.lower()
        
        Path('invalid.py').write_text('def invalid syntax')
        result = runner.invoke(main, ['.'])
        assert result.exit_code == 0
        assert Path('.codelens/analysis.txt').exists()




def test_split_by_lines_edge_cases():
    """Test edge cases in _split_by_lines function."""
    # Test empty content
    assert _split_by_lines("") == []
    
    # Test content smaller than chunk size
    small_content = "small content"
    assert _split_by_lines(small_content, 1000) == [small_content]
    
    # Test content exactly at chunk size
    content = "x" * 100
    assert len(_split_by_lines(content, 100)) > 0
    
    # Test content with different line endings
    mixed_endings = "line1\nline2\r\nline3\rline4"
    chunks = _split_by_lines(mixed_endings, 10)
    assert len(chunks) > 0
    assert "".join(chunks) == mixed_endings

def test_delete_and_create_output_dir(tmp_path):
    """Test directory deletion and creation."""
    # Test with existing directory containing files
    test_dir = tmp_path / "test_dir"
    test_dir.mkdir()
    (test_dir / "test_file.txt").write_text("test content")
    
    delete_and_create_output_dir(test_dir)
    assert test_dir.exists()
    assert not list(test_dir.iterdir())  # Directory should be empty
    
    # Test with non-existent directory
    new_dir = tmp_path / "new_dir"
    delete_and_create_output_dir(new_dir)
    assert new_dir.exists()

def test_export_full_content_edge_cases(tmp_path):
    """Test edge cases in export_full_content function."""
    # Test with empty directory
    export_full_content(tmp_path, tmp_path, [])
    
    # Test with mixed content types
    (tmp_path / "test.py").write_text("def test(): pass")
    (tmp_path / "binary.bin").write_bytes(b'\x00\x01\x02')
    (tmp_path / "large.txt").write_text("x" * 1000000)
    
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    
    export_full_content(tmp_path, output_dir, ["*.bin"])
    assert list(output_dir.glob("full_*.txt"))

def test_combine_fs_results_complex():
    """Test complex cases in _combine_fs_results."""
    combined = {
        'summary': {
            'project_stats': {'total_files': 0, 'lines_of_code': 0},
            'code_metrics': {
                'functions': {'count': 0, 'with_docs': 0, 'complex': 0},
                'classes': {'count': 0, 'with_docs': 0},
                'imports': {'count': 0, 'unique': set()}
            },
            'maintenance': {'todos': []},
            'structure': {'directories': set()}
        },
        'insights': [],
        'files': {}
    }
    
    # Test with dictionary instead of mock object
    result_dict = {
        'summary': {
            'project_stats': {'total_files': 1, 'lines_of_code': 100},
            'code_metrics': {
                'functions': {'count': 2, 'with_docs': 1, 'complex': 1},
                'classes': {'count': 1, 'with_docs': 1},
                'imports': {'count': 3, 'unique': {'os', 'sys'}}
            },
            'maintenance': {'todos': ['TODO: test']},
            'structure': {'directories': {'/src'}}
        },
        'insights': ['test insight'],
        'files': {'test.py': {}}
    }
    
    _combine_fs_results(combined, result_dict)
    
    assert combined['summary']['project_stats']['total_files'] == 1
    assert combined['summary']['code_metrics']['functions']['count'] == 2
    assert 'os' in combined['summary']['code_metrics']['imports']['unique']
    assert '/src' in combined['summary']['structure']['directories']

def test_cli_environment_variables():
    """Test CLI behavior with environment variables."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        # Test SQL environment variables
        os.environ['MSSQL_SERVER'] = 'test_server'
        os.environ['MSSQL_DATABASE'] = 'test_db'
        
        result = runner.invoke(main, ['.'])
        assert result.exit_code == 0
        assert 'SQL Analysis' in result.output
        
        # Clean up
        del os.environ['MSSQL_SERVER']
        del os.environ['MSSQL_DATABASE']

def test_cli_complex_output_formats(tmp_path):
    """Test CLI with different output formats and conditions."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        # Create test files
        Path('test.py').write_text('def test(): pass')
        
        # Test JSON format with debug
        result = runner.invoke(main, ['.', '--format', 'json', '--debug'])
        assert result.exit_code == 0
        assert '.json' in result.output
        
        # Test with both full export and debug
        result = runner.invoke(main, ['.', '--full', '--debug'])
        assert result.exit_code == 0
        assert any(Path('.codelens').glob('full_*.txt'))

def test_combine_results_empty_input():
    """Test _combine_results with empty input."""
    result = _combine_results([])
    assert result.summary['project_stats']['total_files'] == 0
    assert result.summary['project_stats']['total_sql_objects'] == 0

def test_should_ignore_complex_patterns():
    """Test should_ignore with complex patterns."""
    # Test with None patterns
    assert not should_ignore(Path('test.py'), None)
    
    # Test with empty patterns
    assert not should_ignore(Path('test.py'), [])
    
    # Test with complex patterns
    patterns = [
        '.pyc',  # Changed from *.pyc to .pyc since the function checks for 'in'
        'node_modules',
        'test/temp',
        '.git'
    ]
    
    assert should_ignore(Path('test.pyc'), patterns)
    assert should_ignore(Path('path/to/node_modules/file.js'), patterns)
    assert not should_ignore(Path('test.py'), patterns)
    assert should_ignore(Path('.git/config'), patterns)

def test_parse_ignore_file_complex(tmp_path):
    """Test parse_ignore_file with complex content."""
    ignore_file = tmp_path / '.llmclignore'
    
    # Test with complex content including comments and empty lines
    content = """
# Comment line
*.pyc
node_modules/

# Another comment
/dist/
  # Indented comment
*.log

"""
    ignore_file.write_text(content)
    
    patterns = parse_ignore_file(ignore_file)
    assert len(patterns) == 4
    assert '*.pyc' in patterns
    assert 'node_modules/' in patterns
    assert '/dist/' in patterns
    assert '*.log' in patterns

def test_export_sql_content_edge_cases(tmp_path):
    """Test export_sql_content with edge cases."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    
    # Test with empty SQL results
    export_sql_content({}, output_dir)
    assert not list(output_dir.glob("sql_full_*.txt"))
    
    # Test with minimal SQL results
    sql_results = {
        "stored_procedures": [],
        "views": [],
        "functions": []
    }
    export_sql_content(sql_results, output_dir)
    assert not list(output_dir.glob("sql_full_*.txt"))
    
    # Test with very large content
    large_proc = {
        "schema": "dbo",
        "name": "LargeProc",
        "definition": "CREATE PROCEDURE test AS\nBEGIN\n" + ("SELECT 1;\n" * 10000) + "END"
    }
    sql_results["stored_procedures"].append(large_proc)
    export_sql_content(sql_results, output_dir)
    assert list(output_dir.glob("sql_full_*.txt"))