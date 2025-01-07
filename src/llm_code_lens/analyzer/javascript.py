# src/codelens/analyzer/javascript.py
import re
from pathlib import Path
from typing import Dict, List

class JavaScriptAnalyzer:
    """JavaScript/TypeScript code analyzer using regex patterns."""
    
    def analyze_file(self, file_path: Path) -> dict:
        """Analyze a JavaScript/TypeScript file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        analysis = {
            'imports': [],
            'exports': [],
            'functions': [],
            'classes': [],
            'comments': [],
            'todos': [],
            'metrics': {
                'loc': len(content.splitlines()),
                'classes': 0,
                'functions': 0,
                'imports': 0,
            }
        }
        
        # Extract imports and exports
        import_pattern = r'^(?:import|export)\s+.*?[\n;]'
        for match in re.finditer(import_pattern, content, re.MULTILINE):
            stmt = match.group().strip()
            analysis['metrics']['imports'] += 1
            if stmt.startswith('import'):
                analysis['imports'].append(stmt)
            else:
                analysis['exports'].append(stmt)
        
        # Extract functions
        function_pattern = r'(?:async\s+)?(?:function\s+(\w+)|const\s+(\w+)\s*=\s*(?:async\s+)?(?:\([^)]*\)\s*=>|\function\s*\([^)]*\)))'
        for match in re.finditer(function_pattern, content):
            analysis['metrics']['functions'] += 1
            name = match.group(1) or match.group(2)
            if name:
                analysis['functions'].append({
                    'name': name,
                    'line_number': content[:match.start()].count('\n') + 1
                })
        
        # Extract classes
        class_pattern = r'class\s+(\w+)(?:\s+extends\s+(\w+))?\s*\{'
        for match in re.finditer(class_pattern, content):
            analysis['metrics']['classes'] += 1
            analysis['classes'].append({
                'name': match.group(1),
                'extends': match.group(2),
                'line_number': content[:match.start()].count('\n') + 1
            })
        
        # Extract comments and TODOs
        comment_patterns = [
            r'//.*$',  # Single-line comments
            r'/\*[^*]*\*+(?:[^/*][^*]*\*+)*/'  # Multi-line comments
        ]
        
        for pattern in comment_patterns:
            for match in re.finditer(pattern, content, re.MULTILINE):
                comment = match.group()
                # Clean up comment markers
                comment = (comment.strip('/')  # For single-line
                         .strip('*')          # For multi-line
                         .strip())
                
                line_number = content[:match.start()].count('\n') + 1
                
                if any(marker in comment.upper() 
                      for marker in ['TODO', 'FIXME', 'XXX']):
                    analysis['todos'].append({
                        'line': line_number,
                        'text': comment
                    })
                else:
                    analysis['comments'].append({
                        'line': line_number,
                        'text': comment
                    })
        
        return analysis