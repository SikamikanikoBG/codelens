"""
LLM Code Lens - Interactive Menu Module
Provides a TUI for selecting files and directories to include/exclude in analysis.
"""

import curses
import os
import platform
import subprocess
import tempfile
import webbrowser
from pathlib import Path
from typing import Dict, List, Any, Tuple, Set, Optional


class MenuState:
    """Class to manage the state of the interactive menu."""
    
    def __init__(self, root_path: Path, initial_settings: Dict[str, Any] = None):
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
        
        # CLI options
        self.options = {
            'format': 'txt',           # Output format (txt or json)
            'full': False,             # Export full file contents
            'debug': False,            # Enable debug output
            'sql_server': '',          # SQL Server connection string
            'sql_database': '',        # SQL Database to analyze
            'sql_config': '',          # Path to SQL configuration file
            'exclude_patterns': [],    # Patterns to exclude
            'llm_provider': 'claude',  # Default LLM provider
            'llm_options': {           # LLM provider-specific options
                'provider': 'claude',  # Current provider
                'prompt_template': 'code_analysis',  # Current template
                'providers': {
                    'claude': {
                        'api_key': '',
                        'model': 'claude-3-opus-20240229',
                        'temperature': 0.7,
                        'max_tokens': 4000
                    },
                    'chatgpt': {
                        'api_key': '',
                        'model': 'gpt-4-turbo',
                        'temperature': 0.7,
                        'max_tokens': 4000
                    },
                    'gemini': {
                        'api_key': '',
                        'model': 'gemini-pro',
                        'temperature': 0.7,
                        'max_tokens': 4000
                    },
                    'local': {
                        'url': 'http://localhost:8000',
                        'model': 'llama3',
                        'temperature': 0.7,
                        'max_tokens': 4000
                    }
                },
                'available_providers': ['claude', 'chatgpt', 'gemini', 'local'],
                'prompt_templates': {
                    'code_analysis': 'Analyze this code and provide feedback on structure, potential bugs, and improvements:\n\n{code}',
                    'security_review': 'Review this code for security vulnerabilities and suggest fixes:\n\n{code}',
                    'documentation': 'Generate documentation for this code:\n\n{code}',
                    'refactoring': 'Suggest refactoring improvements for this code:\n\n{code}',
                    'explain': 'Explain how this code works in detail:\n\n{code}'
                }
            }
        }
        
        # Apply initial settings if provided
        if initial_settings:
            for key, value in initial_settings.items():
                if key in self.options:
                    self.options[key] = value
        
        # UI state
        self.active_section = 'files'  # Current active section: 'files' or 'options'
        self.option_cursor = 0         # Cursor position in options section
        self.editing_option = None     # Currently editing option (for text input)
        self.edit_buffer = ""          # Buffer for text input
        
        # Load saved state if available
        self._load_state()
        
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
        
        # If item was excluded, remove from excluded
        if path_str in self.excluded_items:
            self.excluded_items.remove(path_str)
        # If item was neither excluded nor selected, add to excluded
        elif path_str not in self.selected_items:
            self.excluded_items.add(path_str)
        # If item was selected, remove from selected and add to excluded
        else:
            self.selected_items.remove(path_str)
            self.excluded_items.add(path_str)
            
    def is_selected(self, path: Path) -> bool:
        """Check if a path is selected."""
        path_str = str(path)
        
        # Check if this path or any parent is explicitly excluded
        current = path
        while current != self.root_path and current != current.parent:
            if str(current) in self.excluded_items:
                return False
            current = current.parent
            
        # If not explicitly excluded, it's included by default
        return True
        
    def is_excluded(self, path: Path) -> bool:
        """Check if a path is excluded."""
        path_str = str(path)
        
        # Check if this path is explicitly excluded
        if path_str in self.excluded_items:
            return True
            
        # Check if any parent is excluded
        current = path
        while current != self.root_path and current != current.parent:
            current = current.parent
            if str(current) in self.excluded_items:
                return True
                
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
                        # Include hidden files/directories (don't skip them)
                        self._build_item_list(item, depth + 1)
                except PermissionError:
                    # Handle permission errors gracefully
                    pass
        except Exception:
            # Ignore any errors during item list building
            pass
    
    def toggle_option(self, option_name: str) -> None:
        """Toggle a boolean option or cycle through value options."""
        if option_name not in self.options:
            return
            
        if option_name == 'format':
            # Cycle through format options
            self.options[option_name] = 'json' if self.options[option_name] == 'txt' else 'txt'
        elif option_name == 'llm_provider':
            # Cycle through LLM provider options
            providers = list(self.options['llm_options']['providers'].keys())
            current_index = providers.index(self.options[option_name]) if self.options[option_name] in providers else 0
            next_index = (current_index + 1) % len(providers)
            self.options[option_name] = providers[next_index]
        elif isinstance(self.options[option_name], bool):
            # Toggle boolean options
            self.options[option_name] = not self.options[option_name]
        
        self.status_message = f"Option '{option_name}' set to: {self.options[option_name]}"
    
    def set_option(self, option_name: str, value: Any) -> None:
        """Set an option to a specific value."""
        if option_name in self.options:
            self.options[option_name] = value
            self.status_message = f"Option '{option_name}' set to: {value}"
    
    def start_editing_option(self, option_name: str) -> None:
        """Start editing a text-based option."""
        if option_name in self.options:
            self.editing_option = option_name
            self.edit_buffer = str(self.options[option_name])
            self.status_message = f"Editing {option_name}. Press Enter to confirm, Esc to cancel."
    
    def finish_editing(self, save: bool = True) -> None:
        """Finish editing the current option."""
        if self.editing_option and save:
            if self.editing_option == 'new_exclude':
                # Special handling for new exclude pattern
                if self.edit_buffer.strip():
                    self.add_exclude_pattern(self.edit_buffer.strip())
            else:
                # Normal option
                self.options[self.editing_option] = self.edit_buffer
                self.status_message = f"Option '{self.editing_option}' set to: {self.edit_buffer}"
        
        self.editing_option = None
        self.edit_buffer = ""
    
    def add_exclude_pattern(self, pattern: str) -> None:
        """Add an exclude pattern."""
        if pattern and pattern not in self.options['exclude_patterns']:
            self.options['exclude_patterns'].append(pattern)
            self.status_message = f"Added exclude pattern: {pattern}"
    
    def remove_exclude_pattern(self, index: int) -> None:
        """Remove an exclude pattern by index."""
        if 0 <= index < len(self.options['exclude_patterns']):
            pattern = self.options['exclude_patterns'].pop(index)
            self.status_message = f"Removed exclude pattern: {pattern}"
    
    def toggle_section(self) -> None:
        """Toggle between files and options sections."""
        if self.active_section == 'files':
            self.active_section = 'options'
            self.option_cursor = 0
        else:
            self.active_section = 'files'
        
        self.status_message = f"Switched to {self.active_section} section"
    
    def move_option_cursor(self, direction: int) -> None:
        """Move the cursor in the options section."""
        # Count total options (fixed options + exclude patterns)
        total_options = 5 + len(self.options['exclude_patterns'])  # 5 fixed options
        
        new_pos = self.option_cursor + direction
        if 0 <= new_pos < total_options:
            self.option_cursor = new_pos
    
    def validate_selection(self) -> Dict[str, List[str]]:
        """Validate the selection and return statistics about selected/excluded items."""
        stats = {
            'excluded_count': len(self.excluded_items),
            'selected_count': len(self.selected_items),
            'excluded_dirs': [],
            'excluded_files': []
        }
        
        # Categorize excluded items
        for path_str in self.excluded_items:
            path = Path(path_str)
            if path.is_dir():
                stats['excluded_dirs'].append(path_str)
            else:
                stats['excluded_files'].append(path_str)
                
        return stats
    
    def get_results(self) -> Dict[str, Any]:
        """Get the final results of the selection process."""
        include_paths = []
        exclude_paths = [Path(p) for p in self.excluded_items]
        
        # Validate selection and log statistics if debug is enabled
        validation_stats = self.validate_selection()
        if self.options['debug']:
            status_message = (
                f"Selection validation: {validation_stats['excluded_count']} items excluded "
                f"({len(validation_stats['excluded_dirs'])} directories, "
                f"{len(validation_stats['excluded_files'])} files)"
            )
            self.status_message = status_message
            print(status_message)
        
        # Save state for future runs
        self._save_state()
        
        # Return all settings
        return {
            'path': self.root_path,
            'include_paths': include_paths,
            'exclude_paths': exclude_paths,
            'format': self.options['format'],
            'full': self.options['full'],
            'debug': self.options['debug'],
            'sql_server': self.options['sql_server'],
            'sql_database': self.options['sql_database'],
            'sql_config': self.options['sql_config'],
            'exclude': self.options['exclude_patterns'],
            'llm_provider': self.options['llm_provider'],
            'llm_options': self.options['llm_options'],
            'validation': validation_stats if self.options['debug'] else None
        }
        
    def _save_state(self) -> None:
        """Save the current state to a file."""
        try:
            state_dir = self.root_path / '.codelens'
            state_dir.mkdir(exist_ok=True)
            state_file = state_dir / 'menu_state.json'
            
            # Convert paths to strings for JSON serialization
            state = {
                'expanded_dirs': list(self.expanded_dirs),
                'excluded_items': list(self.excluded_items),
                'options': self.options
            }
            
            import json
            with open(state_file, 'w') as f:
                json.dump(state, f)
        except Exception:
            # Silently fail if we can't save state
            pass
            
    def _load_state(self) -> None:
        """Load the saved state from a file."""
        try:
            state_file = self.root_path / '.codelens' / 'menu_state.json'
            if state_file.exists():
                import json
                with open(state_file, 'r') as f:
                    state = json.load(f)
                
                # Restore state
                self.expanded_dirs = set(state.get('expanded_dirs', []))
                self.excluded_items = set(state.get('excluded_items', []))
                
                # Restore options if available
                if 'options' in state:
                    for key, value in state['options'].items():
                        if key in self.options:
                            self.options[key] = value
                
                # Set status message to indicate loaded state
                excluded_count = len(self.excluded_items)
                if excluded_count > 0:
                    self.status_message = f"Loaded {excluded_count} excluded items from saved state"
        except Exception as e:
            # Log the error instead of silently failing
            self.status_message = f"Error loading menu state: {str(e)}"
            
    def _open_in_llm(self) -> bool:
        """
        Open selected files in the configured LLM provider.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get the current item
            current_item = self.get_current_item()
            if not current_item or not current_item.is_file():
                self.status_message = "Please select a file to open in LLM"
                return False
                
            # Check if file exists and is readable
            if not current_item.exists() or not os.access(current_item, os.R_OK):
                self.status_message = f"Cannot read file: {current_item}"
                return False
                
            # Get the provider configuration
            provider = self.options['llm_provider']
            provider_config = self.options['llm_options']['providers'].get(provider)
            
            if not provider_config:
                self.status_message = f"Provider '{provider}' not configured"
                return False
                
            # Read the file content
            try:
                with open(current_item, 'r', encoding='utf-8') as f:
                    content = f.read()
            except UnicodeDecodeError:
                # Try with a different encoding or binary mode
                try:
                    with open(current_item, 'r', encoding='latin-1') as f:
                        content = f.read()
                except Exception as e:
                    self.status_message = f"Error reading file: {str(e)}"
                    return False
                    
            # Check if content is too large (simple check)
            if len(content) > 100000:  # 100KB limit
                self.status_message = "File is too large to send to LLM"
                return False
                
            # Prepare message for LLM
            file_ext = current_item.suffix.lstrip('.')
            message = f"Here is the content of {current_item.name} (a {file_ext} file):\n\n```{file_ext}\n{content}\n```\n\nPlease analyze this code and provide feedback."
            
            # TODO: Implement actual API calls to different LLM providers
            # This would require importing the appropriate libraries and handling API keys
            
            # For now, just show a success message
            self.status_message = f"File would be sent to {provider} (API integration not implemented)"
            return True
            
        except Exception as e:
            self.status_message = f"Error opening in LLM: {str(e)}"
            return False


def draw_menu(stdscr, state: MenuState) -> None:
    """Draw the menu interface."""
    curses.curs_set(0)  # Hide cursor
    stdscr.clear()
    
    # Get terminal dimensions
    max_y, max_x = stdscr.getmaxyx()
    
    # Set up colors
    curses.start_color()
    curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLUE)   # Header/footer
    curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_WHITE)  # Selected item
    curses.init_pair(3, curses.COLOR_GREEN, curses.COLOR_BLACK)  # Included item
    curses.init_pair(4, curses.COLOR_RED, curses.COLOR_BLACK)    # Excluded item
    curses.init_pair(5, curses.COLOR_YELLOW, curses.COLOR_BLACK) # Directory
    curses.init_pair(6, curses.COLOR_CYAN, curses.COLOR_BLACK)   # Options
    curses.init_pair(7, curses.COLOR_WHITE, curses.COLOR_RED)    # Active section
    
    # Calculate layout
    options_height = 10  # Height of options section
    files_height = max_y - options_height - 4  # Height of files section (minus header/footer)
    
    # Adjust visible items based on active section
    if state.active_section == 'files':
        state.max_visible = files_height
    else:
        state.max_visible = files_height - 2  # Reduce slightly when in options mode
    
    # Draw header
    header = f" LLM Code Lens - {'File Selection' if state.active_section == 'files' else 'Options'} "
    header = header.center(max_x-1, "=")
    try:
        stdscr.addstr(0, 0, header[:max_x-1], curses.color_pair(1))
    except curses.error:
        pass
    
    # Draw section indicator
    section_y = 1
    files_section = " [F]iles "
    options_section = " [O]ptions "
    
    try:
        # Files section indicator
        attr = curses.color_pair(7) if state.active_section == 'files' else curses.color_pair(1)
        stdscr.addstr(section_y, 2, files_section, attr)
        
        # Options section indicator
        attr = curses.color_pair(7) if state.active_section == 'options' else curses.color_pair(1)
        stdscr.addstr(section_y, 2 + len(files_section) + 2, options_section, attr)
    except curses.error:
        pass
    
    # Draw items if in files section or if files section is visible
    if state.active_section == 'files' or True:  # Always show files
        start_y = 2  # Start after header and section indicators
        visible_count = min(state.max_visible, len(state.visible_items) - state.scroll_offset)
        
        for i in range(visible_count):
            idx = i + state.scroll_offset
            if idx >= len(state.visible_items):
                break
                
            path, depth = state.visible_items[idx]
            is_dir = path.is_dir()
            is_excluded = state.is_excluded(path)
            
            # Prepare the display string
            indent = "  " * depth
            prefix = "+ " if is_dir and str(path) in state.expanded_dirs else \
                     "- " if is_dir else "  "
            
            # Determine selection indicator based on exclusion status
            if is_excluded:
                sel_indicator = "[-]"  # Excluded
            else:
                sel_indicator = "[+]"  # Included
                
            item_str = f"{indent}{prefix}{sel_indicator} {path.name}"
            
            # Truncate if too long
            if len(item_str) > max_x - 2:
                item_str = item_str[:max_x - 5] + "..."
                
            # Determine color
            if state.active_section == 'files' and idx == state.cursor_pos:
                attr = curses.color_pair(2)  # Highlighted
            elif is_excluded:
                attr = curses.color_pair(4)  # Excluded
            elif not is_excluded:
                attr = curses.color_pair(3)  # Included
            else:
                attr = 0  # Default
                
            # If it's a directory, add directory color (but keep excluded color if excluded)
            if is_dir and not (state.active_section == 'files' and idx == state.cursor_pos) and not is_excluded:
                attr = curses.color_pair(5)
                
            # Draw the item
            try:
                stdscr.addstr(i + start_y, 0, " " * (max_x-1))  # Clear line
                # Make sure we don't exceed the screen width
                safe_str = item_str[:max_x-1] if len(item_str) >= max_x else item_str
                stdscr.addstr(i + start_y, 0, safe_str, attr)
            except curses.error:
                # Handle potential curses errors
                pass
    
    # Draw options section
    options_start_y = files_height + 2
    try:
        # Draw options header
        options_header = " Analysis Options "
        options_header = options_header.center(max_x-1, "-")
        stdscr.addstr(options_start_y, 0, options_header[:max_x-1], curses.color_pair(6))
        
        # Draw options
        option_y = options_start_y + 1
        options = [
            ("Format", f"{state.options['format']}", "F1"),
            ("Full Export", f"{state.options['full']}", "F2"),
            ("Debug Mode", f"{state.options['debug']}", "F3"),
            ("SQL Server", f"{state.options['sql_server'] or 'Not set'}", "F4"),
            ("SQL Database", f"{state.options['sql_database'] or 'Not set'}", "F5"),
            ("LLM Provider", f"{state.options['llm_provider']}", "F6")
        ]
        
        # Add exclude patterns
        for i, pattern in enumerate(state.options['exclude_patterns']):
            options.append((f"Exclude Pattern {i+1}", pattern, "Del"))
        
        # Option to add new exclude pattern
        options.append(("Add Exclude Pattern", "", "Ins"))
        
        # Draw each option
        for i, (name, value, key) in enumerate(options):
            if option_y + i >= max_y - 2:  # Don't draw past footer
                break
                
            # Determine if this option is selected
            is_selected = state.active_section == 'options' and i == state.option_cursor
            
            # Format the option string
            option_str = f" {name}: {value}"
            key_str = f"[{key}]"
            
            # Calculate padding to right-align the key
            padding = max_x - len(option_str) - len(key_str) - 2
            if padding < 1:
                padding = 1
                
            display_str = f"{option_str}{' ' * padding}{key_str}"
            
            # Truncate if too long
            if len(display_str) > max_x - 2:
                display_str = display_str[:max_x - 5] + "..."
            
            # Draw with appropriate highlighting
            attr = curses.color_pair(2) if is_selected else curses.color_pair(6)
            stdscr.addstr(option_y + i, 0, " " * (max_x-1))  # Clear line
            stdscr.addstr(option_y + i, 0, display_str, attr)
    except curses.error:
        pass
    
    # Draw footer with controls
    footer_y = max_y - 2
    
    if state.editing_option:
        # Show editing controls
        controls = " Enter: Confirm | Esc: Cancel "
    elif state.active_section == 'files':
        # Show file navigation controls
        controls = " Up/Down: Navigate | Right: Expand | Left: Collapse | Space: Toggle | F7: Open in LLM | Tab: Options | Enter: Confirm "
    else:
        # Show options controls
        controls = " Up/Down: Navigate | Space: Toggle/Edit | Tab: Files | Enter: Confirm "
        
    controls = controls.center(max_x-1, "=")
    try:
        stdscr.addstr(footer_y, 0, controls[:max_x-1], curses.color_pair(1))
    except curses.error:
        pass
    
    # Draw status message or editing prompt
    status_y = max_y - 1
    
    if state.editing_option:
        # Show editing prompt
        prompt = f" Editing {state.editing_option}: {state.edit_buffer} "
        stdscr.addstr(status_y, 0, " " * (max_x-1))  # Clear line
        stdscr.addstr(status_y, 0, prompt[:max_x-1])
        # Show cursor
        curses.curs_set(1)
        stdscr.move(status_y, len(f" Editing {state.editing_option}: ") + len(state.edit_buffer))
    else:
        # Show status message
        status = f" {state.status_message} "
        if not status.strip():
            if state.active_section == 'files':
                excluded_count = len(state.excluded_items)
                if excluded_count > 0:
                    status = f" {excluded_count} items excluded | Space: Toggle exclusion | Enter: Confirm "
                else:
                    status = " All files included by default | Space: Toggle exclusion | Enter: Confirm "
            else:
                status = " Use Space to toggle options or edit text fields | Enter: Confirm "
                
        status = status.ljust(max_x-1)
        try:
            stdscr.addstr(status_y, 0, status[:max_x-1])
        except curses.error:
            pass
    
    stdscr.refresh()


def handle_input(key: int, state: MenuState) -> bool:
    """Handle user input. Returns True if user wants to exit."""
    # Handle editing mode separately
    if state.editing_option:
        if key == 27:  # Escape key
            state.finish_editing(save=False)
        elif key == 10:  # Enter key
            state.finish_editing(save=True)
        elif key == curses.KEY_BACKSPACE or key == 127:  # Backspace
            state.edit_buffer = state.edit_buffer[:-1]
        elif 32 <= key <= 126:  # Printable ASCII characters
            state.edit_buffer += chr(key)
        return False
    
    # Handle normal navigation mode
    if key == 9:  # Tab key
        state.toggle_section()
    elif key == 10:  # Enter key
        # Confirm selection and exit
        return True
    elif key == ord('q'):
        # Quit without saving
        return True
    elif key == ord('f') or key == ord('F'):
        state.active_section = 'files'
    elif key == ord('o') or key == ord('O'):
        state.active_section = 'options'
        
    # Files section controls
    if state.active_section == 'files':
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
    
    # Options section controls
    elif state.active_section == 'options':
        if key == curses.KEY_UP:
            state.move_option_cursor(-1)
        elif key == curses.KEY_DOWN:
            state.move_option_cursor(1)
        elif key == ord(' '):
            # Toggle or edit the current option
            option_index = state.option_cursor
            
            # Fixed options
            if option_index == 0:  # Format
                state.toggle_option('format')
            elif option_index == 1:  # Full Export
                state.toggle_option('full')
            elif option_index == 2:  # Debug Mode
                state.toggle_option('debug')
            elif option_index == 3:  # SQL Server
                state.start_editing_option('sql_server')
            elif option_index == 4:  # SQL Database
                state.start_editing_option('sql_database')
            elif option_index == 5:  # LLM Provider
                # Cycle through available LLM providers
                providers = list(state.options['llm_options']['providers'].keys())
                current_index = providers.index(state.options['llm_provider']) if state.options['llm_provider'] in providers else 0
                next_index = (current_index + 1) % len(providers)
                state.options['llm_provider'] = providers[next_index]
                state.status_message = f"LLM Provider set to: {state.options['llm_provider']}"
            elif option_index == 6 + len(state.options['exclude_patterns']):  # Add exclude pattern
                state.start_editing_option('new_exclude')
            elif option_index >= 5 and option_index < 5 + len(state.options['exclude_patterns']):
                # Remove exclude pattern
                pattern_index = option_index - 5
                state.remove_exclude_pattern(pattern_index)
    
    # Function key controls (work in any section)
    if key == curses.KEY_F1:
        state.toggle_option('format')
    elif key == curses.KEY_F2:
        state.toggle_option('full')
    elif key == curses.KEY_F3:
        state.toggle_option('debug')
    elif key == curses.KEY_F4:
        state.start_editing_option('sql_server')
    elif key == curses.KEY_F5:
        state.start_editing_option('sql_database')
    elif key == curses.KEY_F6:
        # Cycle through available LLM providers
        providers = list(state.options['llm_options']['providers'].keys())
        current_index = providers.index(state.options['llm_provider']) if state.options['llm_provider'] in providers else 0
        next_index = (current_index + 1) % len(providers)
        state.options['llm_provider'] = providers[next_index]
        state.status_message = f"LLM Provider set to: {state.options['llm_provider']}"
    elif key == curses.KEY_F7:
        # Open current file in LLM
        state._open_in_llm()
    elif key == curses.KEY_DC:  # Delete key
        if state.active_section == 'options' and state.option_cursor >= 5 and state.option_cursor < 5 + len(state.options['exclude_patterns']):
            pattern_index = state.option_cursor - 5
            state.remove_exclude_pattern(pattern_index)
    elif key == curses.KEY_IC:  # Insert key
        state.start_editing_option('new_exclude')
        
    return False


def run_menu(path: Path, initial_settings: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Run the interactive file selection menu.
    
    Args:
        path: Root path to start the file browser
        initial_settings: Initial settings from command line arguments
        
    Returns:
        Dict with selected paths and settings
    """
    def _menu_main(stdscr) -> Dict[str, Any]:
        # Initialize curses
        curses.curs_set(0)  # Hide cursor
        stdscr.timeout(100)  # Non-blocking input with 100ms timeout
        
        # Initialize menu state with initial settings
        state = MenuState(path, initial_settings)
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
