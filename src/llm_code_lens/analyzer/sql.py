from pathlib import Path
from typing import Dict, List, Optional
from .base import BaseAnalyzer
import re

class SQLServerAnalyzer(BaseAnalyzer):
    """SQL Server code analyzer with regex-based parsing."""
    
    def __init__(self):
        super().__init__()
    
    def analyze_file(self, file_path: Path) -> dict:
        """Analyze a SQL file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            analysis = {
                'type': 'sql',
                'procedures': [],
                'functions': [],
                'tables': [],
                'views': [],
                'triggers': [],
                'parameters': [],
                'dependencies': [],
                'comments': [],
                'todos': [],
                'metrics': {
                    'loc': len(content.splitlines()),
                    'procedures': 0,
                    'functions': 0,
                    'tables': 0,
                    'views': 0,
                    'triggers': 0,
                    'complexity': 0
                }
            }
            
            # Extract SQL constructs
            self._extract_procedures(content, analysis)
            self._extract_functions(content, analysis)
            self._extract_tables(content, analysis)
            self._extract_views(content, analysis)
            self._extract_triggers(content, analysis)
            self._extract_comments(content, analysis)
            
            # Update metrics
            analysis['metrics']['procedures'] = len(analysis['procedures'])
            analysis['metrics']['functions'] = len(analysis['functions'])
            analysis['metrics']['tables'] = len(analysis['tables'])
            analysis['metrics']['views'] = len(analysis['views'])
            analysis['metrics']['triggers'] = len(analysis['triggers'])
            analysis['metrics']['complexity'] = self._calculate_complexity(content)
            
            return analysis
            
        except Exception as e:
            return {
                'type': 'sql',
                'errors': [{'type': 'parse_error', 'text': str(e)}],
                'metrics': {'loc': 0, 'procedures': 0, 'functions': 0, 'tables': 0, 'views': 0, 'triggers': 0, 'complexity': 0}
            }
    
    def _extract_procedures(self, content: str, analysis: dict):
        """Extract stored procedures."""
        # Pattern for CREATE PROCEDURE
        proc_pattern = r'CREATE\s+(?:OR\s+ALTER\s+)?PROCEDURE\s+(\w+\.?\w*)\s*(?:\(([^)]*)\))?'
        matches = re.finditer(proc_pattern, content, re.IGNORECASE | re.MULTILINE)
        
        procedures = []
        for match in matches:
            proc_name = match.group(1)
            params_text = match.group(2) or ''
            
            # Extract line number
            line_number = content[:match.start()].count('\n') + 1
            
            # Parse parameters
            parameters = self._parse_parameters(params_text)
            
            # Extract procedure body for analysis
            proc_start = match.end()
            proc_body = self._extract_block_body(content, proc_start)
            
            procedures.append({
                'name': proc_name,
                'line_number': line_number,
                'parameters': parameters,
                'complexity': self._calculate_block_complexity(proc_body),
                'dependencies': self._extract_dependencies(proc_body)
            })
        
        analysis['procedures'] = procedures
    
    def _extract_functions(self, content: str, analysis: dict):
        """Extract user-defined functions."""
        func_pattern = r'CREATE\s+(?:OR\s+ALTER\s+)?FUNCTION\s+(\w+\.?\w*)\s*\(([^)]*)\)'
        matches = re.finditer(func_pattern, content, re.IGNORECASE | re.MULTILINE)
        
        functions = []
        for match in matches:
            func_name = match.group(1)
            params_text = match.group(2) or ''
            
            line_number = content[:match.start()].count('\n') + 1
            parameters = self._parse_parameters(params_text)
            
            func_start = match.end()
            func_body = self._extract_block_body(content, func_start)
            
            functions.append({
                'name': func_name,
                'line_number': line_number,
                'parameters': parameters,
                'return_type': self._extract_return_type(func_body),
                'complexity': self._calculate_block_complexity(func_body)
            })
        
        analysis['functions'] = functions
    
    def _extract_tables(self, content: str, analysis: dict):
        """Extract table definitions."""
        table_pattern = r'CREATE\s+TABLE\s+(\w+\.?\w*)\s*\('
        matches = re.finditer(table_pattern, content, re.IGNORECASE | re.MULTILINE)
        
        tables = []
        for match in matches:
            table_name = match.group(1)
            line_number = content[:match.start()].count('\n') + 1
            
            # Extract table definition
            table_start = match.start()
            table_body = self._extract_block_body(content, table_start, 'CREATE TABLE')
            columns = self._extract_table_columns(table_body)
            
            tables.append({
                'name': table_name,
                'line_number': line_number,
                'columns': columns
            })
        
        analysis['tables'] = tables
    
    def _extract_views(self, content: str, analysis: dict):
        """Extract view definitions."""
        view_pattern = r'CREATE\s+(?:OR\s+ALTER\s+)?VIEW\s+(\w+\.?\w*)'
        matches = re.finditer(view_pattern, content, re.IGNORECASE | re.MULTILINE)
        
        views = []
        for match in matches:
            view_name = match.group(1)
            line_number = content[:match.start()].count('\n') + 1
            
            views.append({
                'name': view_name,
                'line_number': line_number
            })
        
        analysis['views'] = views
    
    def _extract_triggers(self, content: str, analysis: dict):
        """Extract trigger definitions."""
        trigger_pattern = r'CREATE\s+(?:OR\s+ALTER\s+)?TRIGGER\s+(\w+\.?\w*)'
        matches = re.finditer(trigger_pattern, content, re.IGNORECASE | re.MULTILINE)
        
        triggers = []
        for match in matches:
            trigger_name = match.group(1)
            line_number = content[:match.start()].count('\n') + 1
            
            triggers.append({
                'name': trigger_name,
                'line_number': line_number
            })
        
        analysis['triggers'] = triggers
    
    def _extract_comments(self, content: str, analysis: dict):
        """Extract comments and TODOs."""
        comments = []
        todos = []
        
        lines = content.splitlines()
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            
            # Single line comments
            if stripped.startswith('--'):
                comment_text = stripped[2:].strip()
                
                if any(marker in comment_text.upper() for marker in ['TODO', 'FIXME', 'XXX', 'HACK', 'BUG']):
                    todos.append({
                        'line': i,
                        'text': comment_text,
                        'type': 'todo'
                    })
                else:
                    comments.append({
                        'line': i,
                        'text': comment_text
                    })
            
            # Multi-line comments
            elif '/*' in stripped:
                # Simple handling of /* */ comments
                comment_start = stripped.find('/*')
                if '*/' in stripped:
                    comment_end = stripped.find('*/')
                    comment_text = stripped[comment_start+2:comment_end].strip()
                    
                    if any(marker in comment_text.upper() for marker in ['TODO', 'FIXME', 'XXX']):
                        todos.append({
                            'line': i,
                            'text': comment_text,
                            'type': 'todo'
                        })
                    else:
                        comments.append({
                            'line': i,
                            'text': comment_text
                        })
        
        analysis['comments'] = comments
        analysis['todos'] = todos
    
    def _parse_parameters(self, params_text: str) -> List[dict]:
        """Parse SQL parameters."""
        if not params_text.strip():
            return []
        
        parameters = []
        # Split by comma, but be careful of nested parentheses
        param_parts = re.split(r',(?![^()]*\))', params_text)
        
        for param in param_parts:
            param = param.strip()
            if param:
                # Parse parameter: @name TYPE [= default]
                parts = param.split()
                if len(parts) >= 2:
                    param_name = parts[0]
                    param_type = parts[1]
                    
                    # Look for default value
                    default_value = None
                    if '=' in param:
                        default_value = param.split('=')[1].strip()
                    
                    parameters.append({
                        'name': param_name,
                        'type': param_type,
                        'default': default_value
                    })
        
        return parameters
    
    def _extract_block_body(self, content: str, start_pos: int, block_type: str = None) -> str:
        """Extract the body of a SQL block (procedure, function, etc.)."""
        # Find the next END statement or end of file
        remaining_content = content[start_pos:]
        
        # Look for AS keyword followed by body
        as_match = re.search(r'\bAS\b', remaining_content, re.IGNORECASE)
        if as_match:
            body_start = start_pos + as_match.end()
            # Find matching END
            body_content = content[body_start:]
            
            # Simple approach: find the next standalone END
            end_match = re.search(r'\bEND\b', body_content, re.IGNORECASE)
            if end_match:
                return body_content[:end_match.start()]
            else:
                # Return next 1000 characters if no END found
                return body_content[:1000]
        
        return remaining_content[:500]  # Fallback
    
    def _extract_dependencies(self, body: str) -> List[str]:
        """Extract table/view dependencies from SQL body."""
        dependencies = set()
        
        # Look for FROM, JOIN, INTO, UPDATE, DELETE patterns
        patterns = [
            r'\bFROM\s+(\w+\.?\w*)',
            r'\bJOIN\s+(\w+\.?\w*)',
            r'\bINTO\s+(\w+\.?\w*)',
            r'\bUPDATE\s+(\w+\.?\w*)',
            r'\bDELETE\s+FROM\s+(\w+\.?\w*)'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, body, re.IGNORECASE)
            dependencies.update(matches)
        
        return sorted(list(dependencies))
    
    def _extract_return_type(self, body: str) -> Optional[str]:
        """Extract return type from function body."""
        returns_match = re.search(r'RETURNS\s+(\w+(?:\(\d+(?:,\s*\d+)?\))?)', body, re.IGNORECASE)
        if returns_match:
            return returns_match.group(1)
        return None
    
    def _extract_table_columns(self, table_body: str) -> List[dict]:
        """Extract column definitions from CREATE TABLE statement."""
        columns = []
        
        # Find the column definitions between parentheses
        paren_start = table_body.find('(')
        paren_end = table_body.rfind(')')
        
        if paren_start != -1 and paren_end != -1:
            columns_text = table_body[paren_start+1:paren_end]
            
            # Split by comma and parse each column
            column_lines = columns_text.split(',')
            
            for line in column_lines:
                line = line.strip()
                if line and not line.upper().startswith('CONSTRAINT'):
                    parts = line.split()
                    if len(parts) >= 2:
                        col_name = parts[0]
                        col_type = parts[1]
                        
                        # Check for NOT NULL, PRIMARY KEY, etc.
                        nullable = 'NOT NULL' not in line.upper()
                        is_primary = 'PRIMARY KEY' in line.upper()
                        
                        columns.append({
                            'name': col_name,
                            'type': col_type,
                            'nullable': nullable,
                            'is_primary_key': is_primary
                        })
        
        return columns
    
    def _calculate_complexity(self, content: str) -> int:
        """Calculate overall complexity of SQL file."""
        complexity = 0
        
        # Count control flow statements
        complexity += len(re.findall(r'\bIF\b', content, re.IGNORECASE))
        complexity += len(re.findall(r'\bWHILE\b', content, re.IGNORECASE))
        complexity += len(re.findall(r'\bCASE\b', content, re.IGNORECASE))
        complexity += len(re.findall(r'\bTRY\b', content, re.IGNORECASE))
        complexity += len(re.findall(r'\bCATCH\b', content, re.IGNORECASE))
        
        # Count joins (complexity indicators)
        complexity += len(re.findall(r'\bJOIN\b', content, re.IGNORECASE))
        
        return complexity
    
    def _calculate_block_complexity(self, body: str) -> int:
        """Calculate complexity of a specific SQL block."""
        complexity = 1  # Base complexity
        
        # Count control flow statements
        complexity += body.upper().count('IF ')
        complexity += body.upper().count('WHILE ')
        complexity += body.upper().count('CASE ')
        complexity += body.upper().count('TRY')
        complexity += body.upper().count('CATCH')
        complexity += body.upper().count('JOIN ')
        complexity += body.upper().count('UNION')
        complexity += body.upper().count('EXISTS')
        
        return complexity