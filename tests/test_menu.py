"""
Unit tests for the interactive menu functionality.
"""

import pytest
from pathlib import Path
import tempfile
import os
from src.llm_code_lens.menu import MenuState

def test_menu_state_validation():
    """Test that MenuState validation correctly identifies excluded items."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a test directory structure
        root = Path(tmpdir)
        
        # Create some test directories and files
        (root / "dir1").mkdir()
        (root / "dir2").mkdir()
        (root / "dir1" / "subdir").mkdir()
        (root / "file1.txt").write_text("test")
        (root / "dir1" / "file2.txt").write_text("test")
        
        # Initialize menu state
        state = MenuState(root)
        
        # Exclude some items
        state.excluded_items.add(str(root / "dir1"))
        state.excluded_items.add(str(root / "file1.txt"))
        
        # Validate selection
        validation = state.validate_selection()
        
        # Check results
        assert validation['excluded_count'] == 2
        assert len(validation['excluded_dirs']) == 1
        assert len(validation['excluded_files']) == 1
        assert str(root / "dir1") in validation['excluded_dirs']
        assert str(root / "file1.txt") in validation['excluded_files']

def test_menu_state_is_excluded():
    """Test that is_excluded correctly identifies excluded items including parent directories."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a test directory structure
        root = Path(tmpdir)
        
        # Create some test directories and files
        (root / "dir1").mkdir()
        (root / "dir1" / "subdir").mkdir()
        (root / "dir1" / "file1.txt").write_text("test")
        (root / "dir1" / "subdir" / "file2.txt").write_text("test")
        
        # Initialize menu state
        state = MenuState(root)
        
        # Exclude a directory
        state.excluded_items.add(str(root / "dir1"))
        
        # Test exclusion
        assert state.is_excluded(root / "dir1") == True
        assert state.is_excluded(root / "dir1" / "file1.txt") == True
        assert state.is_excluded(root / "dir1" / "subdir") == True
        assert state.is_excluded(root / "dir1" / "subdir" / "file2.txt") == True
        
        # Reset and test file exclusion
        state.excluded_items.clear()
        state.excluded_items.add(str(root / "dir1" / "file1.txt"))
        
        assert state.is_excluded(root / "dir1") == False
        assert state.is_excluded(root / "dir1" / "file1.txt") == True
        assert state.is_excluded(root / "dir1" / "subdir") == False
        assert state.is_excluded(root / "dir1" / "subdir" / "file2.txt") == False

def test_get_results_includes_validation():
    """Test that get_results includes validation data when debug is enabled."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a test directory structure
        root = Path(tmpdir)
        
        # Initialize menu state with debug enabled
        state = MenuState(root, {'debug': True})
        
        # Exclude some items
        state.excluded_items.add(str(root / "some_dir"))
        state.excluded_items.add(str(root / "some_file.txt"))
        
        # Get results
        results = state.get_results()
        
        # Check that validation data is included
        assert 'validation' in results
        assert results['validation'] is not None
        assert results['validation']['excluded_count'] == 2
