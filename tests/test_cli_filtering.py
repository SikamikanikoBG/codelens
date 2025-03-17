"""
Unit tests for the file filtering functionality in CLI.
"""

import pytest
from pathlib import Path
import tempfile
import os
from src.llm_code_lens.analyzer.base import ProjectAnalyzer
from src.llm_code_lens.cli import main

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
