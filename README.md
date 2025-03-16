# CodeLens - Intelligent Code Analysis Tool

CodeLens is an intelligent code analysis tool designed to generate LLM-friendly context from your codebase. With seamless integration and insightful output, it helps developers analyze their projects effectively.

[![PyPI version](https://badge.fury.io/py/llm-code-lens.svg)](https://badge.fury.io/py/llm-code-lens)
[![Python Versions](https://img.shields.io/pypi/pyversions/llm-code-lens.svg)](https://pypi.org/project/llm-code-lens/)

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

## SQL Server Integration

CodeLens supports analyzing SQL Server databases including stored procedures, views, and functions.

### Prerequisites

1. **ODBC Driver**: Install the Microsoft ODBC Driver for SQL Server:
   - Windows: Install "ODBC Driver 17 for SQL Server" from Microsoft
   - Linux: Follow [Microsoft's instructions](https://learn.microsoft.com/en-us/sql/connect/odbc/linux-mac/installing-the-microsoft-odbc-driver-for-sql-server) for your distribution

2. **Database Access**: Ensure you have appropriate permissions to view database objects

### Configuration

Three ways to configure SQL Server access:

1. **Environment Variables**:
   ```bash
   export MSSQL_SERVER=your_server
   export MSSQL_DATABASE=your_database  # Optional
   export MSSQL_USERNAME=your_username
   export MSSQL_PASSWORD=your_password
   ```

2. **Command Line Options**:
   ```bash
   llmcl --sql-server "server_name" --sql-database "database_name"
   ```

3. **Configuration File** (recommended for teams):
   Create a `sql-config.json`:
   ```json
   {
     "server": "server_name",
     "database": "database_name",
     "env": {
       "MSSQL_USERNAME": "username",
       "MSSQL_PASSWORD": "password"
     }
   }
   ```
   Then use:
   ```bash
   llmcl --sql-config sql-config.json
   ```

### Usage Examples

Analyze both files and SQL Server:
```bash
llmcl --sql-server "server_name" --sql-database "database_name"
```

Export full object definitions:
```bash
llmcl --sql-server "server_name" --sql-database "database_name" --full
```

Analyze specific database with JSON output:
```bash
llmcl --sql-config sql-config.json --format json
```

### Output Structure

SQL analysis includes:
- Object inventory (procedures, views, functions)
- Dependencies between objects
- Complexity metrics
- TODOs and comments
- Parameter analysis
- Full object definitions (with --full flag)

### Security Notes

- Never commit SQL configuration files with credentials
- Use environment variables or secure secret management
- Consider using integrated security when possible
- Ensure minimum required permissions for analysis

---

## Requirements

- Python >= 3.8

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
   pip install -e ".[dev]"
   ```

### Running Tests

Run the test suite using:
```bash
pytest
```

### Publishing to PyPI

For instructions on how to publish the package to PyPI, see [Publishing Guide](docs/publishing.md).

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

