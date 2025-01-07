Intelligent code analysis tool that generates LLM-friendly context from your codebase.

## Installation

```bash
pip install codelens
```

## Usage

Basic usage - analyze current directory:
```bash
codelens
```

Analyze specific directory:
```bash
codelens path/to/your/code
```

Specify output format:
```bash
codelens --format json  # or txt (default)
```

## Features

- Intelligent code analysis for Python and JavaScript/TypeScript
- LLM-optimized output format
- Extracts:
  - Code structure
  - Functions and classes
  - Dependencies
  - TODOs and comments
  - Key insights
- No configuration needed
- Fast and lightweight

## Output

CodeLens creates a `.codelens` directory containing:
- `analysis.txt` (or .json): Complete codebase analysis
  - Project summary
  - Key insights
  - File structure with context
  - Dependencies
  - TODOs and comments

## License

MIT

# File: LICENSE
MIT License

Copyright (c) 2024 Your Name

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
