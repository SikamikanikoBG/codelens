import ast
from pathlib import Path
from typing import Dict, List, Optional
from .base import BaseAnalyzer

# Try tree-sitter-languages first (easiest)
try:
    from tree_sitter_languages import get_language, get_parser
    TREE_SITTER_AVAILABLE = True
except ImportError:
    TREE_SITTER_AVAILABLE = False

class PythonAnalyzer(BaseAnalyzer):
    """Python code analyzer with Tree-sitter support."""
    
    def __init__(self):
        super().__init__()
        self.tree_sitter_enabled = False
        
        if TREE_SITTER_AVAILABLE:
            try:
                self.language = get_language('python')
                self.parser = get_parser('python')
                self.tree_sitter_enabled = True
            except Exception:
                pass
    
    def analyze_file(self, file_path: Path) -> dict:
        """Analyze a Python file."""
        if self.tree_sitter_enabled:
            return self._analyze_with_treesitter(file_path)
        else:
            return self._analyze_with_ast(file_path)
    
    def _analyze_with_treesitter(self, file_path: Path) -> dict:
        """Analyze using Tree-sitter."""
        try:
            with open(file_path, 'rb') as f:
                content_bytes = f.read()
            
            tree = self.parser.parse(content_bytes)
            content = content_bytes.decode('utf-8', errors='ignore')
            
            analysis = {
                'type': 'python',
                'imports': [],
                'functions': [],
                'classes': [],
                'comments': [],
                'todos': [],
                'metrics': {
                    'loc': len(content.splitlines()),
                    'classes': 0,
                    'functions': 0,
                    'imports': 0,
                    'complexity': 0
                }
            }
            
            # Simple Tree-sitter queries
            self._extract_imports(tree, content, analysis)
            self._extract_functions(tree, content, analysis)
            self._extract_classes(tree, content, analysis)
            self._extract_comments(tree, content, analysis)
            
            # Update metrics
            analysis['metrics']['classes'] = len(analysis['classes'])
            analysis['metrics']['functions'] = len(analysis['functions'])
            analysis['metrics']['imports'] = len(analysis['imports'])
            analysis['metrics']['complexity'] = sum(f.get('complexity', 1) for f in analysis['functions'])
            
            return analysis
            
        except Exception as e:
            # Fall back to AST on any error
            return self._analyze_with_ast(file_path)
    
    def _extract_imports(self, tree, content: str, analysis: dict):
        """Extract imports using Tree-sitter."""
        try:
            query = self.language.query('(import_statement) @import (import_from_statement) @import')
            captures = query.captures(tree.root_node)
            
            imports = set()
            for capture in captures:
                node = capture[0]
                import_text = content[node.start_byte:node.end_byte].strip()
                imports.add(import_text)
            
            analysis['imports'] = sorted(list(imports))
            analysis['metrics']['imports'] = len(imports)
        except Exception:
            pass
    
    def _extract_functions(self, tree, content: str, analysis: dict):
        """Extract functions using Tree-sitter."""
        try:
            query = self.language.query('(function_definition) @function')
            captures = query.captures(tree.root_node)
            
            functions = []
            for capture in captures:
                node = capture[0]
                func_text = content[node.start_byte:node.end_byte]
                
                # Extract function name from first line
                first_line = func_text.split('\n')[0].strip()
                if first_line.startswith('def ') or first_line.startswith('async def '):
                    func_name = first_line.split('(')[0].replace('def ', '').replace('async ', '').strip()
                    is_async = 'async def' in first_line
                    
                    # Simple complexity estimation
                    complexity = 1 + func_text.count('if ') + func_text.count('elif ') + func_text.count('while ') + func_text.count('for ')
                    
                    # Extract docstring
                    docstring = None
                    lines = func_text.split('\n')
                    for i, line in enumerate(lines[1:], 1):
                        stripped = line.strip()
                        if stripped.startswith('"""') or stripped.startswith("'''"):
                            quote_char = '"""' if '"""' in stripped else "'''"
                            if stripped.endswith(quote_char) and len(stripped) > 6:
                                docstring = stripped.strip(quote_char).strip()
                                break
                    
                    functions.append({
                        'name': func_name,
                        'line_number': content[:node.start_byte].count('\n') + 1,
                        'is_async': is_async,
                        'complexity': complexity,
                        'docstring': docstring
                    })
            
            analysis['functions'] = functions
        except Exception:
            pass
    
    def _extract_classes(self, tree, content: str, analysis: dict):
        """Extract classes using Tree-sitter."""
        try:
            query = self.language.query('(class_definition) @class')
            captures = query.captures(tree.root_node)
            
            classes = []
            for capture in captures:
                node = capture[0]
                class_text = content[node.start_byte:node.end_byte]
                
                # Extract class name from first line
                first_line = class_text.split('\n')[0].strip()
                if first_line.startswith('class '):
                    if '(' in first_line:
                        class_name = first_line.split('(')[0].replace('class ', '').strip()
                        # Extract base classes
                        bases_part = first_line.split('(')[1].split(')')[0]
                        bases = [b.strip() for b in bases_part.split(',') if b.strip()] if bases_part else []
                    else:
                        class_name = first_line.split(':')[0].replace('class ', '').strip()
                        bases = []
                    
                    # Extract methods
                    methods = []
                    for line in class_text.split('\n'):
                        stripped = line.strip()
                        if stripped.startswith('def '):
                            method_name = stripped.split('(')[0].replace('def ', '').strip()
                            methods.append(method_name)
                    
                    # Extract docstring
                    docstring = None
                    lines = class_text.split('\n')
                    for i, line in enumerate(lines[1:], 1):
                        stripped = line.strip()
                        if stripped.startswith('"""') or stripped.startswith("'''"):
                            quote_char = '"""' if '"""' in stripped else "'''"
                            if stripped.endswith(quote_char) and len(stripped) > 6:
                                docstring = stripped.strip(quote_char).strip()
                                break
                    
                    classes.append({
                        'name': class_name,
                        'line_number': content[:node.start_byte].count('\n') + 1,
                        'bases': bases,
                        'methods': methods,
                        'docstring': docstring
                    })
            
            analysis['classes'] = classes
        except Exception:
            pass
    
    def _extract_comments(self, tree, content: str, analysis: dict):
        """Extract comments using Tree-sitter."""
        try:
            query = self.language.query('(comment) @comment')
            captures = query.captures(tree.root_node)
            
            comments = []
            todos = []
            
            for capture in captures:
                node = capture[0]
                comment_text = content[node.start_byte:node.end_byte].strip()
                line_number = content[:node.start_byte].count('\n') + 1
                
                # Remove # prefix
                if comment_text.startswith('#'):
                    comment_text = comment_text[1:].strip()
                
                # Check for TODOs
                if any(marker in comment_text.upper() for marker in ['TODO', 'FIXME', 'XXX', 'HACK', 'BUG']):
                    todos.append({
                        'line': line_number,
                        'text': comment_text,
                        'type': 'todo'
                    })
                else:
                    comments.append({
                        'line': line_number,
                        'text': comment_text
                    })
            
            analysis['comments'] = comments
            analysis['todos'] = todos
        except Exception:
            pass
    
    def _analyze_with_ast(self, file_path: Path) -> dict:
        """Fallback AST analysis."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            analysis = {
                'type': 'python',
                'imports': [],
                'functions': [],
                'classes': [],
                'comments': [],
                'todos': [],
                'metrics': {
                    'loc': len(content.splitlines()),
                    'classes': 0,
                    'functions': 0,
                    'imports': 0,
                    'complexity': 0
                }
            }
            
            # Process AST
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for name in node.names:
                        analysis['imports'].append(f"import {name.name}")
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ''
                    for name in node.names:
                        analysis['imports'].append(f"from {module} import {name.name}")
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    analysis['functions'].append({
                        'name': node.name,
                        'line_number': node.lineno,
                        'is_async': isinstance(node, ast.AsyncFunctionDef),
                        'complexity': 1,
                        'docstring': ast.get_docstring(node)
                    })
                elif isinstance(node, ast.ClassDef):
                    analysis['classes'].append({
                        'name': node.name,
                        'line_number': node.lineno,
                        'bases': [b.id if isinstance(b, ast.Name) else str(b) for b in node.bases],
                        'methods': [n.name for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))],
                        'docstring': ast.get_docstring(node)
                    })
            
            # Process comments
            for i, line in enumerate(content.split('\n'), 1):
                if line.strip().startswith('#'):
                    comment = line.strip()[1:].strip()
                    if any(marker in comment.upper() for marker in ['TODO', 'FIXME', 'XXX']):
                        analysis['todos'].append({'text': comment, 'line': i})
                    else:
                        analysis['comments'].append({'text': comment, 'line': i})
            
            # Update metrics
            analysis['imports'] = sorted(list(set(analysis['imports'])))
            analysis['metrics']['classes'] = len(analysis['classes'])
            analysis['metrics']['functions'] = len(analysis['functions'])
            analysis['metrics']['imports'] = len(analysis['imports'])
            analysis['metrics']['complexity'] = sum(f.get('complexity', 1) for f in analysis['functions'])
            
            return analysis
            
        except Exception as e:
            return {
                'type': 'python',
                'errors': [{'type': 'parse_error', 'text': str(e)}],
                'metrics': {'loc': 0, 'classes': 0, 'functions': 0, 'imports': 0, 'complexity': 0}
            }