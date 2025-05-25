"""
Gitignore Parser Utility Module
Handles parsing and applying .gitignore patterns.
"""

from pathlib import Path
import re
from typing import List, Optional

class GitignoreParser:
    """
    Parses .gitignore files and provides methods to check if a file should be ignored.

    Attributes:
        root_path (Path): The root directory where the .gitignore file is located.
        patterns (List[str]): List of ignore patterns parsed from .gitignore.
    """

    def __init__(self, root_path: Path):
        """Initialize with the root path containing .gitignore."""
        self.root_path = root_path
        self.patterns = []

    def load_gitignore(self) -> None:
        """
        Load and parse the .gitignore file from the root directory.
        This method populates the patterns list.
        """
        gitignore_path = self.root_path / '.gitignore'

        if not gitignore_path.exists():
            return

        try:
            with open(gitignore_path, 'r') as f:
                for line in f:
                    # Skip empty lines and comments
                    line = line.strip()
                    if line and not line.startswith('#'):
                        self.patterns.append(line)
        except Exception as e:
            print(f"Warning: Error reading {gitignore_path}: {e}")

    def get_ignore_patterns(self) -> List[str]:
        """
        Get the list of ignore patterns.

        Returns:
            List[str]: List of ignore patterns.
        """
        return self.patterns

    def should_ignore(self, path: Path) -> bool:
        """
        Check if a file or directory matches any of the .gitignore patterns.

        Args:
            path (Path): The file or directory to check.

        Returns:
            bool: True if the path should be ignored, False otherwise.
        """
        path_str = str(path.relative_to(self.root_path))

        for pattern in self.patterns:
            # Convert gitignore pattern to regex
            regex_pattern = self._convert_to_regex(pattern)

            # Check if the path matches the pattern
            if re.search(regex_pattern, path_str):
                return True

        return False

    def _convert_to_regex(self, pattern: str) -> str:
        """
        Convert a gitignore pattern to a regular expression.

        Args:
            pattern (str): The gitignore pattern.

        Returns:
            str: The equivalent regular expression.
        """
        # Escape special regex characters in the pattern
        escaped_pattern = re.escape(pattern)

        # Handle wildcards and special patterns
        escaped_pattern = (
            escaped_pattern.replace(r'\*', '.*')  # * -> .*
            .replace(r'\?', '.')                  # ? -> .
            .replace(r'\[', '[')                  # [ -> [
            .replace(r'\]', ']')                  # ] -> ]
        )

        # Handle directory-specific patterns
        if pattern.endswith('/'):
            escaped_pattern += '/'
        elif not pattern.startswith('/'):
            # If the pattern doesn't start with a slash, it's relative to the current directory
            escaped_pattern = f'.*{escaped_pattern}'

        return escaped_pattern
