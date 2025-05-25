"""
Gitignore file parser and pattern matcher.
Handles .gitignore patterns and converts them to our ignore system.
"""

import fnmatch
import os
from pathlib import Path
from typing import List, Set

class GitignoreParser:
    """Parser for .gitignore files with pattern matching."""
    
    def __init__(self, project_root: Path):
        self.project_root = Path(project_root).resolve()
        self.patterns = []
        self.negation_patterns = []
        
    def load_gitignore(self, gitignore_path: Path = None) -> None:
        """Load patterns from .gitignore file."""
        if gitignore_path is None:
            gitignore_path = self.project_root / '.gitignore'
        
        if not gitignore_path.exists():
            return
        
        try:
            with open(gitignore_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            for line in lines:
                line = line.strip()
                
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue
                
                # Handle negation patterns (starting with !)
                if line.startswith('!'):
                    self.negation_patterns.append(line[1:])
                else:
                    self.patterns.append(line)
                    
        except Exception as e:
            print(f"Warning: Could not read .gitignore file: {e}")
    
    def should_ignore(self, file_path: Path) -> bool:
        """Check if a file should be ignored based on .gitignore patterns."""
        if not self.patterns:
            return False
        
        # Get relative path from project root
        try:
            rel_path = file_path.relative_to(self.project_root)
            path_str = str(rel_path).replace('\\', '/')  # Normalize path separators
        except ValueError:
            # File is outside project root
            return False
        
        # Check if file should be ignored
        ignored = False
        
        for pattern in self.patterns:
            if self._match_pattern(path_str, pattern):
                ignored = True
                break
        
        # Check negation patterns (! patterns)
        if ignored:
            for pattern in self.negation_patterns:
                if self._match_pattern(path_str, pattern):
                    ignored = False
                    break
        
        return ignored
    
    def _match_pattern(self, path: str, pattern: str) -> bool:
        """Match a single gitignore pattern against a path."""
        # Handle directory patterns (ending with /)
        if pattern.endswith('/'):
            pattern = pattern[:-1]
            # Only match directories
            if '/' not in path or not path.endswith('/'):
                return False
        
        # Handle patterns starting with /
        if pattern.startswith('/'):
            pattern = pattern[1:]
            # Match from root only
            return fnmatch.fnmatch(path, pattern) or path.startswith(pattern + '/')
        
        # Handle patterns with intermediate directories
        if '/' in pattern:
            # Pattern contains directory separators
            path_parts = path.split('/')
            pattern_parts = pattern.split('/')
            
            # Try to match pattern at any position in path
            for i in range(len(path_parts) - len(pattern_parts) + 1):
                match = True
                for j, pattern_part in enumerate(pattern_parts):
                    if not fnmatch.fnmatch(path_parts[i + j], pattern_part):
                        match = False
                        break
                if match:
                    return True
            return False
        
        # Simple filename pattern
        filename = os.path.basename(path)
        return fnmatch.fnmatch(filename, pattern) or fnmatch.fnmatch(path, pattern)
    
    def get_ignore_patterns(self) -> List[str]:
        """Get all ignore patterns as simple strings for compatibility."""
        return self.patterns + [f"!{p}" for p in self.negation_patterns]