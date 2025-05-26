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
        """Extract imports and exports with simplified patterns."""

        # Simplified import patterns - process line by line for better performance
        for line_num, line in enumerate(content.splitlines(), 1):
            line = line.strip()
            if line.startswith('import '):
                analysis['imports'].append(line)
            elif line.startswith('export '):
                analysis['exports'].append(line)

    def _extract_functions(self, content: str, analysis: dict) -> None:
        """Extract functions with simplified patterns."""

        # Simplified function extraction - process line by line
        for line_num, line in enumerate(content.splitlines(), 1):
            line = line.strip()

            # Regular function declarations
            if line.startswith('function ') or ' function ' in line:
                match = re.search(r'function\s+(\w+)', line)
                if match:
                    analysis['functions'].append({
                        'name': match.group(1),
                        'params': [],
                        'return_type': None,
                        'line_number': line_num,
                        'is_async': 'async' in line
                    })

            # Arrow functions
            elif '=>' in line and ('const ' in line or 'let ' in line or 'var ' in line):
                match = re.search(r'(?:const|let|var)\s+(\w+)\s*=', line)
                if match:
                    analysis['functions'].append({
                        'name': match.group(1),
                        'params': [],
                        'return_type': None,
                        'line_number': line_num,
                        'is_async': 'async' in line
                    })

    def _extract_classes(self, content: str, analysis: dict) -> None:
        """Extract classes with simplified patterns."""

        # Simplified class extraction - process line by line
        for line_num, line in enumerate(content.splitlines(), 1):
            line = line.strip()
            if line.startswith('class '):
                match = re.search(r'class\s+(\w+)', line)
                if match:
                    extends_match = re.search(r'extends\s+(\w+)', line)
                    analysis['classes'].append({
                        'name': match.group(1),
                        'extends': extends_match.group(1) if extends_match else None,
                        'line_number': line_num
                    })

    def _extract_react_components(self, content: str, analysis: dict) -> None:
        """Extract React components with simplified patterns."""

        # Simplified component extraction - process line by line
        for line_num, line in enumerate(content.splitlines(), 1):
            line = line.strip()

            # Function components (must start with capital letter)
            if ('const ' in line or 'function ' in line) and '=>' in line:
                match = re.search(r'(?:const|function)\s+([A-Z]\w+)', line)
                if match:
                    analysis['components'].append({
                        'name': match.group(1),
                        'type': 'function',
                        'line_number': line_num,
                        'has_jsx': '<' in line
                    })

            # Class components
            elif line.startswith('class ') and 'extends' in line and ('Component' in line or 'PureComponent' in line):
                match = re.search(r'class\s+([A-Z]\w+)', line)
                if match:
                    analysis['components'].append({
                        'name': match.group(1),
                        'type': 'class',
                        'line_number': line_num,
                        'has_jsx': False
                    })

    def _extract_react_hooks(self, content: str, analysis: dict) -> None:
        """Extract React hooks usage with simplified patterns."""

        # Simplified hook extraction - process line by line
        standard_hooks = ['useState', 'useEffect', 'useContext', 'useReducer', 'useCallback', 'useMemo', 'useRef', 'useImperativeHandle', 'useLayoutEffect', 'useDebugValue']

        for line_num, line in enumerate(content.splitlines(), 1):
            for hook in standard_hooks:
                if hook + '(' in line:
                    analysis['hooks'].append({
                        'name': hook,
                        'line_number': line_num,
                        'is_custom': False
                    })

            # Custom hooks (simplified - look for use + CapitalLetter pattern)
            custom_match = re.search(r'(use[A-Z]\w*)\s*\(', line)
            if custom_match:
                hook_name = custom_match.group(1)
                if hook_name not in standard_hooks:
                    analysis['hooks'].append({
                        'name': hook_name,
                        'line_number': line_num,
                        'is_custom': True
                    })

    def _extract_typescript_constructs(self, content: str, analysis: dict) -> None:
        """Extract TypeScript interfaces and types with simplified patterns."""

        # Simplified TypeScript extraction - process line by line
        for line_num, line in enumerate(content.splitlines(), 1):
            line = line.strip()

            # Interface declarations
            if line.startswith('interface '):
                match = re.search(r'interface\s+(\w+)', line)
                if match:
                    extends_match = re.search(r'extends\s+(\w+)', line)
                    analysis['interfaces'].append({
                        'name': match.group(1),
                        'extends': extends_match.group(1) if extends_match else None,
                        'line_number': line_num
                    })

            # Type aliases
            elif line.startswith('type ') and '=' in line:
                match = re.search(r'type\s+(\w+)', line)
                if match:
                    analysis['types'].append({
                        'name': match.group(1),
                        'definition': line.split('=', 1)[1].strip().rstrip(';'),
                        'line_number': line_num
                    })

    def _extract_comments_todos(self, content: str, analysis: dict) -> None:
        """Extract comments and TODOs with simplified patterns."""

        # Simplified comment extraction - process line by line
        for line_num, line in enumerate(content.splitlines(), 1):
            # Single-line comments
            if '//' in line:
                comment_start = line.find('//')
                comment = line[comment_start + 2:].strip()
                if comment:
                    # Check for TODOs/FIXMEs
                    if any(marker in comment.upper() for marker in ['TODO', 'FIXME', 'XXX', 'HACK', 'BUG']):
                        analysis['todos'].append({
                            'line': line_num,
                            'text': comment
                        })
                    else:
                        analysis['comments'].append({
                            'line': line_num,
                            'text': comment
                        })

        # Multi-line comments (simplified - just find start/end markers)
        in_multiline = False
        multiline_start = 0
        multiline_content = []

        for line_num, line in enumerate(content.splitlines(), 1):
            if '/*' in line and not in_multiline:
                in_multiline = True
                multiline_start = line_num
                multiline_content = [line[line.find('/*') + 2:]]
            elif '*/' in line and in_multiline:
                in_multiline = False
                multiline_content.append(line[:line.find('*/')])
                comment = ' '.join(multiline_content).strip()
                if comment:
                    if any(marker in comment.upper() for marker in ['TODO', 'FIXME', 'XXX', 'HACK', 'BUG']):
                        analysis['todos'].append({
                            'line': multiline_start,
                            'text': comment
                        })
                    else:
                        analysis['comments'].append({
                            'line': multiline_start,
                            'text': comment
                        })
                multiline_content = []
            elif in_multiline:
                multiline_content.append(line.strip('* '))
