from pathlib import Path
from typing import Dict, List, Optional
from .base import BaseAnalyzer

# Try tree-sitter-languages first (easiest)
try:
    from tree_sitter_languages import get_language, get_parser
    TREE_SITTER_AVAILABLE = True
except ImportError:
    TREE_SITTER_AVAILABLE = False

class JavaScriptAnalyzer(BaseAnalyzer):
    """JavaScript/TypeScript code analyzer with Tree-sitter support."""
    
    def __init__(self):
        super().__init__()
        self.tree_sitter_enabled = False
        
        if TREE_SITTER_AVAILABLE:
            try:
                self.language = get_language('javascript')
                self.parser = get_parser('javascript')
                self.tree_sitter_enabled = True
            except Exception:
                pass
    
    def analyze_file(self, file_path: Path) -> dict:
        """Analyze a JavaScript/TypeScript file."""
        if self.tree_sitter_enabled:
            return self._analyze_with_treesitter(file_path)
        else:
            return self._analyze_with_regex(file_path)
    
    def _analyze_with_treesitter(self, file_path: Path) -> dict:
        """Analyze using Tree-sitter."""
        try:
            with open(file_path, 'rb') as f:
                content_bytes = f.read()
            
            tree = self.parser.parse(content_bytes)
            content = content_bytes.decode('utf-8', errors='ignore')
            
            analysis = {
                'type': 'javascript',
                'imports': [],
                'exports': [],
                'functions': [],
                'classes': [],
                'components': [],
                'hooks': [],
                'interfaces': [],
                'types': [],
                'comments': [],
                'todos': [],
                'metrics': {
                    'loc': len(content.splitlines()),
                    'classes': 0,
                    'functions': 0,
                    'imports': 0,
                    'exports': 0,
                    'components': 0,
                    'hooks': 0,
                    'complexity': 0
                }
            }
            
            # Simple Tree-sitter queries
            self._extract_imports_exports(tree, content, analysis)
            self._extract_functions(tree, content, analysis)
            self._extract_classes(tree, content, analysis)
            self._extract_react_features(tree, content, analysis)
            self._extract_typescript_features(tree, content, analysis)
            self._extract_comments(tree, content, analysis)
            
            # Update metrics
            analysis['metrics']['classes'] = len(analysis['classes'])
            analysis['metrics']['functions'] = len(analysis['functions'])
            analysis['metrics']['imports'] = len(analysis['imports'])
            analysis['metrics']['exports'] = len(analysis['exports'])
            analysis['metrics']['components'] = len(analysis['components'])
            analysis['metrics']['hooks'] = len(analysis['hooks'])
            analysis['metrics']['complexity'] = sum(f.get('complexity', 1) for f in analysis['functions'])
            
            return analysis
            
        except Exception as e:
            # Fall back to regex on any error
            return self._analyze_with_regex(file_path)
    
    def _extract_imports_exports(self, tree, content: str, analysis: dict):
        """Extract imports and exports using Tree-sitter."""
        try:
            # Import statements
            import_query = self.language.query('(import_statement) @import')
            import_captures = import_query.captures(tree.root_node)
            
            imports = set()
            for capture in import_captures:
                node = capture[0]
                import_text = content[node.start_byte:node.end_byte].strip()
                imports.add(import_text)
            
            # Export statements
            export_query = self.language.query('(export_statement) @export')
            export_captures = export_query.captures(tree.root_node)
            
            exports = set()
            for capture in export_captures:
                node = capture[0]
                export_text = content[node.start_byte:node.end_byte].strip()
                exports.add(export_text)
            
            analysis['imports'] = sorted(list(imports))
            analysis['exports'] = sorted(list(exports))
            
        except Exception:
            pass
    
    def _extract_functions(self, tree, content: str, analysis: dict):
        """Extract functions using Tree-sitter."""
        try:
            query = self.language.query('''
                (function_declaration) @function
                (arrow_function) @arrow
                (method_definition) @method
            ''')
            captures = query.captures(tree.root_node)
            
            functions = []
            for capture in captures:
                node = capture[0]
                func_text = content[node.start_byte:node.end_byte]
                line_number = content[:node.start_byte].count('\n') + 1
                
                # Extract function name and details
                func_info = self._parse_function_info(func_text, line_number)
                if func_info:
                    functions.append(func_info)
            
            analysis['functions'] = functions
            
        except Exception:
            pass
    
    def _extract_classes(self, tree, content: str, analysis: dict):
        """Extract classes using Tree-sitter."""
        try:
            query = self.language.query('(class_declaration) @class')
            captures = query.captures(tree.root_node)
            
            classes = []
            for capture in captures:
                node = capture[0]
                class_text = content[node.start_byte:node.end_byte]
                line_number = content[:node.start_byte].count('\n') + 1
                
                # Extract class name from first line
                first_line = class_text.split('\n')[0].strip()
                if first_line.startswith('class '):
                    class_name = first_line.split(' ')[1].split('{')[0].split('(')[0].split(' extends')[0].strip()
                    
                    # Extract extends
                    extends = None
                    if ' extends ' in first_line:
                        extends = first_line.split(' extends ')[1].split('{')[0].strip()
                    
                    # Extract methods
                    methods = []
                    for line in class_text.split('\n'):
                        stripped = line.strip()
                        if (stripped.startswith('async ') and '(' in stripped) or \
                           (not stripped.startswith('//') and '(' in stripped and stripped.endswith('{') and not stripped.startswith('if') and not stripped.startswith('for')):
                            method_name = stripped.split('(')[0].replace('async ', '').strip()
                            if method_name and not method_name.startswith('class'):
                                methods.append(method_name)
                    
                    classes.append({
                        'name': class_name,
                        'line_number': line_number,
                        'extends': extends,
                        'methods': methods
                    })
            
            analysis['classes'] = classes
            
        except Exception:
            pass
    
    def _extract_react_features(self, tree, content: str, analysis: dict):
        """Extract React components and hooks."""
        try:
            # React components (functions/variables starting with capital letter)
            component_query = self.language.query('''
                (function_declaration name: (identifier) @name) @func
                (variable_declarator name: (identifier) @var_name) @var
            ''')
            captures = component_query.captures(tree.root_node)
            
            components = []
            for capture in captures:
                node = capture[0]
                name = content[node.start_byte:node.end_byte].strip()
                
                # React components typically start with uppercase
                if name and name[0].isupper():
                    line_number = content[:node.start_byte].count('\n') + 1
                    components.append({
                        'name': name,
                        'line_number': line_number,
                        'type': 'function'
                    })
            
            analysis['components'] = components
            
            # React hooks (function calls starting with 'use')
            hook_query = self.language.query('(call_expression function: (identifier) @hook_name)')
            hook_captures = hook_query.captures(tree.root_node)
            
            hooks = []
            standard_hooks = {'useState', 'useEffect', 'useContext', 'useReducer', 'useCallback', 'useMemo', 'useRef'}
            
            for capture in hook_captures:
                node = capture[0]
                hook_name = content[node.start_byte:node.end_byte].strip()
                
                if hook_name.startswith('use') and len(hook_name) > 3:
                    line_number = content[:node.start_byte].count('\n') + 1
                    hooks.append({
                        'name': hook_name,
                        'line_number': line_number,
                        'is_custom': hook_name not in standard_hooks
                    })
            
            analysis['hooks'] = hooks
            
        except Exception:
            pass
    
    def _extract_typescript_features(self, tree, content: str, analysis: dict):
        """Extract TypeScript interfaces and types."""
        # Simple text-based extraction for TypeScript features
        lines = content.splitlines()
        interfaces = []
        types = []
        
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            
            # Interface declarations
            if stripped.startswith('interface '):
                interface_name = stripped.split(' ')[1].split('{')[0].split('<')[0].strip()
                interfaces.append({
                    'name': interface_name,
                    'line_number': i
                })
            
            # Type declarations
            elif stripped.startswith('type ') and '=' in stripped:
                type_name = stripped.split(' ')[1].split('=')[0].split('<')[0].strip()
                types.append({
                    'name': type_name,
                    'line_number': i
                })
        
        analysis['interfaces'] = interfaces
        analysis['types'] = types
    
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
                
                # Clean comment text
                if comment_text.startswith('//'):
                    comment_text = comment_text[2:].strip()
                elif comment_text.startswith('/*') and comment_text.endswith('*/'):
                    comment_text = comment_text[2:-2].strip()
                
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
    
    def _parse_function_info(self, func_text: str, line_number: int) -> Optional[dict]:
        """Parse function information from text."""
        try:
            first_line = func_text.split('\n')[0].strip()
            
            # Function declaration
            if first_line.startswith('function '):
                func_name = first_line.split('(')[0].replace('function ', '').strip()
                func_type = 'function'
                is_async = False
            elif first_line.startswith('async function '):
                func_name = first_line.split('(')[0].replace('async function ', '').strip()
                func_type = 'function'
                is_async = True
            # Arrow function
            elif '=>' in first_line:
                if 'const ' in first_line or 'let ' in first_line or 'var ' in first_line:
                    func_name = first_line.split('=')[0].replace('const ', '').replace('let ', '').replace('var ', '').strip()
                else:
                    func_name = 'anonymous'
                func_type = 'arrow'
                is_async = 'async' in first_line
            # Method
            else:
                func_name = first_line.split('(')[0].strip()
                func_type = 'method'
                is_async = 'async' in first_line
            
            # Extract parameters
            params = []
            if '(' in first_line and ')' in first_line:
                params_text = first_line.split('(')[1].split(')')[0].strip()
                if params_text:
                    params = [p.strip().split('=')[0].strip() for p in params_text.split(',')]
            
            # Simple complexity estimation
            complexity = 1 + func_text.count('if ') + func_text.count('else') + func_text.count('for ') + func_text.count('while ')
            
            return {
                'name': func_name,
                'type': func_type,
                'line_number': line_number,
                'is_async': is_async,
                'params': params,
                'complexity': complexity
            }
            
        except Exception:
            return None
    
    def _analyze_with_regex(self, file_path: Path) -> dict:
        """Fallback regex-based analysis."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            import re
            
            analysis = {
                'type': 'javascript',
                'imports': [],
                'exports': [],
                'functions': [],
                'classes': [],
                'components': [],
                'hooks': [],
                'interfaces': [],
                'types': [],
                'comments': [],
                'todos': [],
                'metrics': {
                    'loc': len(content.splitlines()),
                    'classes': 0,
                    'functions': 0,
                    'imports': 0,
                    'exports': 0,
                    'components': 0,
                    'hooks': 0,
                    'complexity': 0
                }
            }
            
            # Extract imports
            import_pattern = r'^import\s+.*?from\s+[\'"`].*?[\'"`]|^import\s+[\'"`].*?[\'"`]'
            imports = re.findall(import_pattern, content, re.MULTILINE)
            analysis['imports'] = list(set(imports))
            
            # Extract exports
            export_pattern = r'^export\s+.*'
            exports = re.findall(export_pattern, content, re.MULTILINE)
            analysis['exports'] = list(set(exports))
            
            # Extract functions
            func_pattern = r'(?:async\s+)?function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\(.*?\)\s*=>'
            func_matches = re.findall(func_pattern, content)
            functions = []
            for match in func_matches:
                func_name = match[0] or match[1]
                if func_name:
                    functions.append({'name': func_name, 'type': 'function'})
            analysis['functions'] = functions
            
            # Extract classes
            class_pattern = r'class\s+(\w+)'
            class_matches = re.findall(class_pattern, content)
            classes = []
            for class_name in class_matches:
                classes.append({'name': class_name})
            analysis['classes'] = classes
            
            # Update metrics
            analysis['metrics']['classes'] = len(analysis['classes'])
            analysis['metrics']['functions'] = len(analysis['functions'])
            analysis['metrics']['imports'] = len(analysis['imports'])
            analysis['metrics']['exports'] = len(analysis['exports'])
            
            return analysis
            
        except Exception as e:
            return {
                'type': 'javascript',
                'errors': [{'type': 'parse_error', 'text': str(e)}],
                'metrics': {'loc': 0, 'classes': 0, 'functions': 0, 'imports': 0, 'complexity': 0}
            }