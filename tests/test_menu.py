"""
Unit tests for the interactive menu functionality.
"""

import pytest
from pathlib import Path
import tempfile
import os
import sys
import json
import curses
from unittest.mock import patch, MagicMock
from llm_code_lens.menu import MenuState, run_menu, draw_menu, handle_input

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

def test_menu_state_toggle_selection():
    """Test toggling selection status of items."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "test_file.txt").write_text("test")
        
        state = MenuState(root)
        test_file = root / "test_file.txt"
        
        # Initially not excluded
        assert not state.is_excluded(test_file)
        
        # Toggle once - should exclude
        state.toggle_selection(test_file)
        assert state.is_excluded(test_file)
        assert str(test_file) in state.excluded_items
        
        # Toggle again - should include
        state.toggle_selection(test_file)
        assert not state.is_excluded(test_file)
        assert str(test_file) not in state.excluded_items

def test_menu_state_toggle_dir_expanded():
    """Test toggling directory expansion."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "test_dir").mkdir()
        
        state = MenuState(root)
        test_dir = root / "test_dir"
        
        # Initially not expanded
        assert str(test_dir) not in state.expanded_dirs
        
        # Mock rebuild_visible_items to avoid implementation details
        state.rebuild_visible_items = MagicMock()
        
        # Toggle expansion
        state.toggle_dir_expanded(test_dir)
        assert str(test_dir) in state.expanded_dirs
        state.rebuild_visible_items.assert_called_once()
        
        # Toggle again
        state.rebuild_visible_items.reset_mock()
        state.toggle_dir_expanded(test_dir)
        assert str(test_dir) not in state.expanded_dirs
        state.rebuild_visible_items.assert_called_once()

def test_menu_state_move_cursor():
    """Test cursor movement."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        state = MenuState(root)
        
        # Setup visible items
        state.visible_items = [(root, 0), (root / "file1.txt", 1), (root / "file2.txt", 1)]
        state.cursor_pos = 0
        state.max_visible = 2
        state.scroll_offset = 0
        
        # Move down
        state.move_cursor(1)
        assert state.cursor_pos == 1
        
        # Move down again
        state.move_cursor(1)
        assert state.cursor_pos == 2
        
        # Try to move past end (should not change)
        state.move_cursor(1)
        assert state.cursor_pos == 2
        
        # Move up
        state.move_cursor(-1)
        assert state.cursor_pos == 1
        
        # Move up again
        state.move_cursor(-1)
        assert state.cursor_pos == 0
        
        # Try to move before start (should not change)
        state.move_cursor(-1)
        assert state.cursor_pos == 0

def test_menu_state_rebuild_visible_items():
    """Test rebuilding visible items list."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "dir1").mkdir()
        (root / "file1.txt").write_text("test")
        
        state = MenuState(root)
        state.expanded_dirs.add(str(root))
        
        # Initial state
        state.rebuild_visible_items()
        
        # Should have root and its children
        assert len(state.visible_items) >= 3  # root, dir1, file1.txt
        
        # Check that root is first
        assert state.visible_items[0][0] == root
        
        # Check that children are included with correct depth
        dir_found = False
        file_found = False
        for path, depth in state.visible_items[1:]:
            if path.name == "dir1":
                dir_found = True
                assert depth == 1
            elif path.name == "file1.txt":
                file_found = True
                assert depth == 1
        
        assert dir_found and file_found

def test_menu_state_toggle_option():
    """Test toggling options."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        state = MenuState(root)
        
        # Test boolean option
        assert state.options['full'] is False
        state.toggle_option('full')
        assert state.options['full'] is True
        state.toggle_option('full')
        assert state.options['full'] is False
        
        # Test format option cycling
        assert state.options['format'] == 'txt'
        state.toggle_option('format')
        assert state.options['format'] == 'json'
        state.toggle_option('format')
        assert state.options['format'] == 'txt'

def test_menu_state_save_load_state():
    """Test saving and loading menu state."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        
        # Create initial state
        state1 = MenuState(root)
        state1.expanded_dirs.add(str(root / "dir1"))
        state1.excluded_items.add(str(root / "file1.txt"))
        state1.options['format'] = 'json'
        state1.options['debug'] = True
        
        # Save state
        state1._save_state()
        
        # Check that state file was created
        state_file = root / '.codelens' / 'menu_state.json'
        assert state_file.exists()
        
        # Create new state object which should load the saved state
        state2 = MenuState(root)
        
        # Verify state was loaded
        assert str(root / "dir1") in state2.expanded_dirs
        assert str(root / "file1.txt") in state2.excluded_items
        assert state2.options['format'] == 'json'
        assert state2.options['debug'] is True

@patch('curses.wrapper')
def test_run_menu(mock_wrapper):
    """Test the run_menu function."""
    # Setup mock return value
    expected_results = {'path': Path('/test'), 'include_paths': [], 'exclude_paths': []}
    mock_wrapper.return_value = expected_results
    
    # Call run_menu
    results = run_menu(Path('/test'))
    
    # Verify wrapper was called
    mock_wrapper.assert_called_once()
    
    # Verify results
    assert results == expected_results

@patch('curses.wrapper')
def test_run_menu_exception(mock_wrapper):
    """Test run_menu error handling."""
    # Setup mock to raise exception
    mock_wrapper.side_effect = Exception("Test error")
    
    # Call run_menu
    results = run_menu(Path('/test'))
    
    # Verify fallback results
    assert 'path' in results
    assert 'include_paths' in results
    assert 'exclude_paths' in results
    assert results['include_paths'] == []
    assert results['exclude_paths'] == []

def test_handle_input_navigation():
    """Test handle_input for navigation keys."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        state = MenuState(root)
        
        # Setup state for testing
        state.active_section = 'files'
        state.cursor_pos = 1
        state.visible_items = [(root, 0), (root / "file1.txt", 1), (root / "file2.txt", 1)]
        state.move_cursor = MagicMock()
        
        # Test up arrow
        result = handle_input(259, state)  # KEY_UP
        assert result is False
        state.move_cursor.assert_called_with(-1)
        
        # Test down arrow
        state.move_cursor.reset_mock()
        result = handle_input(258, state)  # KEY_DOWN
        assert result is False
        state.move_cursor.assert_called_with(1)

def test_handle_input_toggle_section():
    """Test handle_input for toggling between sections."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        state = MenuState(root)
        
        # Start in files section
        state.active_section = 'files'
        
        # Test tab key
        result = handle_input(9, state)  # Tab
        assert result is False
        assert state.active_section == 'options'
        
        # Test tab again
        result = handle_input(9, state)  # Tab
        assert result is False
        assert state.active_section == 'files'
        
        # Test 'o' key
        result = handle_input(ord('o'), state)
        assert result is False
        assert state.active_section == 'options'
        
        # Test 'f' key
        result = handle_input(ord('f'), state)
        assert result is False
        assert state.active_section == 'files'

def test_handle_input_editing_mode():
    """Test handle_input in editing mode."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        state = MenuState(root)
        
        # Set up editing mode
        state.editing_option = 'sql_server'
        state.edit_buffer = "test"
        state.finish_editing = MagicMock()
        
        # Test escape key
        result = handle_input(27, state)  # Escape
        assert result is False
        state.finish_editing.assert_called_with(save=False)
        
        # Reset and test enter key
        state.finish_editing.reset_mock()
        result = handle_input(10, state)  # Enter
        assert result is False
        state.finish_editing.assert_called_with(save=True)
        
        # Test backspace
        state.finish_editing.reset_mock()
        state.finish_editing = lambda save: None  # Replace with dummy function
        state.edit_buffer = "test"
        result = handle_input(127, state)  # Backspace
        assert result is False
        assert state.edit_buffer == "tes"
        
        # Test adding character
        result = handle_input(ord('x'), state)
        assert result is False
        assert state.edit_buffer == "tesx"

def test_handle_input_file_navigation():
    """Test handle_input for file navigation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "test_dir").mkdir()
        
        state = MenuState(root)
        state.expanded_dirs.add(str(root))
        state.rebuild_visible_items()
        
        # Mock functions to avoid side effects
        state.toggle_dir_expanded = MagicMock()
        state.toggle_selection = MagicMock()
        
        # Set up current item to be a directory
        test_dir = root / "test_dir"
        state.get_current_item = MagicMock(return_value=test_dir)
        
        # Test right arrow (expand directory)
        result = handle_input(curses.KEY_RIGHT, state)
        assert result is False
        state.expanded_dirs.add.assert_called_with(str(test_dir))
        
        # Test left arrow (collapse directory)
        state.expanded_dirs.add.reset_mock()
        state.expanded_dirs.add(str(test_dir))  # Add to expanded dirs
        result = handle_input(curses.KEY_LEFT, state)
        assert result is False
        assert str(test_dir) not in state.expanded_dirs
        
        # Test space (toggle selection)
        result = handle_input(ord(' '), state)
        assert result is False
        state.toggle_selection.assert_called_with(test_dir)

def test_handle_input_option_controls():
    """Test handle_input for option controls."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        state = MenuState(root)
        
        # Switch to options section
        state.active_section = 'options'
        state.option_cursor = 0
        
        # Mock functions
        state.toggle_option = MagicMock()
        state.start_editing_option = MagicMock()
        state.move_option_cursor = MagicMock()
        
        # Test up/down arrows
        result = handle_input(curses.KEY_UP, state)
        assert result is False
        state.move_option_cursor.assert_called_with(-1)
        
        state.move_option_cursor.reset_mock()
        result = handle_input(curses.KEY_DOWN, state)
        assert result is False
        state.move_option_cursor.assert_called_with(1)
        
        # Test space for format option (index 0)
        result = handle_input(ord(' '), state)
        assert result is False
        state.toggle_option.assert_called_with('format')
        
        # Test space for SQL Server option (index 3)
        state.option_cursor = 3
        state.toggle_option.reset_mock()
        result = handle_input(ord(' '), state)
        assert result is False
        state.start_editing_option.assert_called_with('sql_server')

def test_handle_input_function_keys():
    """Test handle_input for function keys."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        state = MenuState(root)
        
        # Mock functions
        state.toggle_option = MagicMock()
        state.start_editing_option = MagicMock()
        
        # Test function keys
        result = handle_input(curses.KEY_F1, state)
        assert result is False
        state.toggle_option.assert_called_with('format')
        
        state.toggle_option.reset_mock()
        result = handle_input(curses.KEY_F2, state)
        assert result is False
        state.toggle_option.assert_called_with('full')
        
        state.toggle_option.reset_mock()
        result = handle_input(curses.KEY_F3, state)
        assert result is False
        state.toggle_option.assert_called_with('debug')
        
        result = handle_input(curses.KEY_F4, state)
        assert result is False
        state.start_editing_option.assert_called_with('sql_server')

def test_menu_state_set_option():
    """Test setting options in MenuState."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        state = MenuState(root)
        
        # Test setting a string option
        state.set_option('sql_server', 'localhost')
        assert state.options['sql_server'] == 'localhost'
        assert 'sql_server' in state.status_message
        
        # Test setting a boolean option
        state.set_option('debug', True)
        assert state.options['debug'] is True
        assert 'debug' in state.status_message

def test_menu_state_editing_options():
    """Test editing options in MenuState."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        state = MenuState(root)
        
        # Test starting to edit an option
        state.start_editing_option('sql_server')
        assert state.editing_option == 'sql_server'
        assert state.edit_buffer == ''
        assert 'Editing' in state.status_message
        
        # Test finishing editing with save
        state.edit_buffer = 'localhost'
        state.finish_editing(save=True)
        assert state.editing_option is None
        assert state.options['sql_server'] == 'localhost'
        
        # Test editing a new exclude pattern
        state.start_editing_option('new_exclude')
        assert state.editing_option == 'new_exclude'
        
        # Add a mock for add_exclude_pattern
        state.add_exclude_pattern = MagicMock()
        
        # Test finishing with save
        state.edit_buffer = 'node_modules'
        state.finish_editing(save=True)
        state.add_exclude_pattern.assert_called_with('node_modules')

def test_menu_state_exclude_patterns():
    """Test adding and removing exclude patterns."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        state = MenuState(root)
        
        # Test adding a pattern
        state.add_exclude_pattern('node_modules')
        assert 'node_modules' in state.options['exclude_patterns']
        assert 'Added exclude pattern' in state.status_message
        
        # Test adding a duplicate pattern (should not add)
        initial_count = len(state.options['exclude_patterns'])
        state.add_exclude_pattern('node_modules')
        assert len(state.options['exclude_patterns']) == initial_count
        
        # Test removing a pattern
        state.remove_exclude_pattern(0)
        assert 'node_modules' not in state.options['exclude_patterns']
        assert 'Removed exclude pattern' in state.status_message
        
        # Test removing with invalid index
        state.status_message = ""
        state.remove_exclude_pattern(99)
        assert state.status_message == ""  # Should not change
