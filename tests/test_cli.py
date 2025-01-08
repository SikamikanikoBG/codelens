import pytest
from click.testing import CliRunner
from pathlib import Path
import json
import time
from llm_code_lens.cli import main, split_content_by_tokens, count_tokens, should_ignore

@pytest.fixture
def runner():
    """Create a CLI runner."""
    return CliRunner(mix_stderr=False)  # Separate stdout and stderr

@pytest.fixture
def sample_project(tmp_path):
    """Create a sample project for CLI testing."""
    with runner().isolated_filesystem() as fs:
        # Create directory structure
        src_dir = tmp_path / "src"
        src_dir.mkdir(exist_ok=True)

        # Create Python file
        test_file = src_dir / "test.py"
        test_file.write_text('''
def test():
    """Test function"""
    return True
''')
        yield tmp_path

def test_basic_analysis(runner, tmp_path):
    """Test basic project analysis."""
    with runner.isolated_filesystem():
        # Create Python file
        src_dir = Path("src")
        src_dir.mkdir(exist_ok=True)
        test_file = src_dir / "test.py"
        test_file.write_text('''
def test():
    """Test function"""
    return True
''')
        
        # Run analysis
        result = runner.invoke(main, ['.'])
        assert result.exit_code == 0

        # Check output directory and file
        output_dir = Path('.codelens')
        assert output_dir.exists()
        analysis_file = output_dir / 'analysis.txt'
        assert analysis_file.exists()
        
        # Verify content
        content = analysis_file.read_text()
        assert 'CODEBASE SUMMARY:' in content
        assert 'test.py' in content
        assert 'Test function' in content

def test_json_output(runner):
    """Test JSON output format."""
    with runner.isolated_filesystem():
        # Create Python file
        src_dir = Path("src")
        src_dir.mkdir(exist_ok=True)
        test_file = src_dir / "test.py"
        test_file.write_text('''
def test():
    return True
''')

        # Run analysis
        result = runner.invoke(main, ['.', '--format', 'json'])
        assert result.exit_code == 0

        # Check output file
        analysis_file = Path('.codelens') / 'analysis.json'
        assert analysis_file.exists()
        
        # Verify JSON content
        content = json.loads(analysis_file.read_text())
        assert 'summary' in content
        assert 'files' in content

def test_empty_directory(runner):
    """Test analysis of empty directory."""
    with runner.isolated_filesystem():
        result = runner.invoke(main, ['.'])
        assert result.exit_code == 0
        
        # Check output directory
        output_dir = Path('.codelens')
        assert output_dir.exists()

def test_large_file_handling(runner):
    """Test handling of large files."""
    with runner.isolated_filesystem():
        # Create a large file
        Path("src").mkdir(exist_ok=True)
        large_file = Path("src/large.py")
        large_content = '\n'.join([f"def function_{i}(): pass" for i in range(1000)])
        large_file.write_text(large_content)

        # Run analysis with full export
        result = runner.invoke(main, ['.', '--full'])
        assert result.exit_code == 0

        # Check output files
        output_dir = Path('.codelens')
        assert output_dir.exists()

        # Check for the main analysis file
        analysis_file = output_dir / 'analysis.txt'
        assert analysis_file.exists()

        # Check for full content files
        full_files = list(output_dir.glob('full_*.txt'))
        assert len(full_files) > 0

        # Verify content
        full_content = full_files[0].read_text()
        assert 'function_0' in full_content
        assert 'function_999' in full_content

def test_unicode_handling(runner):
    """Test handling of files with unicode characters."""
    with runner.isolated_filesystem():
        # Create file with unicode content
        test_file = Path("test.py")
        test_file.write_text('''
def greet():
    """✨ Greet in multiple languages ✨"""
    return "Hello, 世界!"
''', encoding='utf-8')

        # Run analysis
        result = runner.invoke(main, ['.', '--debug'])
        assert result.exit_code == 0

        # Check output file
        output_dir = Path('.codelens')
        assert output_dir.exists()
        analysis_file = output_dir / 'analysis.txt'
        assert analysis_file.exists()

        # Verify content preserves unicode
        content = analysis_file.read_text(encoding='utf-8')
        assert "世界" in content
        assert "✨" in content

def test_error_recovery(runner):
    """Test recovery from analysis errors."""
    with runner.isolated_filesystem():
        # Create output directory
        output_dir = Path('.codelens')
        output_dir.mkdir(exist_ok=True)

        # Create a valid file and an invalid one
        valid_file = Path("valid.py")
        valid_file.write_text("print('valid')")

        invalid_file = Path("invalid.py")
        invalid_file.write_text("this is not valid python")

        result = runner.invoke(main, ['.', '--debug'])
        assert result.exit_code == 0
        assert output_dir.exists()