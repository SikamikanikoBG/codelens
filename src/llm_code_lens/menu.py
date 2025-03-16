"""
LLM Code Lens - Interactive Menu Module
Provides a TUI for selecting files and directories to include/exclude in analysis.
"""

import curses
import os
from pathlib import Path
from typing import Dict, List, Any, Tuple, Set, Optional


class MenuState:
    """Class to manage the state of the interactive menu."""
    
    def __init__(self, root_path: Path):
        self.root_path = root_path.resolve()
        self.current_path = self.root_path
        self.expanded_dirs: Set[str] = set()
        self.selected_items: Set[str] = set()  # Items explicitly selected
        self.excluded_items: Set[str] = set()  # Items explicitly excluded
        self.cursor_pos = 0
        self.scroll_offset = 0
        self.visible_items: List[Tuple[Path, int]] = []  # (path, depth)
        self.max_visible = 0
        self.status_message = ""
        
    def toggle_dir_expanded(self, path: Path) -> None:
        """Toggle directory expansion state."""
        path_str = str(path)
        if path_str in self.expanded_dirs:
            self.expanded_dirs.remove(path_str)
        else:
            self.expanded_dirs.add(path_str)
        self.rebuild_visible_items()
            
    def toggle_selection(self, path: Path) -> None:
        """Toggle selection status of an item."""
        path_str = str(path)
        
        # If item was excluded, remove from excluded and add to selected
        if path_str in self.excluded_items:
            self.excluded_items.remove(path_str)
            self.selected_items.add(path_str)
        # If item was selected, remove from selected and add to excluded
        elif path_str in self.selected_items:
            self.selected_items.remove(path_str)
            self.excluded_items.add(path_str)
        # If item was neither, add to selected
        else:
            self.selected_items.add(path_str)
            
    def is_selected(self, path: Path) -> bool:
        """Check if a path is selected."""
        path_str = str(path)
        
        # Check if this path or any parent is explicitly selected
        current = path
        while current != self.root_path and current != current.parent:
            if str(current) in self.selected_items:
                return True
            current = current.parent
            
        # If not explicitly selected or excluded, it's included by default
        if path_str not in self.excluded_items:
            return True
            
        return False
        
    def is_excluded(self, path: Path) -> bool:
        """Check if a path is excluded."""
        path_str = str(path)
        
        # Check if this path or any parent is explicitly excluded
        current = path
        while current != self.root_path and current != current.parent:
            if str(current) in self.excluded_items:
                return True
            current = current.parent
            
        return False
    
    def get_current_item(self) -> Optional[Path]:
        """Get the currently selected item."""
        if 0 <= self.cursor_pos < len(self.visible_items):
            return self.visible_items[self.cursor_pos][0]
        return None
        
    def move_cursor(self, direction: int) -> None:
        """Move the cursor up or down."""
        new_pos = self.cursor_pos + direction
        if 0 <= new_pos < len(self.visible_items):
            self.cursor_pos = new_pos
            
            # Adjust scroll if needed
            if self.cursor_pos < self.scroll_offset:
                self.scroll_offset = self.cursor_pos
            elif self.cursor_pos >= self.scroll_offset + self.max_visible:
                self.scroll_offset = self.cursor_pos - self.max_visible + 1
    
    def rebuild_visible_items(self) -> None:
        """Rebuild the list of visible items based on expanded directories."""
        self.visible_items = []
        self._build_item_list(self.root_path, 0)
        
        # Adjust cursor position if it's now out of bounds
        if self.cursor_pos >= len(self.visible_items) and len(self.visible_items) > 0:
            self.cursor_pos = len(self.visible_items) - 1
            
        # Adjust scroll offset if needed
        if self.cursor_pos < self.scroll_offset:
            self.scroll_offset = max(0, self.cursor_pos)
        elif self.cursor_pos >= self.scroll_offset + self.max_visible:
            self.scroll_offset = max(0, self.cursor_pos - self.max_visible + 1)
    
    def _build_item_list(self, path: Path, depth: int) -> None:
        """Recursively build the list of visible items."""
        try:
            # Add the current path
            self.visible_items.append((path, depth))
            
            # If it's a directory and it's expanded, add its children
            if path.is_dir() and str(path) in self.expanded_dirs:
                try:
                    # Sort directories first, then files
                    items = sorted(path.iterdir(), 
                                  key=lambda p: (0 if p.is_dir() else 1, p.name.lower()))
                    
                    for item in items:
                        # Skip hidden files/directories
                        if item.name.startswith('.'):
                            continue
                        
                        self._build_item_list(item, depth + 1)
                except PermissionError:
                    # Handle permission errors gracefully
                    pass
        except Exception:
            # Ignore any errors during item list building
            pass
    
    def get_results(self) -> Dict[str, Any]:
        """Get the final results of the selection process."""
        include_paths = [Path(p) for p in self.selected_items]
        exclude_paths = [Path(p) for p in self.excluded_items]
        
        return {
            'path': self.root_path,
            'include_paths': include_paths,
            'exclude_paths': exclude_paths
        }


def draw_menu(stdscr, state: MenuState) -> None:
    """Draw the menu interface."""
    curses.curs_set(0)  # Hide cursor
    stdscr.clear()
    
    # Get terminal dimensions
    max_y, max_x = stdscr.getmaxyx()
    state.max_visible = max_y - 4  # Reserve lines for header and footer
    
    # Set up colors
    curses.start_color()
    curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLUE)  # Header/footer
    curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_WHITE)  # Selected item
    curses.init_pair(3, curses.COLOR_GREEN, curses.COLOR_BLACK)  # Included item
    curses.init_pair(4, curses.COLOR_RED, curses.COLOR_BLACK)    # Excluded item
    curses.init_pair(5, curses.COLOR_YELLOW, curses.COLOR_BLACK) # Directory
    
    # Draw header
    header = f" LLM Code Lens - File Selection "
    header = header.center(max_x, "=")
    stdscr.addstr(0, 0, header, curses.color_pair(1))
    
    # Draw items
    visible_count = min(state.max_visible, len(state.visible_items) - state.scroll_offset)
    for i in range(visible_count):
        idx = i + state.scroll_offset
        if idx >= len(state.visible_items):
            break
            
        path, depth = state.visible_items[idx]
        is_dir = path.is_dir()
        is_selected = state.is_selected(path)
        is_excluded = state.is_excluded(path)
        
        # Prepare the display string
        indent = "  " * depth
        prefix = "+ " if is_dir and str(path) in state.expanded_dirs else \
                 "- " if is_dir else "  "
        
        # Determine selection indicator
        if str(path) in state.selected_items:
            sel_indicator = "[+]"  # Using + instead of ✓
        elif str(path) in state.excluded_items:
            sel_indicator = "[-]"  # Using - instead of ✗
        else:
            sel_indicator = "[ ]"
            
        item_str = f"{indent}{prefix}{sel_indicator} {path.name}"
        
        # Truncate if too long
        if len(item_str) > max_x - 2:
            item_str = item_str[:max_x - 5] + "..."
            
        # Determine color
        if idx == state.cursor_pos:
            attr = curses.color_pair(2)  # Highlighted
        elif is_excluded:
            attr = curses.color_pair(4)  # Excluded
        elif is_selected or (not is_excluded and not str(path) in state.selected_items):
            attr = curses.color_pair(3)  # Included
        else:
            attr = 0  # Default
            
        # If it's a directory, add directory color
        if is_dir and idx != state.cursor_pos:
            attr = curses.color_pair(5)
            
        # Draw the item
        stdscr.addstr(i + 1, 0, " " * max_x)  # Clear line
        stdscr.addstr(i + 1, 0, item_str, attr)
    
    # Draw footer with controls
    footer_y = max_y - 2
    controls = " ↑/↓: Navigate | →: Expand | ←: Collapse | Space: Toggle | Enter: Confirm "
    controls = controls.center(max_x, "=")
    stdscr.addstr(footer_y, 0, controls, curses.color_pair(1))
    
    # Draw status message
    status_y = max_y - 1
    status = f" {state.status_message} "
    if not status.strip():
        status = " Green: Included | Red: Excluded | Yellow: Directory "
    status = status.ljust(max_x)
    stdscr.addstr(status_y, 0, status)
    
    stdscr.refresh()


def handle_input(key: int, state: MenuState) -> bool:
    """Handle user input. Returns True if user wants to exit."""
    current_item = state.get_current_item()
    
    if key == curses.KEY_UP:
        state.move_cursor(-1)
    elif key == curses.KEY_DOWN:
        state.move_cursor(1)
    elif key == curses.KEY_RIGHT and current_item and current_item.is_dir():
        # Expand directory
        state.expanded_dirs.add(str(current_item))
        state.rebuild_visible_items()
    elif key == curses.KEY_LEFT and current_item and current_item.is_dir():
        # Collapse directory
        if str(current_item) in state.expanded_dirs:
            state.expanded_dirs.remove(str(current_item))
        else:
            # If already collapsed, go to parent
            parent = current_item.parent
            for i, (path, _) in enumerate(state.visible_items):
                if path == parent:
                    state.cursor_pos = i
                    break
        state.rebuild_visible_items()
    elif key == ord(' ') and current_item:
        # Toggle selection
        state.toggle_selection(current_item)
    elif key == 10:  # Enter key
        # Confirm selection and exit
        return True
    elif key == ord('q'):
        # Quit without saving
        return True
        
    return False


def run_menu(path: Path) -> Dict[str, Any]:
    """
    Run the interactive file selection menu.
    
    Args:
        path: Root path to start the file browser
        
    Returns:
        Dict with selected paths and settings
    """
    def _menu_main(stdscr) -> Dict[str, Any]:
        # Initialize curses
        curses.curs_set(0)  # Hide cursor
        stdscr.timeout(100)  # Non-blocking input with 100ms timeout
        
        # Initialize menu state
        state = MenuState(path)
        state.expanded_dirs.add(str(path))  # Start with root expanded
        state.rebuild_visible_items()
        
        # Main loop
        while True:
            draw_menu(stdscr, state)
            
            try:
                key = stdscr.getch()
                if key == -1:  # No input
                    continue
                    
                if handle_input(key, state):
                    break
            except KeyboardInterrupt:
                break
                
        return state.get_results()
    
    # Use curses wrapper to handle terminal setup/cleanup
    try:
        return curses.wrapper(_menu_main)
    except Exception as e:
        # Fallback if curses fails
        print(f"Error in menu: {str(e)}")
        return {'path': path, 'include_paths': [], 'exclude_paths': []}
