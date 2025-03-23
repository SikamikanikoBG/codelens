"""
Unit tests for the menu drawing functionality.
"""

import pytest
from pathlib import Path
import tempfile
import os
import sys
import curses
from unittest.mock import patch, MagicMock, call
from llm_code_lens.menu import MenuState, draw_menu

@patch('curses.curs_set')
@patch('curses.start_color')
@patch('curses.init_pair')
def test_draw_menu_setup(mock_init_pair, mock_start_color, mock_curs_set):
    """Test the setup portion of draw_menu."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        state = MenuState(root)
        
        # Create a mock stdscr
        stdscr = MagicMock()
        stdscr.getmaxyx.return_value = (25, 80)  # 25 rows, 80 columns
        
        # Call draw_menu
        draw_menu(stdscr, state)
        
        # Verify setup calls
        mock_curs_set.assert_called_with(0)  # Hide cursor
        stdscr.clear.assert_called_once()
        mock_start_color.assert_called_once()
        
        # Verify color pairs were initialized
        assert mock_init_pair.call_count >= 5

@patch('curses.curs_set')
def test_draw_menu_header(mock_curs_set):
    """Test drawing the header in draw_menu."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        state = MenuState(root)
        
        # Create a mock stdscr
        stdscr = MagicMock()
        stdscr.getmaxyx.return_value = (25, 80)  # 25 rows, 80 columns
        
        # Call draw_menu
        draw_menu(stdscr, state)
        
        # Verify header was drawn
        header_calls = [call for call in stdscr.addstr.call_args_list if call[0][0] == 0]
        assert len(header_calls) > 0
        
        # Verify section indicators were drawn
        section_calls = [call for call in stdscr.addstr.call_args_list if call[0][0] == 1]
        assert len(section_calls) >= 2  # At least files and options sections

@patch('curses.curs_set')
def test_draw_menu_files_section(mock_curs_set):
    """Test drawing the files section in draw_menu."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "test_dir").mkdir()
        (root / "test_file.txt").write_text("test")
        
        state = MenuState(root)
        state.expanded_dirs.add(str(root))
        state.rebuild_visible_items()
        
        # Create a mock stdscr
        stdscr = MagicMock()
        stdscr.getmaxyx.return_value = (25, 80)  # 25 rows, 80 columns
        
        # Call draw_menu
        draw_menu(stdscr, state)
        
        # Verify files were drawn (starting from row 2)
        file_calls = [call for call in stdscr.addstr.call_args_list if call[0][0] >= 2 and call[0][0] < 15]
        assert len(file_calls) >= 3  # Root, test_dir, and test_file.txt

@patch('curses.curs_set')
def test_draw_menu_options_section(mock_curs_set):
    """Test drawing the options section in draw_menu."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        state = MenuState(root)
        
        # Create a mock stdscr
        stdscr = MagicMock()
        stdscr.getmaxyx.return_value = (25, 80)  # 25 rows, 80 columns
        
        # Call draw_menu
        draw_menu(stdscr, state)
        
        # Verify options header was drawn
        options_header_calls = [call for call in stdscr.addstr.call_args_list 
                               if call[0][0] == 15 and "Options" in str(call)]
        assert len(options_header_calls) > 0
        
        # Verify options were drawn
        option_calls = [call for call in stdscr.addstr.call_args_list 
                       if call[0][0] > 15 and call[0][0] < 23]
        assert len(option_calls) >= 5  # At least 5 options

@patch('curses.curs_set')
def test_draw_menu_footer(mock_curs_set):
    """Test drawing the footer in draw_menu."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        state = MenuState(root)
        
        # Create a mock stdscr
        stdscr = MagicMock()
        stdscr.getmaxyx.return_value = (25, 80)  # 25 rows, 80 columns
        
        # Call draw_menu
        draw_menu(stdscr, state)
        
        # Verify footer was drawn (second to last row)
        footer_calls = [call for call in stdscr.addstr.call_args_list if call[0][0] == 23]
        assert len(footer_calls) > 0
        
        # Verify status message was drawn (last row)
        status_calls = [call for call in stdscr.addstr.call_args_list if call[0][0] == 24]
        assert len(status_calls) > 0

@patch('curses.curs_set')
def test_draw_menu_editing_mode(mock_curs_set):
    """Test drawing the menu in editing mode."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        state = MenuState(root)
        
        # Set up editing mode
        state.editing_option = 'sql_server'
        state.edit_buffer = 'localhost'
        
        # Create a mock stdscr
        stdscr = MagicMock()
        stdscr.getmaxyx.return_value = (25, 80)  # 25 rows, 80 columns
        
        # Call draw_menu
        draw_menu(stdscr, state)
        
        # Verify cursor is shown
        mock_curs_set.assert_called_with(1)
        
        # Verify editing prompt is shown in status line
        status_calls = [call for call in stdscr.addstr.call_args_list if call[0][0] == 24]
        assert any("Editing sql_server: localhost" in str(call) for call in status_calls)
        
        # Verify cursor is positioned at end of edit buffer
        stdscr.move.assert_called_once()
        move_args = stdscr.move.call_args[0]
        assert move_args[0] == 24  # Last row
        assert move_args[1] > 20  # After the prompt
