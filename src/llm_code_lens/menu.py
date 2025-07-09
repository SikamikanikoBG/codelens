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
        self.selected_items: Set[str] = set()  # Simple binary selection: selected or not
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

        self.status_message = "Ready"

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
            'verbose': False,          # Enable verbose debug output
            'sql_server': '',          # SQL Server connection string
            'sql_database': '',        # SQL Database to analyze
            'sql_config': '',          # Path to SQL configuration file
            'exclude_patterns': [],    # Patterns to exclude
            'llm_provider': 'claude',  # Default LLM provider
            'custom_llm_url': '',      # Custom LLM URL
            'respect_gitignore': True, # Respect .gitignore patterns
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
                    'custom': {
                        'url': '',
                        'model': 'custom',
                        'temperature': 0.7,
                        'max_tokens': 4000
                    }
                },
                'available_providers': ['claude', 'chatgpt', 'gemini', 'custom', 'none'],
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
                    # Migration: convert 'local' to 'custom' for backward compatibility
                    if key == 'llm_provider' and value == 'local':
                        value = 'custom'
                    self.options[key] = value

        # UI state
        self.active_section = 'files'  # Current active section: 'files' or 'options'
        self.option_cursor = 0         # Cursor position in options section
        self.editing_option = None     # Currently editing option (for text input)
        self.edit_buffer = ""          # Buffer for text input

        # Simple initialization - just build the initial visible items
        # Make sure root is expanded by default so we can see files
        self.expanded_dirs.add(str(self.root_path))
        self.rebuild_visible_items()

        # Load saved state first, then auto-select if no saved state exists
        state_loaded = self._load_state()

        # Debug: Check if we have legacy 'local' provider
        if self.options['llm_provider'] == 'local':
            print(f"DEBUG: Found legacy 'local' provider, converting to 'custom'")
            self.options['llm_provider'] = 'custom'

        if not state_loaded:
            # No saved state - auto-select all non-ignored files and folders
            self._auto_select_files()

    def toggle_dir_expanded(self, path: Path) -> None:
        """Toggle directory expansion state."""
        path_str = str(path)
        if path_str in self.expanded_dirs:
            self.expanded_dirs.remove(path_str)
        else:
            self.expanded_dirs.add(path_str)
        self.rebuild_visible_items()

    def toggle_selection(self, path: Path) -> None:
        """Simple Norton Commander style selection toggle."""
        path_str = str(path)

        if path_str in self.selected_items:
            self.selected_items.remove(path_str)
            self.status_message = f"Deselected: {path.name}"
        else:
            self.selected_items.add(path_str)
            self.status_message = f"Selected: {path.name}"

    def is_selected(self, path: Path) -> bool:
        """Check if a path is selected."""
        return str(path) in self.selected_items

    def is_excluded(self, path: Path) -> bool:
        """Check if a path should be excluded by default (common directories)."""
        # Check gitignore first if enabled
        if self.gitignore_parser and self.gitignore_parser.should_ignore(path):
            return True

        # Check if it's a common exclude directory
        if path.is_dir() and path.name in self.common_excludes:
            return True

        # Check if parent is a common exclude directory
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
        """Fast rebuild of visible items - Norton Commander style."""
        self.visible_items = []
        self._build_item_list(self.root_path, 0)

        # Adjust cursor position if it's now out of bounds
        if self.cursor_pos >= len(self.visible_items) and len(self.visible_items) > 0:
            self.cursor_pos = len(self.visible_items) - 1

    def _build_item_list(self, path: Path, depth: int) -> None:
        """Fast build of visible items - Norton Commander style."""
        # Add the current path to visible items (including root for navigation)
        self.visible_items.append((path, depth))

        # If it's a directory and it's expanded, add its children
        if path.is_dir() and str(path) in self.expanded_dirs:
            try:
                # Sort directories first, then files
                items = sorted(path.iterdir(),
                              key=lambda p: (0 if p.is_dir() else 1, p.name.lower()))

                for item in items:
                    # Skip items that should be ignored
                    if not self.is_excluded(item):
                        self._build_item_list(item, depth + 1)
            except (PermissionError, OSError):
                # Silently handle permission errors in TUI mode
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

            # Handle legacy 'local' provider
            current_provider = self.options[option_name]
            if current_provider == 'local':
                current_provider = 'custom'
                self.options[option_name] = 'custom'

            current_index = providers.index(current_provider) if current_provider in providers else 0
            next_index = (current_index + 1) % len(providers)
            self.options[option_name] = providers[next_index]

            # If switching to custom, prompt for URL if not set
            if self.options[option_name] == 'custom' and not self.options['custom_llm_url']:
                self.start_editing_option('custom_llm_url')

            # Update the custom provider URL in llm_options
            if self.options[option_name] == 'custom':
                self.options['llm_options']['providers']['custom']['url'] = self.options['custom_llm_url']

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

                # Special handling for custom_llm_url - sync with providers
                if self.editing_option == 'custom_llm_url':
                    self.options['llm_options']['providers']['custom']['url'] = self.edit_buffer
                    # Auto-switch to custom provider if URL is set
                    if self.edit_buffer.strip():
                        self.options['llm_provider'] = 'custom'
                        self.status_message = f"Custom LLM URL set to: {self.edit_buffer} (Provider switched to custom)"

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
        total_options = 9 + len(self.options['exclude_patterns'])  # 9 fixed options + exclude patterns

        new_pos = self.option_cursor + direction
        if 0 <= new_pos < total_options:
            self.option_cursor = new_pos

    def validate_selection(self) -> Dict[str, List[str]]:
        """Simple selection validation - Norton Commander style."""
        stats = {
            'selected_count': len(self.selected_items),
            'selected_dirs': [],
            'selected_files': []
        }

        for path_str in self.selected_items:
            path = Path(path_str)
            if path.is_dir():
                stats['selected_dirs'].append(path_str)
            else:
                stats['selected_files'].append(path_str)

        return stats

    def get_results(self) -> Dict[str, Any]:
        """Get the final results - simple Norton Commander style."""
        # Simple approach: if items are selected, use only those
        # Otherwise, include everything except common excludes
        if self.selected_items:
            include_paths = [Path(p) for p in self.selected_items]
            exclude_paths = []
        else:
            include_paths = [self.root_path]
            exclude_paths = []

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
            'verbose': self.options['verbose'],
            'sql_server': self.options['sql_server'],
            'sql_database': self.options['sql_database'],
            'sql_config': self.options['sql_config'],
            'exclude': self.options['exclude_patterns'],
            'open_in_llm': self.options['llm_provider'],
            'custom_llm_url': self.options['custom_llm_url'],
            'llm_options': self.options['llm_options'],
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

    def _auto_select_files(self) -> None:
        """Auto-select relevant code files and important folders that are not ignored by gitignore or common excludes."""
        selected_count = 0

        # Define relevant code file extensions
        code_extensions = {
            '.py', '.js', '.jsx', '.ts', '.tsx', '.vue', '.svelte',  # Frontend/Python
            '.java', '.kt', '.scala', '.groovy',  # JVM languages
            '.c', '.cpp', '.cc', '.cxx', '.h', '.hpp',  # C/C++
            '.cs', '.vb', '.fs',  # .NET languages
            '.go', '.rs', '.rb', '.php', '.swift', '.m', '.mm',  # Other languages
            '.sql', '.graphql', '.proto',  # Data/API
            '.html', '.css', '.scss', '.sass', '.less', '.styl',  # Web
            '.json', '.yaml', '.yml', '.toml', '.xml', '.ini', '.cfg', '.conf',  # Config
            '.md', '.rst', '.txt',  # Documentation
            '.sh', '.bash', '.zsh', '.ps1', '.bat', '.cmd',  # Scripts
            '.dockerfile', '.makefile', '.gradle', '.cmake'  # Build files
        }

        # Important directories that should be included (if they exist and aren't excluded)
        important_dirs = {
            'src', 'lib', 'components', 'pages', 'utils', 'helpers', 'services',
            'api', 'models', 'views', 'controllers', 'routes', 'middleware',
            'config', 'scripts', 'tests', 'test', 'spec', 'docs', 'documentation'
        }

        try:
            # Walk through all files and directories
            for root, dirs, files in os.walk(self.root_path):
                root_path = Path(root)

                # Skip deep nesting (more than 5 levels deep to avoid selecting too much)
                relative_depth = len(root_path.relative_to(self.root_path).parts)
                if relative_depth > 5:
                    dirs.clear()  # Don't recurse deeper
                    continue

                # Process directories - be selective about which ones to include
                for dir_name in dirs[:]:  # Use slice copy to allow modification during iteration
                    dir_path = root_path / dir_name

                    # Skip if this directory should be excluded
                    if self.is_excluded(dir_path):
                        dirs.remove(dir_name)  # Don't recurse into excluded directories
                        continue

                    # Only auto-select directories that are important or at root level
                    should_select_dir = (
                        relative_depth == 0 or  # Root level directories
                        dir_name.lower() in important_dirs or  # Important directory names
                        any(dir_name.lower().startswith(prefix) for prefix in ['src', 'lib', 'app', 'web'])  # Common prefixes
                    )

                    if should_select_dir:
                        self.selected_items.add(str(dir_path))
                        selected_count += 1

                # Process files - only select relevant code files
                for file_name in files:
                    file_path = root_path / file_name

                    # Skip if this file should be excluded
                    if self.is_excluded(file_path):
                        continue

                    # Check if it's a relevant code file
                    file_ext = file_path.suffix.lower()
                    is_relevant_file = (
                        file_ext in code_extensions or
                        file_name.lower() in {
                            'readme', 'readme.md', 'readme.txt', 'license', 'license.txt',
                            'package.json', 'package-lock.json', 'yarn.lock', 'pnpm-lock.yaml',
                            'requirements.txt', 'setup.py', 'pyproject.toml', 'pipfile', 'poetry.lock',
                            'dockerfile', 'docker-compose.yml', 'docker-compose.yaml',
                            'makefile', 'cmake', 'build.gradle', 'pom.xml', 'cargo.toml',
                            '.gitignore', '.env.example', '.env.template'
                        } or
                        any(file_name.lower().startswith(prefix) for prefix in ['readme', 'license', 'changelog', 'contributing'])
                    )

                    if is_relevant_file:
                        self.selected_items.add(str(file_path))
                        selected_count += 1

            # Update status message
            if selected_count > 0:
                self.status_message = f"Auto-selected {selected_count} relevant files and folders (excluding ignored items)"
            else:
                self.status_message = "No relevant files found to auto-select"

        except Exception as e:
            self.status_message = f"Error during auto-selection: {str(e)}"

    def _save_state(self) -> None:
        """Save the current state to a file."""
        try:
            state_dir = self.root_path / '.codelens'
            state_dir.mkdir(exist_ok=True)
            state_file = state_dir / 'menu_state.json'

            # Enhanced state - expanded dirs, selected items, and metadata
            state = {
                'expanded_dirs': list(self.expanded_dirs),
                'selected_items': list(self.selected_items),
                'options': self.options,
                'auto_selected': True,  # Mark that we have performed auto-selection
                'version': '1.0'  # State format version for future compatibility
            }

            import json
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
        except Exception as e:
            # Use status message instead of print in TUI mode
            self.status_message = f"Error saving menu state: {str(e)}"

    def _load_state(self) -> bool:
        """Load the saved state from a file. Returns True if state was loaded successfully."""
        try:
            state_file = self.root_path / '.codelens' / 'menu_state.json'
            if state_file.exists():
                import json
                with open(state_file, 'r') as f:
                    state = json.load(f)

                # Restore simple state
                self.expanded_dirs = set(state.get('expanded_dirs', []))
                self.selected_items = set(state.get('selected_items', []))

                # Restore options if available
                if 'options' in state:
                    for key, value in state['options'].items():
                        if key in self.options:
                            # Migration: convert 'local' to 'custom' for backward compatibility
                            if key == 'llm_provider' and value == 'local':
                                value = 'custom'
                            self.options[key] = value

                # Set status message to indicate loaded state
                selected_count = len(self.selected_items)
                if selected_count > 0:
                    self.status_message = f"Loaded {selected_count} selected items from saved state"
                return True
        except Exception as e:
            self.status_message = f"Error loading menu state: {str(e)}"
        return False

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

            # Prepare the display string - simplified folder states
            indent = "  " * depth
            if is_dir:
                prefix = "- " if str(path) in state.expanded_dirs else "+ "
            else:
                prefix = "  "

            # Simple Norton Commander style display
            path_str = str(path)
            is_selected = path_str in state.selected_items

            if is_selected:
                sel_indicator = "[*]"  # Selected
            elif is_excluded:
                sel_indicator = "[X]"  # Auto-excluded (common dirs)
            else:
                sel_indicator = "[ ]"  # Available

            item_str = f"{indent}{prefix}{sel_indicator} {path.name}"

            # Truncate if too long
            if len(item_str) > max_x - 2:
                item_str = item_str[:max_x - 5] + "..."

            # Simple color scheme
            if state.active_section == 'files' and idx == state.cursor_pos:
                attr = curses.color_pair(2)  # Highlighted
            elif is_selected:
                attr = curses.color_pair(3) | curses.A_BOLD  # Selected
            elif is_excluded:
                attr = curses.color_pair(4)  # Auto-excluded
            elif is_dir:
                attr = curses.color_pair(5)  # Directory
            else:
                attr = 0  # Default file

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
            ("Verbose Mode", f"{state.options['verbose']}", "F4"),
            ("SQL Server", f"{state.options['sql_server'] or 'Not set'}", "F5"),
            ("SQL Database", f"{state.options['sql_database'] or 'Not set'}", "F6"),
            ("LLM Provider", f"{state.options['llm_provider']}" + (" (needs URL)" if state.options['llm_provider'] == 'custom' and not state.options['custom_llm_url'] else ""), "F7"),
            ("Custom LLM URL", f"{state.options['custom_llm_url'] or 'Not set'}", "F8"),
            ("Respect .gitignore", f"{state.options['respect_gitignore']}", "F9")
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
                # Count excluded items by checking all visible items
                excluded_count = sum(1 for path, _ in state.visible_items if state.is_excluded(path))
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
            # Rebuild visible items to show expanded content
            state.visible_items = []
            state._build_item_list(state.root_path, 0)
            # Adjust cursor if needed
            if state.cursor_pos >= len(state.visible_items):
                state.cursor_pos = len(state.visible_items) - 1
        elif key == curses.KEY_LEFT and current_item and current_item.is_dir():
            # Collapse directory
            if str(current_item) in state.expanded_dirs:
                state.expanded_dirs.remove(str(current_item))
                # Rebuild visible items to hide collapsed content
                state.visible_items = []
                state._build_item_list(state.root_path, 0)
                # Adjust cursor if needed
                if state.cursor_pos >= len(state.visible_items):
                    state.cursor_pos = len(state.visible_items) - 1
            else:
                # If already collapsed, go to parent
                parent = current_item.parent
                for i, (path, _) in enumerate(state.visible_items):
                    if path == parent:
                        state.cursor_pos = i
                        break
        elif key == ord(' ') and current_item:
            # Simple Norton Commander style selection toggle
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
            elif option_index == 3:  # Verbose Mode
                state.toggle_option('verbose')
            elif option_index == 4:  # SQL Server
                state.start_editing_option('sql_server')
            elif option_index == 5:  # SQL Database
                state.start_editing_option('sql_database')
            elif option_index == 6:  # LLM Provider
                state.toggle_option('llm_provider')
            elif option_index == 7:  # Custom LLM URL
                state.start_editing_option('custom_llm_url')
            elif option_index == 8:  # Respect .gitignore
                state.toggle_option('respect_gitignore')
            elif option_index >= 9 and option_index < 9 + len(state.options['exclude_patterns']):
                # Remove exclude pattern
                pattern_index = option_index - 9
                state.remove_exclude_pattern(pattern_index)

    # Function key controls (work in any section)
    if key == curses.KEY_F1:
        state.toggle_option('format')
    elif key == curses.KEY_F2:
        state.toggle_option('full')
    elif key == curses.KEY_F3:
        state.toggle_option('debug')
    elif key == curses.KEY_F4:
        state.toggle_option('verbose')
    elif key == curses.KEY_F5:
        state.start_editing_option('sql_server')
    elif key == curses.KEY_F6:
        state.start_editing_option('sql_database')
    elif key == curses.KEY_F7:
        state.toggle_option('llm_provider')
    elif key == curses.KEY_F8:
        state.start_editing_option('custom_llm_url')
    elif key == curses.KEY_F9:
        state.toggle_option('respect_gitignore')
    elif key == curses.KEY_F10:
        # Show update dialog if updates are available
        if state.new_version_available:
            state.show_update_dialog = True
    elif key == curses.KEY_DC:  # Delete key
        if state.active_section == 'options' and state.option_cursor >= 6 and state.option_cursor < 6 + len(state.options['exclude_patterns']):
            pattern_index = state.option_cursor - 6
            state.remove_exclude_pattern(pattern_index)

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

        # Set timeout for responsive input
        stdscr.timeout(-1)

        # Main loop - simple and fast
        while True:
            draw_menu(stdscr, state)

            try:
                key = stdscr.getch()
                if handle_input(key, state):
                    break
            except KeyboardInterrupt:
                state.cancelled = True
                break

        return state.get_results()

    # Use curses wrapper to handle terminal setup/cleanup
    try:
        return curses.wrapper(_menu_main)
    except Exception as e:
        # Fallback if curses fails
        print(f"Error in menu: {str(e)}")
        return {'path': path, 'include_paths': [], 'exclude_paths': []}
