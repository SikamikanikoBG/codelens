# src/codelens/analyzer/javascript.py
import re
from pathlib import Path
from typing import Dict, List

class JavaScriptAnalyzer:
    """Enhanced JavaScript/TypeScript code analyzer with improved regex patterns."""

    def analyze_file(self, file_path: Path) -> dict:
        """Analyze a JavaScript/TypeScript file with enhanced patterns."""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        analysis = {
            'type': 'javascript',
            'imports': [],
            'exports': [],
            'functions': [],
            'classes': [],
            'components': [],  # New: React components
            'hooks': [],       # New: React hooks
            'interfaces': [],  # New: TypeScript interfaces
            'types': [],       # New: TypeScript types
            'comments': [],
            'todos': [],
            'metrics': {
                'loc': len(content.splitlines()),
                'classes': 0,
                'functions': 0,
                'components': 0,  # New metric
                'hooks': 0,       # New metric
                'imports': 0,
            }
        }

        # Enhanced import/export patterns
        self._extract_imports_exports(content, analysis)

        # Enhanced function patterns (including arrow functions, async/await)
        self._extract_functions(content, analysis)

        # Enhanced class patterns
        self._extract_classes(content, analysis)

        # New: React component patterns
        self._extract_react_components(content, analysis)

        # New: React hooks patterns
        self._extract_react_hooks(content, analysis)

        # New: TypeScript interfaces and types
        self._extract_typescript_constructs(content, analysis)

        # Existing comment/TODO extraction
        self._extract_comments_todos(content, analysis)

        # Update metrics
        analysis['metrics']['classes'] = len(analysis['classes'])
        analysis['metrics']['functions'] = len(analysis['functions'])
        analysis['metrics']['components'] = len(analysis['components'])
        analysis['metrics']['hooks'] = len(analysis['hooks'])
        analysis['metrics']['imports'] = len(analysis['imports'])

        return analysis

    def _extract_imports_exports(self, content: str, analysis: dict) -> None:
        """Extract imports and exports with enhanced patterns."""

        # Enhanced import patterns
        import_patterns = [
            # Standard imports: import { a, b } from 'module'
            r'import\s+\{([^}]+)\}\s+from\s+[\'"]([^\'"]+)[\'"]',
            # Default imports: import React from 'react'
            r'import\s+(\w+)\s+from\s+[\'"]([^\'"]+)[\'"]',
            # Namespace imports: import * as React from 'react'
            r'import\s+\*\s+as\s+(\w+)\s+from\s+[\'"]([^\'"]+)[\'"]',
            # Side-effect imports: import 'module'
            r'import\s+[\'"]([^\'"]+)[\'"]',
            # Dynamic imports: import() statements
            r'import\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)',
        ]

        for pattern in import_patterns:
            for match in re.finditer(pattern, content, re.MULTILINE):
                analysis['imports'].append(match.group(0).strip())

        # Enhanced export patterns
        export_patterns = [
            # Named exports: export { a, b }
            r'export\s+\{[^}]+\}',
            # Default exports: export default
            r'export\s+default\s+[^;]+',
            # Direct exports: export const/function/class
            r'export\s+(const|let|var|function|class|interface|type)\s+\w+',
            # Re-exports: export * from 'module'
            r'export\s+\*\s+from\s+[\'"][^\'"]+[\'"]',
        ]

        for pattern in export_patterns:
            for match in re.finditer(pattern, content, re.MULTILINE):
                analysis['exports'].append(match.group(0).strip())

    def _extract_functions(self, content: str, analysis: dict) -> None:
        """Extract functions with enhanced patterns."""

        function_patterns = [
            # Regular function declarations
            r'(?:async\s+)?function\s+(\w+)\s*\(([^)]*)\)\s*(?::\s*([^{]+))?\s*\{',
            # Arrow functions with names
            r'(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\(([^)]*)\)\s*(?::\s*([^=]+))?\s*=>\s*\{',
            # Arrow functions (simple)
            r'(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?([^=]*)\s*=>\s*([^;]+);?',
            # Method definitions in classes/objects
            r'(?:async\s+)?(\w+)\s*\(([^)]*)\)\s*(?::\s*([^{]+))?\s*\{',
        ]

        for pattern in function_patterns:
            for match in re.finditer(pattern, content, re.MULTILINE):
                func_name = match.group(1)
                params = match.group(2) if len(match.groups()) > 1 else ''
                return_type = match.group(3) if len(match.groups()) > 2 else None

                analysis['functions'].append({
                    'name': func_name,
                    'params': [p.strip() for p in params.split(',') if p.strip()],
                    'return_type': return_type.strip() if return_type else None,
                    'line_number': content[:match.start()].count('\n') + 1,
                    'is_async': 'async' in match.group(0)
                })

    def _extract_classes(self, content: str, analysis: dict) -> None:
        """Extract classes with enhanced patterns."""

        class_patterns = [
            # Regular class declarations
            r'class\s+(\w+)(?:\s+extends\s+([^{]+))?\s*\{',
            # Class expressions
            r'(?:const|let|var)\s+\w+\s*=\s*class\s+(\w+)(?:\s+extends\s+([^{]+))?\s*\{'
        ]

        for pattern in class_patterns:
            for match in re.finditer(pattern, content, re.MULTILINE):
                analysis['classes'].append({
                    'name': match.group(1),
                    'extends': match.group(2).strip() if match.group(2) else None,
                    'line_number': content[:match.start()].count('\n') + 1
                })

    def _extract_react_components(self, content: str, analysis: dict) -> None:
        """Extract React components."""

        component_patterns = [
            # Function components
            r'(?:const|function)\s+([A-Z]\w+)\s*[=:]?\s*(?:\([^)]*\))?\s*(?::\s*[^=>{]+)?\s*(?:=>)?\s*\{[^}]*return\s*\(',
            # Function components with JSX
            r'(?:const|function)\s+([A-Z]\w+)\s*[=:]?\s*(?:\([^)]*\))?\s*(?::\s*[^=>{]+)?\s*(?:=>)?\s*\{[^}]*<\w+',
            # Class components
            r'class\s+([A-Z]\w+)\s+extends\s+(?:React\.)?(?:Component|PureComponent)',
        ]

        for pattern in component_patterns:
            for match in re.finditer(pattern, content, re.MULTILINE | re.DOTALL):
                component_name = match.group(1)
                line_number = content[:match.start()].count('\n') + 1

                # Determine component type
                is_class = 'class' in match.group(0)

                analysis['components'].append({
                    'name': component_name,
                    'type': 'class' if is_class else 'function',
                    'line_number': line_number,
                    'has_jsx': '<' in match.group(0) and '>' in match.group(0)
                })

    def _extract_react_hooks(self, content: str, analysis: dict) -> None:
        """Extract React hooks usage."""

        # Common React hooks
        hook_patterns = [
            r'(useState)\s*\(',
            r'(useEffect)\s*\(',
            r'(useContext)\s*\(',
            r'(useReducer)\s*\(',
            r'(useCallback)\s*\(',
            r'(useMemo)\s*\(',
            r'(useRef)\s*\(',
            r'(useImperativeHandle)\s*\(',
            r'(useLayoutEffect)\s*\(',
            r'(useDebugValue)\s*\(',
            # Custom hooks (start with 'use')
            r'(use[A-Z]\w*)\s*\(',
        ]

        for pattern in hook_patterns:
            for match in re.finditer(pattern, content):
                hook_name = match.group(1)
                line_number = content[:match.start()].count('\n') + 1

                analysis['hooks'].append({
                    'name': hook_name,
                    'line_number': line_number,
                    'is_custom': not hook_name.startswith(('useState', 'useEffect', 'useContext', 'useReducer', 'useCallback', 'useMemo', 'useRef'))
                })

    def _extract_typescript_constructs(self, content: str, analysis: dict) -> None:
        """Extract TypeScript interfaces and types."""

        # Interface pattern
        interface_pattern = r'interface\s+(\w+)(?:\s+extends\s+([^{]+))?\s*\{'
        for match in re.finditer(interface_pattern, content):
            analysis['interfaces'].append({
                'name': match.group(1),
                'extends': match.group(2).strip() if match.group(2) else None,
                'line_number': content[:match.start()].count('\n') + 1
            })

        # Type alias pattern
        type_pattern = r'type\s+(\w+)(?:<[^>]*>)?\s*=\s*([^;]+);'
        for match in re.finditer(type_pattern, content):
            analysis['types'].append({
                'name': match.group(1),
                'definition': match.group(2).strip(),
                'line_number': content[:match.start()].count('\n') + 1
            })

    def _extract_comments_todos(self, content: str, analysis: dict) -> None:
        """Extract comments and TODOs (existing functionality enhanced)."""

        comment_patterns = [
            (r'//(.*)$', False),  # Single-line comments
            (r'/\*([^*]*\*+(?:[^/*][^*]*\*+)*/)/', True)  # Multi-line comments
        ]

        for pattern, is_multiline in comment_patterns:
            for match in re.finditer(pattern, content, re.MULTILINE if not is_multiline else re.MULTILINE | re.DOTALL):
                comment = match.group(1).strip()
                line_number = content[:match.start()].count('\n') + 1

                # Check for TODOs/FIXMEs
                if any(marker in comment.upper() for marker in ['TODO', 'FIXME', 'XXX', 'HACK', 'BUG']):
                    analysis['todos'].append({
                        'line': line_number,
                        'text': comment
                    })
                else:
                    analysis['comments'].append({
                        'line': line_number,
                        'text': comment
                    })
