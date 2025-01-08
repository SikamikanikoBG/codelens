# CodeLens - Intelligent Code Analysis Tool

CodeLens is an intelligent code analysis tool designed to generate LLM-friendly context from your codebase. With seamless integration and insightful output, it helps developers analyze their projects effectively.

---

## Features

- **Multi-language support**: Analyzes Python and JavaScript/TypeScript codebases.
- **LLM-optimized analysis**: Extracts key elements like functions, classes, dependencies, and comments.
- **Token-friendly outputs**: Splits large file contents into token-limited chunks for LLM compatibility.
- **Seamless CLI**: Easy-to-use command-line interface with multiple options.
- **TODO tracking**: Highlights TODOs and FIXMEs for better code maintenance.
- **Pre-commit hook integration**: Automatically runs tests before committing to ensure code quality.

---

## Installation

To install CodeLens, use pip:

```bash
pip install llm-code-lens
```

---

## Usage

### Basic Usage
Analyze the current directory:
```bash
llmcl
```

Analyze a specific directory:
```bash
llmcl path/to/your/code
```

Specify output format (default is `txt`):
```bash
llmcl --format json
```

### Advanced Options
- Export full file contents in token-limited chunks:
  ```bash
  llmcl --full
  ```

- Enable debug output:
  ```bash
  llmcl --debug
  ```

- Customize the output directory:
  ```bash
  llmcl --output /path/to/output
  ```

---

## Configuration

CodeLens requires no additional configuration. However, you can integrate it with pre-commit hooks for seamless testing workflows.

### Setting up Pre-commit Hooks

1. Navigate to the `scripts/` directory.
2. Run the following script to install the pre-commit hook:
   ```bash
   python scripts/install-hooks.py
   ```
3. The pre-commit hook will automatically run tests using `pytest` before committing.

---

## Output Structure

CodeLens creates a `.codelens` directory containing the following:
- **`analysis.txt` (or `.json`)**: Complete codebase analysis, including:
  - Project summary
  - Key insights
  - File structure and context
  - Dependencies
  - TODOs and comments
- **Full file content files**: When using the `--full` option, the full content of files is exported in token-limited chunks.

---

## Requirements

- Python >= 3.6

---

## Development

### Setting up the Environment

1. Clone the repository:
   ```bash
   git clone https://github.com/SikamikanikoBG/codelens.git
   ```
2. Navigate to the project directory:
   ```bash
   cd codelens
   ```
3. Create a virtual environment and activate it:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Running Tests

Run the test suite using:
```bash
pytest
```

---

## Contributing

We welcome contributions! To get started:
1. Fork the repository.
2. Create a new branch for your feature or fix.
3. Submit a pull request with a detailed description of your changes.

---

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

## Support

For issues or feature requests, please visit our [GitHub Issues](https://github.com/SikamikanikoBG/codelens/issues).

