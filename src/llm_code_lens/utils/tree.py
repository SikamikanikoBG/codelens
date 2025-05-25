"""
Project tree structure generator.
Creates ASCII tree visualization of project structure.
"""

from pathlib import Path
from typing import List, Set, Dict
import os

class ProjectTree:
    """Generates ASCII tree structure for projects."""

    def __init__(self, ignore_patterns: List[str] = None, max_depth: int = 5):
        self.ignore_patterns = ignore_patterns or []
        self.max_depth = max_depth
        self.tree_chars = {
            'pipe': '│   ',
            'tee': '├── ',
            'last': '└── ',
            'blank': '    '
        }

    def generate_tree(self, root_path: Path, excluded_paths: Set[str] = None) -> str:
        """Generate ASCII tree structure."""
        excluded_paths = excluded_paths or set()

        tree_lines = [f"{root_path.name}/"]
        self._build_tree_recursive(
            root_path,
            tree_lines,
            "",
            excluded_paths,
            depth=0
        )

        return "\n".join(tree_lines)

    def _build_tree_recursive(self, path: Path, tree_lines: List[str], prefix: str,
                            excluded_paths: Set[str], depth: int) -> None:
        """Recursively build tree structure."""

        if depth >= self.max_depth:
            return

        try:
            # Get all items in directory
            items = list(path.iterdir())

            # Filter out ignored items
            items = [item for item in items if not self._should_ignore(item, excluded_paths)]

            # Sort directories first, then files
            items.sort(key=lambda x: (not x.is_dir(), x.name.lower()))

            # Process each item
            for i, item in enumerate(items):
                is_last = i == len(items) - 1

                # Choose tree characters
                current_prefix = self.tree_chars['last'] if is_last else self.tree_chars['tee']
                next_prefix = prefix + (self.tree_chars['blank'] if is_last else self.tree_chars['pipe'])

                # Add item to tree
                item_name = item.name
                if item.is_dir():
                    item_name += "/"

                tree_lines.append(f"{prefix}{current_prefix}{item_name}")

                # Recurse into directories
                if item.is_dir() and depth < self.max_depth - 1:
                    self._build_tree_recursive(item, tree_lines, next_prefix, excluded_paths, depth + 1)

        except PermissionError:
            # Handle permission errors gracefully
            tree_lines.append(f"{prefix}{self.tree_chars['last']}[Permission Denied]")

    def _should_ignore(self, path: Path, excluded_paths: Set[str]) -> bool:
        """Check if path should be ignored."""
        path_str = str(path)

        # Check explicit exclusions
        if path_str in excluded_paths:
            return True

        # Check ignore patterns
        from ..cli import should_ignore
        return should_ignore(path, self.ignore_patterns)

    def generate_summary_tree(self, root_path: Path, excluded_paths: Set[str] = None) -> str:
        """Generate a summary tree showing only key directories and file counts."""
        excluded_paths = excluded_paths or set()

        structure = self._analyze_structure(root_path, excluded_paths)

        summary_lines = [f"{root_path.name}/ ({structure['total_files']} files, {structure['total_dirs']} directories)"]

        for dir_name, info in sorted(structure['directories'].items()):
            file_count = info['file_count']
            subdir_count = info['subdir_count']
            summary_lines.append(f" {dir_name}/ ({file_count} files, {subdir_count} subdirs)")

        # Show file type distribution
        if structure['file_types']:
            summary_lines.append(" File types:")
            for ext, count in sorted(structure['file_types'].items()):
                summary_lines.append(f"     {ext}: {count} files")

        return "\n".join(summary_lines)

    def _analyze_structure(self, root_path: Path, excluded_paths: Set[str]) -> Dict:
        """Analyze project structure for summary."""
        structure = {
            'total_files': 0,
            'total_dirs': 0,
            'directories': {},
            'file_types': {}
        }

        for item in root_path.rglob('*'):
            if self._should_ignore(item, excluded_paths):
                continue

            if item.is_file():
                structure['total_files'] += 1

                # Count file types
                ext = item.suffix.lower() or 'no extension'
                structure['file_types'][ext] = structure['file_types'].get(ext, 0) + 1

            elif item.is_dir():
                structure['total_dirs'] += 1

                # Analyze immediate subdirectories of root
                if item.parent == root_path:
                    dir_info = self._analyze_directory(item, excluded_paths)
                    structure['directories'][item.name] = dir_info

        return structure

    def _analyze_directory(self, dir_path: Path, excluded_paths: Set[str]) -> Dict:
        """Analyze a single directory."""
        file_count = 0
        subdir_count = 0

        try:
            for item in dir_path.rglob('*'):
                if self._should_ignore(item, excluded_paths):
                    continue

                if item.is_file():
                    file_count += 1
                elif item.is_dir() and item != dir_path:
                    subdir_count += 1
        except PermissionError:
            pass

        return {
            'file_count': file_count,
            'subdir_count': subdir_count
        }
