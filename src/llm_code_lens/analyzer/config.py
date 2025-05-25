"""
Configuration file analyzers for project context.
"""

import json
from pathlib import Path
from typing import Dict, Optional, List

try:
    import tomli
except ImportError:
    tomli = None

def analyze_package_json(file_path: Path) -> Optional[Dict]:
    """Extract key information from package.json."""
    if not file_path.exists():
        return None

    try:
        with open(file_path, 'r') as f:
            data = json.load(f)

        return {
            'name': data.get('name'),
            'version': data.get('version'),
            'description': data.get('description'),
            'main': data.get('main'),
            'scripts': list(data.get('scripts', {}).keys()),
            'dependencies': list(data.get('dependencies', {}).keys()),
            'devDependencies': list(data.get('devDependencies', {}).keys()),
            'framework_indicators': _detect_frameworks(data)
        }
    except (json.JSONDecodeError, Exception):
        return {'error': 'Failed to parse package.json'}

def _detect_frameworks(package_data: dict) -> List[str]:
    """Detect frameworks based on dependencies."""
    frameworks = []
    all_deps = {**package_data.get('dependencies', {}), **package_data.get('devDependencies', {})}

    if 'react' in all_deps: frameworks.append('React')
    if 'next' in all_deps: frameworks.append('Next.js')
    if 'vue' in all_deps: frameworks.append('Vue.js')
    if 'angular' in all_deps: frameworks.append('Angular')
    if 'typescript' in all_deps: frameworks.append('TypeScript')
    if 'tailwindcss' in all_deps: frameworks.append('Tailwind CSS')

    return frameworks

def analyze_tsconfig(file_path: Path) -> Optional[Dict]:
    """Extract TypeScript configuration."""
    if not file_path.exists():
        return None

    try:
        with open(file_path, 'r') as f:
            # Simple JSON parsing (ignoring comments for now)
            content = f.read()
            # Remove comments (basic approach)
            lines = [line.split('//')[0].strip() for line in content.split('\n')]
            clean_content = '\n'.join(lines)
            data = json.loads(clean_content)

        compiler_options = data.get('compilerOptions', {})
        return {
            'target': compiler_options.get('target'),
            'module': compiler_options.get('module'),
            'jsx': compiler_options.get('jsx'),
            'strict': compiler_options.get('strict'),
            'baseUrl': compiler_options.get('baseUrl'),
            'paths': bool(compiler_options.get('paths')),
            'include': data.get('include', []),
            'exclude': data.get('exclude', [])
        }
    except (json.JSONDecodeError, Exception):
        return {'error': 'Failed to parse tsconfig.json'}

def extract_readme_summary(file_path: Path) -> Optional[Dict]:
    """Extract first few lines of README for project description."""
    readme_files = ['README.md', 'README.txt', 'README.rst', 'README']

    for readme_name in readme_files:
        readme_path = file_path / readme_name
        if readme_path.exists():
            try:
                with open(readme_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()[:10]  # First 10 lines
                    content = ''.join(lines).strip()

                return {
                    'filename': readme_name,
                    'summary': content[:500] + '...' if len(content) > 500 else content,
                    'has_badges': '[![' in content,
                    'has_installation': any(word in content.lower() for word in ['install', 'setup', 'getting started'])
                }
            except Exception:
                continue

    return None
