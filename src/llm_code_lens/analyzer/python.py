import ast
from pathlib import Path
from typing import Dict, List, Optional

class PythonAnalyzer:
    """Python-specific code analyzer using AST."""
    
    def analyze_file(self, file_path: Path) -> dict:
        """Analyze a Python file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        analysis = {
            'imports': [],
            'functions': [],
            'classes': [],
            'comments': [],
            'todos': [],
            'full_content': content,  # Store full content for reference
            'metrics': {
                'loc': len(content.splitlines()),
                'classes': 0,
                'functions': 0,
                'imports': 0,
            }
        }
        
        try:
            tree = ast.parse(content)
            
            # Extract imports
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    analysis['metrics']['imports'] += len(node.names)
                    for name in node.names:
                        analysis['imports'].append(f"import {name.name}")
                elif isinstance(node, ast.ImportFrom):
                    analysis['metrics']['imports'] += len(node.names)
                    module = node.module or ''
                    for name in node.names:
                        analysis['imports'].append(
                            f"from {module} import {name.name}"
                        )
            
            # Extract functions
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    analysis['metrics']['functions'] += 1
                    
                    # Extract function body
                    body_start = node.body[0].lineno if node.body else node.lineno
                    body_end = node.body[-1].end_lineno if node.body else node.end_lineno
                    function_content = '\n'.join(
                        content.splitlines()[body_start-1:body_end]
                    )
                    
                    analysis['functions'].append({
                        'name': node.name,
                        'args': [arg.arg for arg in node.args.args],
                        'docstring': ast.get_docstring(node),
                        'content': function_content,
                        'loc': len(node.body),
                        'line_number': node.lineno
                    })
            
            # Extract classes
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    analysis['metrics']['classes'] += 1
                    analysis['classes'].append({
                        'name': node.name,
                        'docstring': ast.get_docstring(node),
                        'methods': [n.name for n in node.body 
                                  if isinstance(n, ast.FunctionDef)],
                        'line_number': node.lineno
                    })
            
            # Extract comments and TODOs
            lines = content.split('\n')
            for i, line in enumerate(lines, 1):
                line = line.strip()
                if line.startswith('#'):
                    comment_text = line[1:].strip()
                    if any(marker in comment_text.upper() 
                          for marker in ['TODO', 'FIXME', 'XXX']):
                        analysis['todos'].append({
                            'line': i,
                            'text': comment_text
                        })
                    else:
                        analysis['comments'].append({
                            'line': i,
                            'text': comment_text
                        })
            
        except SyntaxError as e:
            analysis['errors'] = [f"Syntax error: {str(e)}"]
        
        return analysis