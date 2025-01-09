# Update to src/llm_code_lens/analyzer/sql.py

import re
from pathlib import Path
from typing import Dict, List, Optional
import os

class SQLServerAnalyzer:
    """SQL Server code analyzer for stored procedures and views."""
    def analyze_file(self, file_path: Path) -> dict:
        """Analyze a SQL file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        analysis = {
            'type': 'sql',
            'metrics': {
                'loc': len(content.splitlines()),
                'complexity': self._estimate_complexity(content)
            },
            'objects': [],
            'parameters': [],
            'comments': [],
            'todos': [],
            'dependencies': self._extract_dependencies(content)
        }
        
        # Extract SQL objects
        objects = self._extract_sql_objects(content)
        if objects:
            analysis['objects'] = objects
        
        # Extract and update parameters with comments
        params = self._extract_parameters(content)
        self._update_params_with_comments(params, content)
        if params:
            analysis['parameters'] = params
        
        # Extract comments and TODOs
        comments, todos = self._extract_comments_and_todos(content)
        analysis['comments'] = comments
        analysis['todos'] = todos
        
        return analysis
    
    def _extract_sql_objects(self, content: str) -> List[dict]:
        """Extract SQL objects like procedures, functions, and views."""
        objects = []
        
        # Match CREATE/ALTER statements
        patterns = {
            'procedure': r'CREATE\s+(?:OR\s+ALTER\s+)?PROCEDURE\s+([^\s]+)',
            'function': r'CREATE\s+(?:OR\s+ALTER\s+)?FUNCTION\s+([^\s]+)',
            'view': r'CREATE\s+(?:OR\s+ALTER\s+)?VIEW\s+([^\s]+)'
        }
        
        for obj_type, pattern in patterns.items():
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                name = match.group(1)
                # Find the object's body
                start_pos = match.start()
                # Look for GO or end of file
                end_match = re.search(r'\bGO\b', content[start_pos:], re.IGNORECASE)
                if end_match:
                    end_pos = start_pos + end_match.start()
                    definition = content[start_pos:end_pos].strip()
                else:
                    definition = content[start_pos:].strip()
                
                objects.append({
                    'type': obj_type,
                    'name': name,
                    'definition': definition,
                    'loc': len(definition.splitlines()),
                    'complexity': self._estimate_complexity(definition)
                })
        
        return objects

    def _extract_parameters(self, content: str) -> List[dict]:
        """Extract parameters from procedure or function definitions."""
        params = []
        # Find the procedure declaration
        proc_match = re.search(
            r'CREATE\s+(?:OR\s+ALTER\s+)?PROCEDURE\s+([^\s]+)([\s\S]+?)AS\b',
            content,
            re.IGNORECASE
        )
        
        if proc_match:
            param_section = proc_match.group(2)
            # Extract each parameter line, handling multiline declarations
            param_lines = re.findall(
                r'@\w+\s+[^,@]+(?:\s*=\s*[^,]+)?(?=\s*,|\s*AS\b|\s*$)',
                param_section,
                re.IGNORECASE | re.DOTALL
            )
            
            for param_line in param_lines:
                # Extract individual parameter components
                param_match = re.match(
                    r'@(\w+)\s+([^=\s]+(?:\([^)]*\))?)\s*(?:=\s*([^,\s][^,]*)?)?',
                    param_line.strip()
                )
                
                if param_match:
                    name, data_type, default = param_match.groups()
                    param_info = {
                        'name': name,
                        'data_type': data_type.strip()
                    }
                    
                    if default:
                        param_info['default'] = default.strip()
                    
                    # Look for inline comment on the same line
                    comment_match = re.search(r'--\s*(.*?)(?:\r?\n|$)', param_line)
                    if comment_match:
                        param_info['description'] = comment_match.group(1).strip()
                    
                    params.append(param_info)
        
        return params

    def _update_params_with_comments(self, params: List[dict], content: str) -> None:
        """Update parameter documentation from nearby comments."""
        lines = content.splitlines()
        for i, line in enumerate(lines):
            if '--' in line and any(param['name'] in line for param in params):
                comment = line[line.index('--')+2:].strip()
                param_name = next(
                    (param['name'] for param in params if param['name'] in line),
                    None
                )
                if param_name:
                    param = next(p for p in params if p['name'] == param_name)
                    if 'description' not in param:
                        param['description'] = comment


    def _extract_dependencies(self, content: str) -> List[str]:
        """Extract table and view dependencies."""
        deps = set()
        
        # Define patterns for table references
        patterns = [
            # FROM, JOIN, UPDATE, etc. followed by table name
            r'(?:FROM|JOIN|INTO|UPDATE)\s+([a-zA-Z_]\w*(?:\.[a-zA-Z_]\w*)?)\b(?!\s*[=@])',
            # INSERT INTO pattern
            r'INSERT\s+INTO\s+([a-zA-Z_]\w*(?:\.[a-zA-Z_]\w*)?)\b',
            # REFERENCES in constraints
            r'REFERENCES\s+([a-zA-Z_]\w*(?:\.[a-zA-Z_]\w*)?)\b'
        ]
        
        # Define words that should not be treated as table names
        excluded_words = {
            'null', 'select', 'where', 'group', 'order', 'having',
            'exists', 'between', 'like', 'in', 'is', 'not', 'and', 'or',
            'operation', 'existing'  # Add common variables
        }
        
        for pattern in patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                table_name = match.group(1).strip()
                if table_name.lower() not in excluded_words:
                    deps.add(table_name)
        
        return sorted(list(deps))

    def _extract_comments_and_todos(self, content: str) -> tuple:
        """Extract comments and TODOs from SQL code."""
        comments = []
        todos = []
        
        # Match inline comments and block comments
        patterns = [
            (r'--([^\n]+)', False),  # Inline comments
            (r'/\*[\s\S]*?\*/', True)  # Block comments
        ]
        
        for pattern, is_multiline in patterns:
            for match in re.finditer(pattern, content):
                comment = match.group()
                if is_multiline:
                    comment = comment.strip('/*').strip('*/')
                else:
                    comment = comment.strip('--')
                comment = comment.strip()
                
                # Skip empty comments and parameter comments
                if not comment or comment.startswith('@'):
                    continue
                
                line_num = content[:match.start()].count('\n') + 1
                
                if any(marker in comment.upper() 
                    for marker in ['TODO', 'FIXME', 'XXX']):
                    todos.append({
                        'text': comment,
                        'line': line_num
                    })
                else:
                    comments.append({
                        'text': comment,
                        'line': line_num
                    })
        
        return comments, todos
   

    def _estimate_complexity(self, content: str) -> int:
        """Estimate SQL complexity based on various factors."""
        complexity = 0
        content_lower = content.lower()
        
        # Control flow complexity
        complexity += content_lower.count('if ') * 2
        complexity += content_lower.count('else ') * 2
        complexity += content_lower.count('case ') * 2
        complexity += content_lower.count('while ') * 3
        complexity += content_lower.count('cursor') * 4
        
        # Query complexity
        complexity += content_lower.count('join ') * 2
        complexity += content_lower.count('where ') * 2
        complexity += content_lower.count('group by ') * 2
        complexity += content_lower.count('having ') * 3
        complexity += content_lower.count('union ') * 3
        
        # Transaction complexity
        complexity += content_lower.count('transaction') * 2
        complexity += content_lower.count('try') * 2
        complexity += content_lower.count('catch') * 2
        
        return complexity