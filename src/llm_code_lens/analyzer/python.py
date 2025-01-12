import ast
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union
from dataclasses import dataclass
from .base import BaseAnalyzer

@dataclass
class CodeLocation:
    """Represents a location in source code."""
    line: int
    column: int
    end_line: Optional[int] = None
    end_column: Optional[int] = None

@dataclass
class ImportInfo:
    """Information about an import statement."""
    name: str
    alias: Optional[str]
    module: Optional[str]
    is_relative: bool
    location: CodeLocation

@dataclass
class FunctionArgument:
    """Information about a function argument."""
    name: str
    type_annotation: Optional[str]
    default_value: Optional[str]
    is_kwonly: bool = False
    is_vararg: bool = False
    is_kwarg: bool = False

@dataclass
class FunctionInfo:
    """Detailed information about a function."""
    name: str
    args: List[FunctionArgument]
    return_type: Optional[str]
    docstring: Optional[str]
    decorators: List[str]
    is_async: bool
    location: CodeLocation
    complexity: int
    loc: int

@dataclass
class ClassInfo:
    """Detailed information about a class."""
    name: str
    bases: List[str]
    methods: List[str]
    docstring: Optional[str]
    decorators: List[str]
    location: CodeLocation
    complexity: int

class PythonAnalyzer(BaseAnalyzer):
    """Python-specific code analyzer using AST with enhanced features."""
    
    def analyze_file(self, file_path: Path) -> dict:
        """
        Analyze a Python file and return detailed analysis results.
        
        Args:
            file_path: Path to the Python file to analyze.
            
        Returns:
            dict: Comprehensive analysis results including:
                - Imports
                - Functions (with args, types, etc.)
                - Classes (with inheritance, methods)
                - Docstrings and comments
                - Complexity metrics
                - TODOs and other markers
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            # Initialize analysis dictionary
            analysis = {
                'type': 'python',
                'full_content': content,
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
            
            # Process each component
            self._process_imports(tree, analysis)
            self._process_functions(tree, analysis, content)
            self._process_classes(tree, analysis, content)
            self._process_comments(content, analysis)
            
            # Calculate overall complexity
            analysis['metrics']['complexity'] = self._calculate_module_complexity(tree)
            
            return analysis
            
        except SyntaxError as e:
            # Return partial analysis for syntax errors
            return {
                'type': 'python',
                'errors': [{
                    'type': 'syntax_error',
                    'line': e.lineno,
                    'offset': e.offset,
                    'text': str(e)
                }],
                'metrics': {
                    'loc': 0,
                    'classes': 0,
                    'functions': 0,
                    'imports': 0,
                    'complexity': 0
                }
            }
        except Exception as e:
            # Handle other errors gracefully
            return {
                'type': 'python',
                'errors': [{
                    'type': 'analysis_error',
                    'text': str(e)
                }],
                'metrics': {
                    'loc': 0,
                    'classes': 0,
                    'functions': 0,
                    'imports': 0,
                    'complexity': 0
                }
            }

    def _process_imports(self, tree: ast.AST, analysis: dict) -> None:
        """Process imports and handle each import statement individually."""
        unique_imports = set()
        import_count = 0
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for name in node.names:
                    import_count += 1
                    unique_imports.add(f"import {name.name}")
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ''
                level = '.' * node.level
                
                # Group imports from same module together
                for name in node.names:
                    import_count += 1
                    if name.asname:
                        unique_imports.add(f"from {level}{module} import {name.name} as {name.asname}")
                    else:
                        unique_imports.add(f"from {level}{module} import {name.name}")
        
        analysis['metrics']['imports'] = import_count
        analysis['imports'] = sorted(list(unique_imports))




    
    def _process_functions(self, tree: ast.AST, analysis: dict, content: str) -> None:
        """Extract and analyze function definitions."""
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                analysis['metrics']['functions'] += 1
                
                # Extract function information
                func_info = FunctionInfo(
                    name=node.name,
                    args=self._extract_function_args(node.args),
                    return_type=self._format_annotation(node.returns) if node.returns else None,
                    docstring=ast.get_docstring(node),
                    decorators=[self._format_decorator(d) for d in node.decorator_list],
                    is_async=isinstance(node, ast.AsyncFunctionDef),
                    location=CodeLocation(
                        line=node.lineno,
                        column=node.col_offset,
                        end_line=node.end_lineno,
                        end_column=node.end_col_offset
                    ),
                    complexity=self._calculate_function_complexity(node),
                    loc=len(node.body)
                )
                
                # Get function content
                func_content = self._extract_source(content, func_info.location)
                
                # Add to analysis
                analysis['functions'].append({
                    'name': func_info.name,
                    'args': [self._format_argument(arg) for arg in func_info.args],
                    'return_type': func_info.return_type,
                    'docstring': func_info.docstring,
                    'decorators': func_info.decorators,
                    'is_async': func_info.is_async,
                    'content': func_content,
                    'loc': func_info.loc,
                    'line_number': func_info.location.line,
                    'complexity': func_info.complexity
                })

    def _extract_function_args(self, args: ast.arguments) -> List[FunctionArgument]:
        """Extract function arguments with improved handling."""
        arguments = []
        
        # Handle positional-only arguments (Python 3.8+)
        if hasattr(args, 'posonlyargs'):
            for arg in args.posonlyargs:
                arguments.append(self._create_argument(arg))
        
        # Handle regular positional arguments
        for arg in args.args:
            # Skip self/cls for methods
            if arg.arg in ('self', 'cls') and len(args.args) > 0:
                continue
            arguments.append(self._create_argument(arg))
        
        # Add defaults for positional arguments
        defaults_start = len(arguments) - len(args.defaults)
        for i, default in enumerate(args.defaults):
            if i + defaults_start >= 0:  # Ensure valid index
                arguments[defaults_start + i].default_value = self._format_annotation(default)
        
        # Handle *args
        if args.vararg:
            arguments.append(FunctionArgument(
                name=f"*{args.vararg.arg}",
                type_annotation=self._format_annotation(args.vararg.annotation) if args.vararg.annotation else None,
                default_value=None,
                is_vararg=True
            ))
        
        # Handle keyword-only arguments
        for arg in args.kwonlyargs:
            arguments.append(self._create_argument(arg, is_kwonly=True))
        
        # Add defaults for keyword-only arguments
        for i, default in enumerate(args.kw_defaults):
            if default and i < len(args.kwonlyargs):
                arg_idx = len(arguments) - len(args.kw_defaults) + i
                if arg_idx >= 0:  # Ensure valid index
                    arguments[arg_idx].default_value = self._format_annotation(default)
        
        # Handle **kwargs
        if args.kwarg:
            arguments.append(FunctionArgument(
                name=f"**{args.kwarg.arg}",
                type_annotation=self._format_annotation(args.kwarg.annotation) if args.kwarg.annotation else None,
                default_value=None,
                is_kwarg=True
            ))
        
        return arguments

    def _create_argument(self, arg: ast.arg, is_kwonly: bool = False) -> FunctionArgument:
        """Helper to create a FunctionArgument instance."""
        return FunctionArgument(
            name=arg.arg,
            type_annotation=self._format_annotation(arg.annotation) if arg.annotation else None,
            default_value=None,
            is_kwonly=is_kwonly
        )

    
    def _process_classes(self, tree: ast.AST, analysis: dict, content: str) -> None:
        """Extract and analyze class definitions."""
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                analysis['metrics']['classes'] += 1
                
                # Get class information
                class_info = ClassInfo(
                    name=node.name,
                    bases=self._extract_base_classes(node),
                    methods=self._extract_class_methods(node),
                    docstring=ast.get_docstring(node),
                    decorators=[self._format_decorator(d) for d in node.decorator_list],
                    location=CodeLocation(
                        line=node.lineno,
                        column=node.col_offset,
                        end_line=node.end_lineno,
                        end_column=node.end_col_offset
                    ),
                    complexity=self._calculate_class_complexity(node)
                )
                
                # Add to analysis
                analysis['classes'].append({
                    'name': class_info.name,
                    'bases': class_info.bases,
                    'methods': class_info.methods,
                    'docstring': class_info.docstring,
                    'decorators': class_info.decorators,
                    'line_number': class_info.location.line,
                    'complexity': class_info.complexity
                })
    
    def _extract_class_methods(self, node: ast.ClassDef) -> List[Dict]:
        """Extract detailed method information from a class."""
        methods = []
        
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                method_info = {
                    'name': item.name,
                    'docstring': ast.get_docstring(item),
                    'decorators': [self._format_decorator(d) for d in item.decorator_list],
                    'is_property': self._is_property(item),
                    'is_classmethod': self._is_classmethod(item),
                    'is_staticmethod': self._is_staticmethod(item),
                    'line_number': item.lineno
                }
                methods.append(method_info)
        
        return methods
    
    def _process_comments(self, content: str, analysis: dict) -> None:
        """Extract and categorize comments and TODOs."""
        lines = content.split('\n')
        
        # Track multiline strings/comments
        in_multiline = False
        multiline_content = []
        multiline_start = 0
        
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            
            # Handle multiline strings that might be docstrings
            if stripped.startswith('"""') or stripped.startswith("'''"):
                if not in_multiline and not (stripped.endswith('"""') or stripped.endswith("'''")):
                    in_multiline = True
                    multiline_start = i
                    multiline_content = [stripped]
                    continue
                elif in_multiline:
                    in_multiline = False
                    multiline_content.append(stripped)
                    # Only process if it's a comment, not a docstring
                    if not self._is_docstring(content, multiline_start):
                        comment_text = '\n'.join(multiline_content)
                        self._add_comment_or_todo(comment_text, multiline_start, analysis)
                    continue
            
            if in_multiline:
                multiline_content.append(stripped)
                continue
            
            # Handle single line comments
            if stripped.startswith('#'):
                comment_text = stripped[1:].strip()
                self._add_comment_or_todo(comment_text, i, analysis)

    def _calculate_function_complexity(self, node: ast.FunctionDef) -> int:
        """Calculate cyclomatic complexity for a function."""
        complexity = 1  # Base complexity
        
        for child in ast.walk(node):
            # Control flow increases complexity
            if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
            elif isinstance(child, ast.ExceptHandler):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                if isinstance(child.op, ast.And):
                    complexity += len(child.values) - 1
            elif isinstance(child, ast.Return):
                if isinstance(child.value, ast.IfExp):
                    complexity += 1
        
        return complexity
    
    def _calculate_class_complexity(self, node: ast.ClassDef) -> int:
        """Calculate complexity for a class."""
        complexity = len(node.bases)  # Inheritance adds complexity
        
        # Add complexity of methods
        for child in node.body:
            if isinstance(child, ast.FunctionDef):
                complexity += self._calculate_function_complexity(child)
        
        return complexity
    
    def _calculate_module_complexity(self, tree: ast.AST) -> int:
        """Calculate overall module complexity."""
        complexity = 0
        
        # Add complexity of all functions and classes
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                complexity += self._calculate_function_complexity(node)
            elif isinstance(node, ast.ClassDef):
                complexity += self._calculate_class_complexity(node)
        
        return complexity

    def _extract_base_classes(self, node: ast.ClassDef) -> List[str]:
        """Extract and format base class information."""
        bases = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                bases.append(base.id)
            elif isinstance(base, ast.Attribute):
                bases.append(f"{self._format_dotted_name(base)}")
            elif isinstance(base, ast.Call):
                # Handle metaclasses and parameterized bases
                if isinstance(base.func, ast.Name):
                    bases.append(f"{base.func.id}(...)")
                elif isinstance(base.func, ast.Attribute):
                    bases.append(f"{self._format_dotted_name(base.func)}(...)")
        return bases
    
    def _format_dotted_name(self, node: ast.Attribute) -> str:
        """Format attribute access into dotted name."""
        parts = []
        current = node
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
        return '.'.join(reversed(parts))
    
    def _format_annotation(self, node: Optional[ast.AST]) -> Optional[str]:
        """Format type annotations into string representation."""
        if node is None:
            return None
            
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return self._format_dotted_name(node)
        elif isinstance(node, ast.Subscript):
            value = self._format_annotation(node.value)
            if isinstance(node.slice, ast.Index):
                # Handle Python 3.8 style annotations
                slice_value = self._format_annotation(node.slice.value)
            else:
                # Handle Python 3.9+ style annotations
                slice_value = self._format_annotation(node.slice)
            return f"{value}[{slice_value}]"
        elif isinstance(node, ast.Tuple):
            elements = [self._format_annotation(elt) for elt in node.elts]
            return f"Tuple[{', '.join(elements)}]"
        elif isinstance(node, ast.List):
            elements = [self._format_annotation(elt) for elt in node.elts]
            return f"List[{', '.join(elements)}]"
        elif isinstance(node, ast.Constant):
            return repr(node.value)
        elif isinstance(node, ast.BinOp):
            if isinstance(node.op, ast.BitOr):
                left = self._format_annotation(node.left)
                right = self._format_annotation(node.right)
                return f"Union[{left}, {right}]"
        elif isinstance(node, ast.Index):
            # Handle Python 3.8 style index nodes directly
            return self._format_annotation(node.value)
        return str(node)


    
    def _format_import(self, import_info: ImportInfo) -> str:
        """Format import information into string representation."""
        if import_info.module:
            result = f"from {import_info.module} import {import_info.name}"
        else:
            result = f"import {import_info.name}"
        
        if import_info.alias:
            result += f" as {import_info.alias}"
            
        return result
    
    def _format_argument(self, arg: FunctionArgument) -> str:
        """Format function argument into string representation."""
        parts = []
        
        # Handle special argument types
        if arg.is_vararg:
            parts.append('*' + arg.name)
        elif arg.is_kwarg:
            parts.append('**' + arg.name)
        else:
            parts.append(arg.name)
        
        # Add type annotation if present
        if arg.type_annotation:
            parts[0] += f": {arg.type_annotation}"
        
        # Add default value if present
        if arg.default_value:
            parts[0] += f" = {arg.default_value}"
        
        return parts[0]
    
    def _format_decorator(self, node: ast.expr) -> str:
        """Format decorator into string representation."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                return f"{node.func.id}(...)"
            elif isinstance(node.func, ast.Attribute):
                return f"{self._format_dotted_name(node.func)}(...)"
        elif isinstance(node, ast.Attribute):
            return self._format_dotted_name(node)
        return "unknown_decorator"
    
    def _extract_source(self, content: str, location: CodeLocation) -> str:
        """Extract source code for a node based on its location."""
        lines = content.splitlines()
        if location.end_line:
            return '\n'.join(lines[location.line-1:location.end_line])
        return lines[location.line-1]
    
    def _is_docstring(self, content: str, line_number: int) -> bool:
        """Check if a multiline string is a docstring."""
        lines = content.splitlines()
        
        # Look for the previous non-empty line
        current_line = line_number - 2  # -2 because line_number is 1-based
        while current_line >= 0 and not lines[current_line].strip():
            current_line -= 1
        
        if current_line < 0:
            return True  # Module-level docstring
            
        prev_line = lines[current_line].strip()
        return prev_line.endswith(':') or prev_line.startswith('@')
    
    def _add_comment_or_todo(self, text: str, line: int, analysis: dict) -> None:
        """Add a comment as either a regular comment or TODO based on content."""
        text = text.strip()
        if any(marker in text.upper() for marker in ['TODO', 'FIXME', 'XXX']):
            analysis['todos'].append({
                'text': text,
                'line': line
            })
        else:
            analysis['comments'].append({
                'text': text,
                'line': line
            })
    
    def _is_property(self, node: ast.FunctionDef) -> bool:
        """Check if a method is a property."""
        return any(
            self._format_decorator(d) in {'property', 'cached_property'}
            for d in node.decorator_list
        )
    
    def _is_classmethod(self, node: ast.FunctionDef) -> bool:
        """Check if a method is a classmethod."""
        return any(
            self._format_decorator(d) == 'classmethod'
            for d in node.decorator_list
        )
    
    def _is_staticmethod(self, node: ast.FunctionDef) -> bool:
        """Check if a method is a staticmethod."""
        return any(
            self._format_decorator(d) == 'staticmethod'
            for d in node.decorator_list
        )