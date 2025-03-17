# CodeLens - Intelligent Code Analysis Tool

CodeLens is an intelligent code analysis tool designed to generate LLM-friendly context from your codebase. With seamless integration and insightful output, it helps developers analyze their projects effectively.

[![PyPI version](https://badge.fury.io/py/llm-code-lens.svg)](https://badge.fury.io/py/llm-code-lens)
[![Python Versions](https://img.shields.io/pypi/pyversions/llm-code-lens.svg)](https://pypi.org/project/llm-code-lens/)

---

## Features

- **Multi-language support**: Analyzes Python and JavaScript/TypeScript codebases.
- **LLM-optimized analysis**: Extracts key elements like functions, classes, dependencies, and comments.
- **Interactive file selection**: Choose which files and directories to include in your analysis.
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
Simply run:
```bash
llmcl
```

This launches the interactive interface where you can:
- Navigate and select files/directories to analyze
- Configure all analysis options
- Save your settings for future runs

The tool now always opens in interactive mode for improved usability.

### Interactive Interface
CodeLens now features an always-on interactive interface that provides:
- File/directory navigation and selection
- Analysis option configuration through easy-to-use menus
- Persistent settings between runs
- Visual feedback on selection status

The interactive interface allows you to:
- Navigate through your project structure with arrow keys
- Expand/collapse directories with Right/Left arrows
- Include or exclude specific files and directories with Space
- Toggle format, export, and debug options with function keys
- Save your selection for future runs automatically

Key shortcuts in the interactive interface:
- **Up/Down**: Navigate files and directories
- **Right**: Expand a directory
- **Left**: Collapse a directory
- **Space**: Toggle inclusion/exclusion of the selected item
- **F1**: Toggle output format (txt/json)
- **F2**: Toggle full export mode
- **F3**: Toggle debug mode
- **Enter**: Confirm selection and start analysis
- **Q**: Quit without saving

### Advanced Options
All options are available directly in the interactive interface:

- **Format**: Toggle between text and JSON output (F1)
- **Full Export**: Enable/disable full file content export (F2)
- **Debug**: Enable/disable debug output (F3)
- **SQL Connection**: Configure SQL server connections

All settings persist between runs, eliminating the need to specify command-line options repeatedly.

For automation scenarios, all command-line options still work:
```bash
llmcl --format json --full --debug
```

### Version Checking
CodeLens now automatically checks for newer versions on PyPI and notifies you when an update is available. This check:
- Runs silently in the background
- Only notifies when newer versions exist
- Provides upgrade instructions
- Works offline with no errors or delays

This feature ensures you always know when new features and improvements are available.

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

## Interactive Menu Controls

The interactive interface provides intuitive controls for navigating your project and configuring analysis options:

- **Up/Down Arrow Keys**: Navigate through files and directories
- **Right Arrow**: Expand a directory
- **Left Arrow**: Collapse a directory
- **Space**: Toggle inclusion/exclusion of the selected item
- **Tab**: Switch between Files and Options sections
- **F1-F5**: Toggle or edit various analysis options
- **Enter**: Confirm selection and start analysis
- **Q**: Quit without saving

By default, all files are included. Use Space to exclude specific files or directories.
Your selection and settings are saved between runs, so you don't have to reconfigure everything each time.

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

