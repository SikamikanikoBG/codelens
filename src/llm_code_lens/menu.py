"""
LLM Code Lens - Interactive Menu Module
Provides a TUI for selecting files and directories to include/exclude in analysis.
"""

import curses
import os
import webbrowser
from pathlib import Path
from typing import Dict, List, Any, Tuple, Set, Optional
from llm_code_lens.utils.gitignore import GitignoreParser

class MenuState:
    """Class to manage the state of the interactive menu."""
    
    def __init__(self, root_path: Path, initial_settings: Dict[str, Any] = None):
        self.root_path = root_path.resolve()
        self.current_path = self.root_path
        self.expanded_dirs: Set[str] = set()
        self.selected_items: Set[str] = set()  # Items explicitly selected (overrides exclusions)
        self.partially_selected_items: Set[str] = set()  # Items partially selected
        self.excluded_items: Set[str] = set()  # Items explicitly excluded
        self.cursor_pos = 0
        self.scroll_offset = 0
        self.visible_items: List[Tuple[Path, int]] = []  # (path, depth)
        self.max_visible = 0
        self.status_message = ""
        self.cancelled = False  # Flag to indicate if user cancelled
        
        # Add version update related attributes
        self.new_version_available = False
        self.current_version = ""
        self.latest_version = ""
        self.update_message = ""
        self.show_update_dialog = False
        self.update_in_progress = False
        self.update_result = ""
        
        # Check for updates
        self._check_for_updates()
        
        # New flags for scanning optimization
        self.scan_complete = False
        self.dirty_scan = True  # Indicates directory structure needs rescanning
        self.auto_exclude_complete = False  # Flag to prevent repeated auto-exclusion scans
        
        # Scanning progress tracking
        self.scanning_in_progress = True  # Start in scanning state
        self.scan_current_dir = ""
        self.scan_progress = 0
        self.scan_total = 0
        self.cancel_scan_requested = False
        self.status_message = "Initializing directory scan..."
        
        # Common directories to exclude by default
        self.common_excludes = [
            # Python
            '__pycache__', '.pytest_cache', '.coverage', '.tox', '.mypy_cache', '.ruff_cache',
            'venv', 'env', '.env', '.venv', 'virtualenv', '.virtualenv', 'htmlcov', 'site-packages',
            'egg-info', '.eggs', 'dist', 'build', 'wheelhouse', '.pytype', 'instance',
            
            # JavaScript/TypeScript/React
            'node_modules', 'bower_components', '.npm', '.yarn', '.pnp', '.next', '.nuxt',
            '.cache', '.parcel-cache', '.angular', 'coverage', 'storybook-static', '.storybook',
            'cypress/videos', 'cypress/screenshots', '.docusaurus', 'out', 'dist-*', '.turbo',
            
            # Java/Kotlin/Android
            'target', '.gradle', '.m2', 'build', 'out', '.idea', '.settings', 'bin', 'gen',
            'classes', 'obj', 'proguard', 'captures', '.externalNativeBuild', '.cxx',
            
            # C/C++/C#
            'Debug', 'Release', 'x64', 'x86', 'bin', 'obj', 'ipch', '.vs', 'packages',
            'CMakeFiles', 'CMakeCache.txt', 'cmake-build-*', 'vcpkg_installed',
            
            # Go
            'vendor', '.glide', 'Godeps', '_output', 'bazel-*',
            
            # Rust
            'target', 'Cargo.lock', '.cargo',
            
            # Swift/iOS
            'Pods', '.build', 'DerivedData', '.swiftpm', '*.xcworkspace', '*.xcodeproj/xcuserdata',
            
            # Docker/Kubernetes
            '.docker', 'docker-data', 'k8s-data',
            
            # Version control
            '.git', '.hg', '.svn', '.bzr', '_darcs', 'CVS', '.pijul',
            
            # IDE/Editor
            '.vscode', '.idea', '.vs', '.fleet', '.atom', '.eclipse', '.settings', '.project',
            '.classpath', '.factorypath', '.nbproject', '.sublime-*', '.ensime', '.metals',
            '.bloop', '.history', '.ionide', '__pycharm__', '.spyproject', '.spyderproject',
            
            # Logs and databases
            'logs', '*.log', 'npm-debug.log*', 'yarn-debug.log*', 'yarn-error.log*',
            '*.sqlite', '*.sqlite3', '*.db', 'db.json',
            
            # OS specific
            '.DS_Store', 'Thumbs.db', 'ehthumbs.db', 'Desktop.ini', '$RECYCLE.BIN',
            '.directory', '*.swp', '*.swo', '*~',
            
            # Documentation
            'docs/_build', 'docs/site', 'site', 'public', '_site', '.docz', '.docusaurus',
            
            # Jupyter
            '.ipynb_checkpoints', '.jupyter', '.ipython',
            
            # Tool specific
            '.eslintcache', '.stylelintcache', '.sass-cache', '.phpunit.result.cache',
            '.phpcs-cache', '.php_cs.cache', '.php-cs-fixer.cache', '.sonarqube',
            '.scannerwork', '.terraform', '.terragrunt-cache', '.serverless',
            
            # LLM Code Lens specific
            '.codelens'
        ]
        
        # CLI options (updated)
        self.options = {
            'format': 'txt',           # Output format (txt or json)
            'full': False,             # Export full file contents
            'debug': False,            # Enable debug output
            'sql_server': '',          # SQL Server connection string
            'sql_database': '',        # SQL Database to analyze
            'sql_config': '',          # Path to SQL configuration file
            'exclude_patterns': [],    # Patterns to exclude
            'llm_provider': 'claude',  # Default LLM provider
            'respect_gitignore': True,  # NEW OPTION
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
                'available_providers': ['claude', 'chatgpt', 'gemini', 'local', 'none'],
                'prompt_templates': {
                    'code_analysis': 'Analyze this code and provide feedback on structure, potential bugs, and improvements:\n\n{code}',
                    'security_review': 'Review this code for security vulnerabilities and suggest fixes:\n\n{code}',
                    'documentation': 'Generate documentation for this code:\n\n{code}',
                    'refactoring': 'Suggest refactoring improvements for this code:\n\n{code}',
                    'explain': 'Explain how this code works in detail:\n\n{code}'
                }
            }
        }

        # Initialize gitignore parser
        self.gitignore_parser = None
        if self.options['respect_gitignore']:
            self.gitignore_parser = GitignoreParser(self.root_path)
            self.gitignore_parser.load_gitignore()
        
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
        
        # Load saved state if available - will be done after scanning completes
        # self._load_state()
        
    def toggle_dir_expanded(self, path: Path) -> None:
        """Toggle directory expansion state."""
        path_str = str(path)
        if path_str in self.expanded_dirs:
            self.expanded_dirs.remove(path_str)
        else:
            self.expanded_dirs.add(path_str)
        self.rebuild_visible_items()
            
    def toggle_selection(self, path: Path, fully_select: bool = False) -> None:
        """
        Toggle selection status of an item.
        
        Args:
            path: The path to toggle
            fully_select: If True, fully select the directory and all children
        """
        path_str = str(path)
        
        # Determine the current state
        is_excluded = path_str in self.excluded_items
        is_selected = path_str in self.selected_items
        is_partially_selected = path_str in self.partially_selected_items
        
        # If it's a directory, we'll need to handle all children
        if path.is_dir():
            # If item was excluded, move to partially selected or fully selected state
            if is_excluded:
                # Remove this directory from excluded
                self.excluded_items.discard(path_str)
                
                if fully_select:
                    # Move to fully selected
                    self.selected_items.add(path_str)
                    self.partially_selected_items.discard(path_str)
                    # Recursively include all children
                    self._recursively_include(path)
                else:
                    # Move to partially selected
                    self.partially_selected_items.add(path_str)
                    self.selected_items.discard(path_str)
                    # Expand the directory to show its contents
                    self.expanded_dirs.add(path_str)
                
                # Mark directory structure as dirty to force rescan
                self.dirty_scan = True
                
            # If item was explicitly selected, move to excluded
            elif is_selected:
                # Remove from selected
                self.selected_items.discard(path_str)
                
                # Add to excluded
                self.excluded_items.add(path_str)
                
                # Recursively exclude all children
                self._recursively_exclude(path)
                
                # Mark directory structure as dirty to force rescan
                self.dirty_scan = True
                
            # If item was partially selected, toggle to fully selected or excluded
            elif is_partially_selected:
                # Remove from partially selected
                self.partially_selected_items.discard(path_str)
                
                if fully_select:
                    # Move to fully selected
                    self.selected_items.add(path_str)
                    # Recursively include all children
                    self._recursively_include(path)
                else:
                    # Move to excluded
                    self.excluded_items.add(path_str)
                    # Recursively exclude all children
                    self._recursively_exclude(path)
                
                # Mark directory structure as dirty to force rescan
                self.dirty_scan = True
                
            # If item was neither excluded, selected, nor partially selected
            else:
                if fully_select:
                    # Add to selected
                    self.selected_items.add(path_str)
                    # Recursively include all children
                    self._recursively_include(path)
                else:
                    # Add to excluded
                    self.excluded_items.add(path_str)
                    # Recursively exclude all children
                    self._recursively_exclude(path)
                
                # Mark directory structure as dirty to force rescan
                self.dirty_scan = True
        else:
            # For files, toggle between excluded and included
            if is_excluded:
                self.excluded_items.discard(path_str)
                self.selected_items.add(path_str)  # Explicitly select the file
            elif is_selected:
                self.selected_items.discard(path_str)
                # If the file is in a common directory, exclude it by default
                parent_is_common = any(path.parent.name == common for common in self.common_excludes)
                if parent_is_common:
                    self.excluded_items.add(path_str)
            else:
                self.excluded_items.add(path_str)
            
            # Update parent directory's selection state
            self._update_parent_selection_state(path.parent)
            
            # Mark directory structure as dirty to force rescan
            self.dirty_scan = True
            
    def is_selected(self, path: Path) -> bool:
        """Check if a path is selected."""
        path_str = str(path)
        
        # If the item is explicitly selected, it's included
        if path_str in self.selected_items:
            return True
            
        # If the item is explicitly excluded or partially selected, it's not fully selected
        if path_str in self.excluded_items or path_str in self.partially_selected_items:
            return False
            
        # Check if any parent is explicitly excluded
        current = path.parent
        while current != self.root_path.parent:
            parent_str = str(current)
            if parent_str in self.excluded_items:
                return False
            if parent_str in self.selected_items:
                return True
            current = current.parent
            
        # Check for common directories that should be excluded by default
        if path.is_dir() and path.name in self.common_excludes:
            # Auto-exclude common directories unless they're explicitly selected or partially selected
            if path_str not in self.selected_items and path_str not in self.partially_selected_items:
                return False
                
        # For files in common directories, they're excluded by default
        if path.parent.name in self.common_excludes and path_str not in self.selected_items:
            return False
            
        # If not explicitly excluded and not in a common directory, it's included by default
        return True
        
    def is_partially_selected(self, path: Path) -> bool:
        """Check if a path is partially selected."""
        path_str = str(path)
        
        # Only directories can be partially selected
        if not path.is_dir():
            return False
            
        # If the item is explicitly partially selected
        if path_str in self.partially_selected_items:
            return True
            
        # If the item is explicitly selected or excluded, it's not partially selected
        if path_str in self.selected_items or path_str in self.excluded_items:
            return False
            
        # Check if any parent is partially selected (and this item is not excluded)
        current = path.parent
        while current != self.root_path.parent:
            parent_str = str(current)
            if parent_str in self.partially_selected_items:
                # If parent is partially selected and this item is not excluded, it inherits partial selection
                if path_str not in self.excluded_items:
                    return True
            if parent_str in self.excluded_items:
                return False
            current = current.parent
                
        return False
        
    def _update_parent_selection_state(self, directory: Path) -> None:
        """Update the selection state of a parent directory based on its children."""
        if not directory.exists() or directory == self.root_path.parent:
            return
            
        dir_str = str(directory)
        
        # Skip if the directory is explicitly excluded or selected
        if dir_str in self.excluded_items or dir_str in self.selected_items:
            return
            
        # Initialize counters
        total_children = 0
        selected_children = 0
        excluded_children = 0
        partially_selected_children = 0
        
        try:
            # Count all immediate children
            for child in directory.iterdir():
                child_str = str(child)
                total_children += 1
                
                if child_str in self.selected_items:
                    selected_children += 1
                elif child_str in self.excluded_items:
                    excluded_children += 1
                elif child_str in self.partially_selected_items:
                    partially_selected_children += 1
                else:
                    # If child is neither selected nor excluded, check if it's a common directory
                    if child.is_dir() and child.name in self.common_excludes:
                        excluded_children += 1
        except (PermissionError, OSError):
            # If we can't access the directory, don't change its state
            return
            
        # Skip empty directories
        if total_children == 0:
            return
            
        # Update the directory's state based on its children
        if selected_children == total_children:
            # All children are selected, so the directory should be fully selected
            self.partially_selected_items.discard(dir_str)
            self.selected_items.add(dir_str)
        elif excluded_children == total_children:
            # All children are excluded, so the directory should be excluded
            self.partially_selected_items.discard(dir_str)
            self.selected_items.discard(dir_str)
            self.excluded_items.add(dir_str)
        elif selected_children > 0 or partially_selected_children > 0:
            # Some children are selected or partially selected, so the directory should be partially selected
            self.selected_items.discard(dir_str)
            self.excluded_items.discard(dir_str)
            self.partially_selected_items.add(dir_str)
        else:
            # No children are selected or partially selected, so the directory should be neither
            self.selected_items.discard(dir_str)
            self.partially_selected_items.discard(dir_str)
            
        # Recursively update parent directories, but only if this directory's state changed
        if dir_str in self.selected_items or dir_str in self.partially_selected_items or dir_str in self.excluded_items:
            self._update_parent_selection_state(directory.parent)
        
    def is_excluded(self, path: Path) -> bool:
        """Check if a path is excluded (updated to include gitignore)."""
        path_str = str(path)

        # Check gitignore first if enabled
        if self.gitignore_parser and self.gitignore_parser.should_ignore(path):
            return True

        # If the item is explicitly selected or partially selected, it's not excluded
        if path_str in self.selected_items or path_str in self.partially_selected_items:
            return False

        # Check if this path is explicitly excluded
        if path_str in self.excluded_items:
            return True

        # Check if any parent is excluded
        current = path.parent
        while current != self.root_path.parent:
            if str(current) in self.excluded_items:
                return True
            if str(current) in self.selected_items or str(current) in self.partially_selected_items:
                return False
            current = current.parent

        # Check for common directories that should be excluded by default
        if path.is_dir() and path.name in self.common_excludes:
            return True

        # For files in common directories, they're excluded by default
        if path.parent.name in self.common_excludes:
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
        # Only rebuild if dirty flag is set
        if not self.dirty_scan:
            return

        try:
            # Auto-exclude common directories before building the list
            if not self.auto_exclude_complete:
                self._auto_exclude_common_dirs()
                
                # If scan was cancelled, don't continue
                if self.cancel_scan_requested:
                    self.dirty_scan = False
                    self.scanning_in_progress = False
                    return
            
            # Update status
            self.status_message = "Building directory tree..."
            
            # Reset visible items
            self.visible_items = []
            
            # Build the item list
            self._build_item_list(self.root_path, 0)
            
            # Adjust cursor position if it's now out of bounds
            if self.cursor_pos >= len(self.visible_items) and len(self.visible_items) > 0:
                self.cursor_pos = len(self.visible_items) - 1
                
            # Adjust scroll offset if needed
            if self.cursor_pos < self.scroll_offset:
                self.scroll_offset = max(0, self.cursor_pos)
            elif self.cursor_pos >= self.scroll_offset + self.max_visible:
                self.scroll_offset = max(0, self.cursor_pos - self.max_visible + 1)
            
            # Mark scan as complete and not dirty
            self.scan_complete = True
            self.dirty_scan = False
            self.status_message = "Directory structure loaded"
        except Exception as e:
            self.status_message = f"Error building directory tree: {str(e)}"
        finally:
            # Always reset scanning state when done
            self.scanning_in_progress = False
    
    def _auto_exclude_common_dirs(self) -> None:
        """Automatically exclude common directories that should be ignored."""
        # Prevent repeated scans
        if self.auto_exclude_complete:
            return

        # Set scanning state
        self.scanning_in_progress = True
        self.status_message = "Scanning directory structure..."
        
        try:
            # First, count total directories for progress reporting
            self.scan_total = 0
            self.scan_progress = 0
            
            # Count directories first to provide progress percentage
            self.status_message = "Counting directories for progress tracking..."
            
            # Use a more efficient approach with os.walk
            for root, dirs, _ in os.walk(str(self.root_path)):
                # Check for cancellation request more frequently
                if self.cancel_scan_requested:
                    self.status_message = "Scan cancelled by user"
                    self.scanning_in_progress = False
                    self.dirty_scan = False  # Mark as not dirty to prevent automatic rescan
                    return
                    
                # Update progress for UI feedback
                self.scan_total += len(dirs)
                self.scan_current_dir = os.path.basename(root)
                self.status_message = f"Counting directories: {self.scan_total} found so far..."
                
                # Force screen refresh periodically
                if self.scan_total % 50 == 0:
                    # We can't directly refresh the screen here, but we can yield control
                    # back to the main loop by sleeping briefly
                    import time
                    time.sleep(0.01)
            
            # Now find and exclude common directories
            self.status_message = "Scanning for common directories to exclude..."
            self.scan_progress = 0  # Reset progress for the second phase
            
            # Use a more efficient approach with a single walk
            for root, dirs, _ in os.walk(str(self.root_path)):
                # Check for cancellation request
                if self.cancel_scan_requested:
                    self.status_message = "Scan cancelled by user"
                    self.scanning_in_progress = False
                    self.dirty_scan = False  # Mark as not dirty to prevent automatic rescan
                    return
                
                # Update progress
                self.scan_progress += 1
                
                # Update progress percentage more frequently
                if self.scan_total > 0:
                    progress_pct = min(100, int((self.scan_progress / max(1, self.scan_total)) * 100))
                    self.scan_current_dir = os.path.basename(root)
                    self.status_message = f"Scanning: {self.scan_current_dir} ({progress_pct}%)"
                
                # Check if any of the directories match our common excludes
                for d in dirs[:]:  # Create a copy to safely modify during iteration
                    if d in self.common_excludes:
                        path = Path(os.path.join(root, d))
                        path_str = str(path)
                        if path_str not in self.excluded_items:
                            self.excluded_items.add(path_str)
                
                # Force screen refresh periodically
                if self.scan_progress % 50 == 0:
                    import time
                    time.sleep(0.01)
            
            # Mark auto-exclusion as complete
            self.auto_exclude_complete = True
            self.status_message = "Directory scan complete"
        except Exception as e:
            # Log error but continue
            self.status_message = f"Error during directory scan: {str(e)}"
        finally:
            # Always reset scanning state when done
            if self.cancel_scan_requested:
                self.status_message = "Scan cancelled by user"
                self.dirty_scan = False  # Mark as not dirty to prevent automatic rescan
            
    def _recursively_include(self, directory: Path) -> None:
        """Recursively include all files and subdirectories."""
        try:
            # First, add the directory itself to selected items and remove from other collections
            dir_str = str(directory)
            self.selected_items.add(dir_str)
            self.excluded_items.discard(dir_str)
            self.partially_selected_items.discard(dir_str)
            
            # Process immediate children first to avoid excessive recursion
            try:
                for item in directory.iterdir():
                    item_str = str(item)
                    
                    # Remove from excluded and partially selected items
                    self.excluded_items.discard(item_str)
                    self.partially_selected_items.discard(item_str)
                    
                    # Add to selected items
                    self.selected_items.add(item_str)
                    
                    # If it's a directory, process it recursively
                    if item.is_dir():
                        # Expand the directory
                        self.expanded_dirs.add(item_str)
                        
                        # Process recursively, but with a try/except to handle permission errors
                        try:
                            self._recursively_include(item)
                        except (PermissionError, OSError):
                            # If we can't access the directory, just mark it as selected
                            pass
            except (PermissionError, OSError):
                # If we can't access the directory, just mark it as selected
                pass
                
            # Mark directory structure as dirty to force rescan
            self.dirty_scan = True
        except Exception as e:
            # Log the error but continue
            self.status_message = f"Error including directory: {str(e)}"
    
    def _recursively_exclude(self, directory: Path) -> None:
        """Recursively exclude all files and subdirectories."""
        try:
            # First, add the directory itself to excluded items and remove from other collections
            dir_str = str(directory)
            self.excluded_items.add(dir_str)
            self.selected_items.discard(dir_str)
            self.partially_selected_items.discard(dir_str)
            
            # Process immediate children first to avoid excessive recursion
            try:
                for item in directory.iterdir():
                    item_str = str(item)
                    
                    # Add to excluded items
                    self.excluded_items.add(item_str)
                    
                    # Remove from selected and partially selected items
                    self.selected_items.discard(item_str)
                    self.partially_selected_items.discard(item_str)
                    
                    # If it's a directory, process it recursively
                    if item.is_dir():
                        # Process recursively, but with a try/except to handle permission errors
                        try:
                            self._recursively_exclude(item)
                        except (PermissionError, OSError):
                            # If we can't access the directory, just mark it as excluded
                            pass
            except (PermissionError, OSError):
                # If we can't access the directory, just mark it as excluded
                pass
                
            # Mark directory structure as dirty to force rescan
            self.dirty_scan = True
        except Exception as e:
            # Log the error but continue
            self.status_message = f"Error excluding directory: {str(e)}"
    
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
                    
                    # Use the class's common_excludes list
                    for item in items:
                        # Auto-exclude common directories but still show them in the list
                        if item.is_dir() and item.name in self.common_excludes:
                            if str(item) not in self.excluded_items:
                                self.excluded_items.add(str(item))
                        
                        # Include all files/directories in the visible list
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

        if option_name == 'respect_gitignore':
            # Toggle gitignore support
            self.options[option_name] = not self.options[option_name]

            # Reinitialize gitignore parser
            if self.options[option_name]:
                self.gitignore_parser = GitignoreParser(self.root_path)
                self.gitignore_parser.load_gitignore()
                self.status_message = "Gitignore support enabled"
            else:
                self.gitignore_parser = None
                self.status_message = "Gitignore support disabled"

            # Mark for rescan since ignore patterns changed
            self.dirty_scan = True

        elif option_name == 'format':
            # Cycle through format options
            self.options[option_name] = 'json' if self.options[option_name] == 'txt' else 'txt'
        elif option_name == 'llm_provider':
            # Cycle through LLM provider options including 'none'
            providers = list(self.options['llm_options']['providers'].keys()) + ['none']
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
        total_options = 6 + len(self.options['exclude_patterns'])  # 6 fixed options + exclude patterns
        
        new_pos = self.option_cursor + direction
        if 0 <= new_pos < total_options:
            self.option_cursor = new_pos
    
    def validate_selection(self) -> Dict[str, List[str]]:
        """Validate the selection and return statistics about selected/excluded items."""
        stats = {
            'excluded_count': len(self.excluded_items),
            'selected_count': len(self.selected_items),
            'partially_selected_count': len(self.partially_selected_items),
            'excluded_dirs': [],
            'excluded_files': [],
            'selected_dirs': [],
            'selected_files': [],
            'partially_selected_dirs': []
        }
        
        # Categorize excluded items
        for path_str in self.excluded_items:
            path = Path(path_str)
            if path.is_dir():
                stats['excluded_dirs'].append(path_str)
            else:
                stats['excluded_files'].append(path_str)
                
        # Categorize selected items
        for path_str in self.selected_items:
            path = Path(path_str)
            if path.is_dir():
                stats['selected_dirs'].append(path_str)
            else:
                stats['selected_files'].append(path_str)
                
        # Categorize partially selected items
        for path_str in self.partially_selected_items:
            path = Path(path_str)
            if path.is_dir():
                stats['partially_selected_dirs'].append(path_str)
                
        return stats
    
    def get_results(self) -> Dict[str, Any]:
        """Get the final results of the selection process."""
        # Process selection states to determine include and exclude paths
        include_paths = [Path(p) for p in self.selected_items]
        exclude_paths = [Path(p) for p in self.excluded_items]
        
        # Add partially selected directories to include_paths
        # Their children will be filtered individually
        for path_str in self.partially_selected_items:
            path = Path(path_str)
            if path not in include_paths:
                include_paths.append(path)
        
        # Validate selection and log statistics if debug is enabled
        validation_stats = self.validate_selection()
        if self.options['debug']:
            status_message = (
                f"Selection validation: {validation_stats['excluded_count']} items excluded "
                f"({len(validation_stats['excluded_dirs'])} directories, "
                f"{len(validation_stats['excluded_files'])} files), "
                f"{validation_stats['selected_count']} items explicitly included "
                f"({len(validation_stats['selected_dirs'])} directories, "
                f"{len(validation_stats['selected_files'])} files), "
                f"{validation_stats['partially_selected_count']} items partially selected"
            )
            self.status_message = status_message
            print(status_message)
        
        # Save state for future runs
        if not self.cancelled:
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
            'open_in_llm': self.options['llm_provider'],
            'llm_options': self.options['llm_options'],
            'validation': validation_stats if self.options['debug'] else None,
            'cancelled': self.cancelled
        }
        
    def _check_for_updates(self) -> None:
        """Check if a newer version is available."""
        try:
            from llm_code_lens.version import check_for_newer_version, _get_current_version, _get_latest_version
            
            # Get current and latest versions
            self.current_version = _get_current_version()
            self.latest_version, _ = _get_latest_version()
            
            if self.latest_version and self.current_version:
                # Compare versions
                if self.latest_version != self.current_version:
                    self.new_version_available = True
                    self.update_message = f"New version available: {self.latest_version} (current: {self.current_version})"
                    self.show_update_dialog = True
        except Exception as e:
            # Silently fail if version check fails
            self.update_message = f"Failed to check for updates: {str(e)}"
    
    def update_to_latest_version(self) -> None:
        """Update to the latest version."""
        self.update_in_progress = True
        self.update_result = "Updating..."
        
        try:
            import subprocess
            import sys
            
            # First attempt - normal upgrade
            self.update_result = "Running pip install --upgrade..."
            process = subprocess.run(
                [sys.executable, "-m", "pip", "install", "--upgrade", "llm-code-lens"],
                capture_output=True,
                text=True,
                check=False
            )
            
            if process.returncode != 0:
                # If first attempt failed, try with --no-cache-dir
                self.update_result = "First attempt failed. Trying with --no-cache-dir..."
                process = subprocess.run(
                    [sys.executable, "-m", "pip", "install", "--upgrade", "--no-cache-dir", "llm-code-lens"],
                    capture_output=True,
                    text=True,
                    check=False
                )
            
            if process.returncode == 0:
                self.update_result = f"Successfully updated to version {self.latest_version}. Please restart LLM Code Lens."
                # Hide the dialog after successful update
                self.show_update_dialog = False
            else:
                self.update_result = f"Update failed: {process.stderr}"
        except Exception as e:
            self.update_result = f"Update failed: {str(e)}"
        finally:
            self.update_in_progress = False
            
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
                'selected_items': list(self.selected_items),
                'partially_selected_items': list(self.partially_selected_items),
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
                self.selected_items = set(state.get('selected_items', []))
                self.partially_selected_items = set(state.get('partially_selected_items', []))
                
                # Restore options if available
                if 'options' in state:
                    for key, value in state['options'].items():
                        if key in self.options:
                            self.options[key] = value
                
                # Set status message to indicate loaded state
                excluded_count = len(self.excluded_items)
                partially_selected_count = len(self.partially_selected_items)
                if excluded_count > 0 or partially_selected_count > 0:
                    self.status_message = f"Loaded {excluded_count} excluded items and {partially_selected_count} partially selected items from saved state"
        except Exception as e:
            # Log the error instead of silently failing
            self.status_message = f"Error loading menu state: {str(e)}"
            
    def _open_in_llm(self) -> bool:
        """
        Open selected files in the configured LLM provider.
        
        Returns:
            bool: True if successful, False otherwise
        """
        # Get the provider name
        provider = self.options['llm_provider']
        
        # Handle 'none' option
        if provider.lower() == 'none':
            self.status_message = "LLM integration is disabled (set to 'none')"
            return True
            
        # Get the current item
        current_item = self.get_current_item()
        if not current_item or not current_item.is_file():
            self.status_message = "Please select a file to open in LLM"
            return False
            
        # Check if file exists and is readable
        if not current_item.exists() or not os.access(current_item, os.R_OK):
            self.status_message = f"Cannot read file: {current_item}"
            return False
        
        # Show a message that this feature is not yet implemented
        self.status_message = f"Opening in {provider} is not yet implemented"
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
    
    # If scanning is in progress, show a progress screen
    if state.scanning_in_progress:
        stdscr.clear()
        
        # Draw header
        header = " LLM Code Lens - Scanning Repository "
        header = header.center(max_x-1, "=")
        try:
            stdscr.addstr(0, 0, header[:max_x-1], curses.color_pair(1))
        except curses.error:
            pass
        
        # Calculate progress percentage
        progress_pct = min(100, int((state.scan_progress / max(1, state.scan_total)) * 100))
        
        # Show status message with better formatting
        try:
            # Status message with timestamp
            import time
            timestamp = time.strftime("%H:%M:%S")
            status_line = f"Status [{timestamp}]: {state.status_message}"
            stdscr.addstr(3, 2, status_line)
            
            # Show current directory with better formatting
            current_dir = state.scan_current_dir
            if len(current_dir) > max_x - 20:
                current_dir = "..." + current_dir[-(max_x - 23):]
            
            # Show directory with highlight
            stdscr.addstr(5, 2, "Current directory: ")
            stdscr.addstr(5, 20, current_dir, curses.color_pair(5) | curses.A_BOLD)
            
            # Show scan statistics
            stdscr.addstr(6, 2, f"Directories found: {state.scan_total}")
            stdscr.addstr(6, 30, f"Processed: {state.scan_progress}")
            
            # Draw progress bar with better visual feedback
            bar_width = max_x - 20
            filled_width = int((bar_width * progress_pct) / 100)
            
            # Use different colors for different progress levels
            bar_color = curses.color_pair(3)  # Default green
            if progress_pct < 25:
                bar_color = curses.color_pair(4)  # Red for early progress
            elif progress_pct < 50:
                bar_color = curses.color_pair(5)  # Yellow for mid progress
            
            # Draw progress percentage
            stdscr.addstr(8, 2, f"Progress: {progress_pct}% ")
            
            # Draw progress bar background
            stdscr.addstr(8, 15, "[" + " " * bar_width + "]")
            
            # Draw filled portion of progress bar
            if filled_width > 0:
                stdscr.addstr(8, 16, "=" * filled_width, bar_color | curses.A_BOLD)
            
            # Show cancel instruction with highlight
            stdscr.addstr(10, 2, "Press ", curses.A_BOLD)
            stdscr.addstr(10, 8, "ESC", curses.color_pair(7) | curses.A_BOLD)
            stdscr.addstr(10, 12, " to cancel scanning", curses.A_BOLD)
            
            # Add more helpful information
            stdscr.addstr(12, 2, "Scanning large repositories may take some time...")
            stdscr.addstr(13, 2, "This helps optimize the analysis by excluding irrelevant files.")
            
            # Add animation to show activity even when progress doesn't change
            import time
            animation_chars = "|/-\\"
            animation_idx = int(time.time() * 5) % len(animation_chars)
            stdscr.addstr(15, 2, f"Working {animation_chars[animation_idx]}")
        except curses.error:
            pass
        
        # Draw footer
        footer_y = max_y - 2
        footer = " Please wait while we prepare your repository for analysis... "
        footer = footer.center(max_x-1, "=")
        try:
            stdscr.addstr(footer_y, 0, footer[:max_x-1], curses.color_pair(1))
        except curses.error:
            pass
        
        stdscr.refresh()
        return
    
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
    
    # Draw section indicator with improved visibility
    section_y = 1
    files_section = " [F]iles "
    options_section = " [O]ptions "
    tab_hint = " [Tab] to switch sections "
    esc_hint = " [Esc] to cancel "
    
    try:
        # Files section indicator with better highlighting
        attr = curses.color_pair(7) if state.active_section == 'files' else curses.color_pair(1)
        stdscr.addstr(section_y, 2, files_section, attr)
        
        # Options section indicator
        attr = curses.color_pair(7) if state.active_section == 'options' else curses.color_pair(1)
        stdscr.addstr(section_y, 2 + len(files_section) + 2, options_section, attr)
        
        # Add Tab hint in the middle
        middle_pos = max_x // 2 - len(tab_hint) // 2
        stdscr.addstr(section_y, middle_pos, tab_hint, curses.color_pair(6))
        
        # Add Escape hint on the right
        right_pos = max_x - len(esc_hint) - 2
        stdscr.addstr(section_y, right_pos, esc_hint, curses.color_pair(6))
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
            
            # Determine selection indicator based on exclusion/selection status
            path_str = str(path)
            if path_str in state.selected_items:
                sel_indicator = "[*]"  # Explicitly selected
            elif path_str in state.partially_selected_items:
                sel_indicator = "[~]"  # Partially selected
            elif is_excluded:
                sel_indicator = "[-]"  # Excluded
            else:
                sel_indicator = "[+]"  # Included
                
            item_str = f"{indent}{prefix}{sel_indicator} {path.name}"
            
            # Truncate if too long
            if len(item_str) > max_x - 2:
                item_str = item_str[:max_x - 5] + "..."
                
            # Determine color
            path_str = str(path)
            if state.active_section == 'files' and idx == state.cursor_pos:
                attr = curses.color_pair(2)  # Highlighted
            elif path_str in state.selected_items:
                attr = curses.color_pair(3) | curses.A_BOLD  # Explicitly selected (bold)
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
            ("LLM Provider", f"{state.options['llm_provider']}", "F6"),
            ("Respect .gitignore", f"{state.options['respect_gitignore']}", "F7")  # NEW OPTION
        ]
        
        # Add exclude patterns
        for i, pattern in enumerate(state.options['exclude_patterns']):
            options.append((f"Exclude Pattern {i+1}", pattern, "Del"))
        
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
    
    # Draw update dialog if needed
    if state.show_update_dialog:
        # Calculate dialog dimensions and position
        dialog_width = 60
        dialog_height = 8
        dialog_x = max(0, (max_x - dialog_width) // 2)
        dialog_y = max(0, (max_y - dialog_height) // 2)
        
        # Draw dialog box
        for y in range(dialog_height):
            try:
                if y == 0 or y == dialog_height - 1:
                    # Draw top and bottom borders
                    stdscr.addstr(dialog_y + y, dialog_x, "+" + "-" * (dialog_width - 2) + "+")
                else:
                    # Draw side borders
                    stdscr.addstr(dialog_y + y, dialog_x, "|" + " " * (dialog_width - 2) + "|")
            except curses.error:
                pass
        
        # Draw dialog title
        title = " Update Available "
        title_x = dialog_x + (dialog_width - len(title)) // 2
        try:
            stdscr.addstr(dialog_y, title_x, title, curses.color_pair(1) | curses.A_BOLD)
        except curses.error:
            pass
        
        # Draw update message
        message_lines = [
            state.update_message,
            "",
            "Do you want to update now?",
            "",
            "[Y] Yes   [N] No"
        ]
        
        if state.update_in_progress:
            message_lines = [state.update_result, "", "Updating, please wait..."]
        elif state.update_result:
            message_lines = [state.update_result, "", "[Enter] Continue"]
        
        for i, line in enumerate(message_lines):
            if i < dialog_height - 2:  # Ensure we don't draw outside the dialog
                line_x = dialog_x + (dialog_width - len(line)) // 2
                try:
                    stdscr.addstr(dialog_y + i + 1, line_x, line)
                except curses.error:
                    pass
    
    # Draw footer with improved controls
    footer_y = max_y - 2
    
    if state.editing_option:
        # Show editing controls
        controls = " Enter: Confirm | Esc: Cancel "
    elif state.active_section == 'files':
        # Show file navigation controls with better organization
        controls = " ↑/↓: Navigate | →: Expand | ←: Collapse | Space: Select | Tab: Switch to Options | Enter: Confirm | Esc: Cancel "
        if state.new_version_available:
            controls = " F8: Update | " + controls
    else:
        # Show options controls
        controls = " ↑/↓: Navigate | Space: Toggle/Edit | Tab: Switch to Files | Enter: Confirm | Esc: Cancel "
        if state.new_version_available:
            controls = " F8: Update | " + controls
        
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
                selected_count = len(state.selected_items)
                if excluded_count > 0 and selected_count > 0:
                    status = f" {excluded_count} items excluded, {selected_count} explicitly included | Space: Toggle selection (recursive for directories) | Enter: Confirm "
                elif excluded_count > 0:
                    status = f" {excluded_count} items excluded | Space: Toggle selection (recursive for directories) | Enter: Confirm "
                elif selected_count > 0:
                    status = f" {selected_count} items explicitly included | Space: Toggle selection (recursive for directories) | Enter: Confirm "
                else:
                    status = " All files included by default | Space: Toggle selection (recursive for directories) | Enter: Confirm "
            else:
                status = " Use Space to toggle options or edit text fields | Enter: Confirm "
        
        # Add version info if available
        if state.current_version:
            version_info = f"v{state.current_version}"
            if state.new_version_available:
                version_info += f" (New: v{state.latest_version} available! Press F8 to update)"
            
            # Add version info to status if there's room
            if len(status) + len(version_info) + 3 < max_x:
                padding = max_x - len(status) - len(version_info) - 3
                status += " " * padding + version_info + " "
                
        status = status.ljust(max_x-1)
        try:
            stdscr.addstr(status_y, 0, status[:max_x-1])
        except curses.error:
            pass
    
    stdscr.refresh()


def handle_input(key: int, state: MenuState) -> bool:
    """Handle user input. Returns True if user wants to exit."""
    # Handle update dialog first
    if state.show_update_dialog:
        if state.update_in_progress:
            # Don't handle input during update
            return False
        
        if state.update_result:
            # After update is complete, any key dismisses the dialog
            if key == 10 or key == 27:  # Enter or Escape
                state.show_update_dialog = False
                state.update_result = ""
            return False
        
        # Handle update dialog inputs
        if key == ord('y') or key == ord('Y'):
            # Start the update process
            state.update_to_latest_version()
            return False
        elif key == ord('n') or key == ord('N') or key == 27:  # 'n', 'N', or Escape
            # Dismiss the dialog
            state.show_update_dialog = False
            return False
        return False
        
    # Handle scanning cancellation
    if state.scanning_in_progress:
        if key == 27:  # ESC key
            state.cancel_scan_requested = True
            state.status_message = "Cancelling scan..."
            # Don't exit the menu, just cancel the scan
            return False
        # Ignore all other input during scanning
        return False
        
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
    if key == 27:  # Escape key
        # Cancel and exit
        state.cancelled = True
        state.status_message = "Operation cancelled by user"
        return True
    elif key == 9:  # Tab key
        state.toggle_section()
    elif key == 10:  # Enter key
        # Confirm selection and exit
        return True
    elif key == ord('q'):
        # Quit without saving
        state.cancelled = True
        state.status_message = "Operation cancelled by user"
        return True
    elif key == ord('f') or key == ord('F'):
        state.active_section = 'files'
    elif key == ord('o') or key == ord('O'):
        state.active_section = 'options'
    # Removed Ctrl+Space shortcut as Space now does full selection
        
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
            # Full select with all sub-elements
            state.toggle_selection(current_item, fully_select=True)
    
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
                state.toggle_option('llm_provider')
            elif option_index == 6:  # Respect .gitignore
                state.toggle_option('respect_gitignore')
            elif option_index >= 7 and option_index < 7 + len(state.options['exclude_patterns']):
                # Remove exclude pattern
                pattern_index = option_index - 7
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
        # Cycle through available LLM providers including 'none'
        providers = list(state.options['llm_options']['providers'].keys()) + ['none']
        current_index = providers.index(state.options['llm_provider']) if state.options['llm_provider'] in providers else 0
        next_index = (current_index + 1) % len(providers)
        state.options['llm_provider'] = providers[next_index]
        state.status_message = f"LLM Provider set to: {state.options['llm_provider']}"
    elif key == curses.KEY_F7:
        # Toggle gitignore respect
        state.toggle_option('respect_gitignore')
    elif key == curses.KEY_F8:
        # Show update dialog if updates are available
        if state.new_version_available:
            state.show_update_dialog = True
    elif key == curses.KEY_DC:  # Delete key
        if state.active_section == 'options' and state.option_cursor >= 6 and state.option_cursor < 6 + len(state.options['exclude_patterns']):
            pattern_index = state.option_cursor - 6
            state.remove_exclude_pattern(pattern_index)
    # Insert key handling removed
        
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
        
        # Initialize menu state with initial settings
        state = MenuState(path, initial_settings)
        state.expanded_dirs.add(str(path))  # Start with root expanded
        
        # Set a shorter timeout for responsive UI updates during scanning
        stdscr.timeout(50)  # Even shorter timeout for more responsive UI
        
        # Initial scan phase - block UI until complete or cancelled
        state.scanning_in_progress = True
        state.dirty_scan = True
        
        # Start the scan in a separate thread to keep UI responsive
        import threading
        
        def perform_scan():
            try:
                state._auto_exclude_common_dirs()
                if not state.cancel_scan_requested:
                    state.rebuild_visible_items()
                    state._load_state()
                state.scanning_in_progress = False
            except Exception as e:
                state.status_message = f"Error during scan: {str(e)}"
                state.scanning_in_progress = False
        
        # Start the scan thread
        scan_thread = threading.Thread(target=perform_scan)
        scan_thread.daemon = True
        scan_thread.start()
        
        # Main loop
        while True:
            # Draw the menu (will show scanning screen if scanning_in_progress is True)
            draw_menu(stdscr, state)
            
            # Handle input with shorter timeout during scanning
            try:
                if state.scanning_in_progress:
                    # Use a very short timeout during scanning for responsive UI
                    stdscr.timeout(50)
                else:
                    # Use a longer timeout when not scanning
                    stdscr.timeout(-1)
                
                key = stdscr.getch()
                
                # Handle ESC key during scanning
                if state.scanning_in_progress and key == 27:  # ESC key
                    state.cancel_scan_requested = True
                    state.status_message = "Cancelling scan..."
                    # Don't exit, just wait for scan to complete
                    continue
                
                # Skip other input processing during scanning
                if state.scanning_in_progress:
                    continue
            
                # Normal input handling when not scanning
                if handle_input(key, state):
                    break
            except KeyboardInterrupt:
                # Handle Ctrl+C
                if state.scanning_in_progress:
                    state.cancel_scan_requested = True
                    state.status_message = "Cancelling scan..."
                else:
                    state.cancelled = True
                    break
        
        # If scan thread is still running, wait for it to finish
        if scan_thread.is_alive():
            state.cancel_scan_requested = True
            scan_thread.join(timeout=1.0)  # Wait up to 1 second
        
        return state.get_results()
    
    # Use curses wrapper to handle terminal setup/cleanup
    try:
        return curses.wrapper(_menu_main)
    except Exception as e:
        # Fallback if curses fails
        print(f"Error in menu: {str(e)}")
        return {'path': path, 'include_paths': [], 'exclude_paths': []}
