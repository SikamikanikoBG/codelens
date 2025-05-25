# 🔍 CodeLens - Supercharge Your LLM Coding Experience

CodeLens is your AI coding assistant's best friend - an intelligent code analysis tool that transforms your codebase into LLM-optimized context. Stop wasting tokens on irrelevant files or struggling to explain your project structure. CodeLens does the heavy lifting, so you can focus on building great software.

[![PyPI version](https://badge.fury.io/py/llm-code-lens.svg)](https://badge.fury.io/py/llm-code-lens)
[![Python Versions](https://img.shields.io/pypi/pyversions/llm-code-lens.svg)](https://pypi.org/project/llm-code-lens/)
[![Downloads](https://static.pepy.tech/badge/llm-code-lens/month)](https://pepy.tech/project/llm-code-lens)

---

## 🚀 Why CodeLens?

- **Save time and tokens**: Automatically extract the most relevant code context for your LLM
- **Get better answers**: Provide AI with structured insights about your codebase architecture
- **Seamless LLM integration**: One-click sharing with Claude, ChatGPT, Gemini and other LLMs
- **Work smarter**: Identify core files, entry points, and dependencies automatically
- **Maintain with ease**: Track TODOs, complexity hotspots, and technical debt

---

## ✨ Features

- **Multi-language analysis**: Deep insights for Python, JavaScript/TypeScript, and SQL codebases
- **Direct LLM integration**: Send analysis directly to Claude, ChatGPT, or Gemini with one click
- **Smart code extraction**: Identifies core files, entry points, and critical dependencies
- **Interactive selection**: Choose exactly which files and directories to analyze
- **Token optimization**: Splits large files into perfectly-sized chunks for LLM context windows
- **Complexity metrics**: Highlights complex functions and classes that need attention
- **Maintenance tracking**: Collects TODOs, FIXMEs, and technical debt indicators
- **SQL database analysis**: Examines stored procedures, views, and functions
- **Pre-commit integration**: Automatically runs tests before committing

---

## 📦 Installation

```bash
pip install llm-code-lens
```

That's it! No complex configuration needed.

---

## 🎮 Usage

### Quick Start
Simply run:
```bash
llmcl
```

This launches the interactive interface where you can navigate your project, select files, and configure analysis options with just a few keystrokes.

### Workflow

1. **Select files**: Navigate your project and choose what to analyze
2. **Configure options**: Set output format, LLM provider, and other settings
3. **Run analysis**: CodeLens examines your code and generates insights
4. **Send to LLM**: With one click, send everything to your preferred AI assistant

### LLM Integration (Enhanced in v0.5.15!)

CodeLens now integrates directly with popular LLM providers:

```bash
llmcl --open-in-llm claude
```

Or select your provider in the interactive menu:
- **Claude**: Optimized format for Anthropic's Claude
- **ChatGPT**: Perfect context for OpenAI's models
- **Gemini**: Formatted for Google's Gemini
- **None**: Skip browser opening

When analysis completes, CodeLens:
1. Opens your chosen LLM in your default browser
2. Copies the complete analysis to your clipboard
3. Provides a system prompt optimized for code understanding

Just paste and start asking questions about your code!

#### New in v0.5.15: Enhanced AI Workflow
CodeLens now provides an optimized workflow for AI code assistance:

1. **System Context**: Automatically includes your OS, Python version, and architecture
2. **Smart Editing**: AI will ask for current files before suggesting changes (ensuring 100% accuracy)
3. **Effortless Updates**: All suggestions use search-and-replace format for quick implementation
4. **Progress Tracking**: Real-time progress bars show exactly what's happening during analysis

The enhanced system prompt ensures AI assistants provide more accurate, contextual suggestions that work perfectly with your specific development environment.

### Interactive Interface

The intuitive terminal interface lets you:
- **See real-time progress** with detailed progress bars and file-by-file indicators
- Navigate with arrow keys (↑↓←→)
- **Watch progress in real-time** with animated progress bars and current file indicators
- Select files and directories with Space (includes all sub-elements)
- Switch sections with Tab
- Configure options with function keys (F1-F6)
- Confirm with Enter
- Cancel with Escape or Q

All your settings persist between runs, so you can quickly analyze the same files again.

#### Selection States
- **[+]** - Included file or directory
- **[*]** - Explicitly selected file or directory
- **[-]** - Excluded file or directory

### Command Line Options

For CI/CD pipelines or scripting:

```bash
llmcl --format json --full --open-in-llm claude
```

Full options list:
- `--output/-o`: Output directory (default: .codelens)
- `--format/-f`: Output format (txt or json)
- `--full`: Export complete file contents
- `--debug`: Enable detailed logging
- `--sql-server`: SQL Server connection string
- `--sql-database`: Database to analyze
- `--open-in-llm`: LLM provider to open results in

---

## 📊 What You Get

CodeLens generates a comprehensive analysis in the `.codelens` directory:

### 1. Project Overview
- Total files, lines of code, and complexity metrics
- **Visual project tree structure** showing your codebase hierarchy
- Language distribution and project structure
- Entry points and core files identification
- **System environment context** (OS, Python version, architecture)

### 2. Smart Insights
- Architectural patterns detected
- Potential code smells and improvement areas
- Dependency relationships and import graphs

### 3. File-by-File Analysis
- Function and class inventories with complexity scores
- Documentation coverage and quality assessment
- TODOs and technical debt indicators

### 4. Full Content Export (Optional)
- Complete file contents split into token-optimized chunks
- Perfect for providing full context to your LLM

### 5. SQL Analysis (If Configured)
- Stored procedures, views, and functions inventory
- Object dependencies and relationships
- Parameter analysis and complexity metrics

---

## 🛠️ Configuration

### Pre-commit Integration

Set up pre-commit hooks to ensure quality:

```bash
python scripts/install-hooks.py
```

This automatically runs tests before each commit.

### SQL Server Configuration

Three ways to configure SQL analysis:

1. **Environment Variables**:
   ```bash
   export MSSQL_SERVER=your_server
   export MSSQL_DATABASE=your_database
   ```

2. **Command Line**:
   ```bash
   llmcl --sql-server "server_name" --sql-database "database_name"
   ```

3. **Configuration File**:
   Create `sql-config.json` and use:
   ```bash
   llmcl --sql-config sql-config.json
   ```

---

## 💡 Use Cases

### For Developers
- **Onboarding to new projects**: Quickly understand unfamiliar codebases
- **Refactoring planning**: Identify complex areas that need attention
- **Technical debt management**: Track TODOs and maintenance needs
- **Architecture discussions**: Generate insights about code structure

### For LLM Interactions
- **Bug fixing**: Provide perfect context for debugging issues
- **Feature development**: Help LLMs understand where and how to add features
- **Code reviews**: Get AI assistance with reviewing complex changes
- **Documentation**: Generate comprehensive docs from code analysis

### For Teams
- **Knowledge sharing**: Create shareable insights about project structure
- **Consistent context**: Ensure everyone provides similar context to LLMs
- **Codebase health**: Track metrics over time to measure improvement
- **SQL analysis**: Understand database objects without direct access

---

## 🧩 SQL Server Integration

CodeLens provides deep analysis of SQL Server databases:

### Prerequisites
- Microsoft ODBC Driver for SQL Server
- Appropriate database permissions

### What You Get
- Complete inventory of stored procedures, views, and functions
- Parameter analysis and usage patterns
- Complexity metrics and dependency mapping
- Full object definitions with the `--full` flag

### Security Best Practices
- Use environment variables for credentials
- Consider integrated security when possible
- Apply least-privilege principles for analysis

---

## 🔧 Development

### Setting up the Environment

```bash
git clone https://github.com/SikamikanikoBG/codelens.git
cd codelens
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -e ".[dev]"
```

### Running Tests

```bash
pytest
```

---

## 🤝 Contributing

We welcome contributions! To get started:
1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request with a clear description

---

## 📄 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

## 🆘 Support

For issues or feature requests, please visit our [GitHub Issues](https://github.com/SikamikanikoBG/codelens/issues).

---

## 🌟 Star Us on GitHub!

If CodeLens has helped you, please consider giving us a star on GitHub. It helps others discover the tool and supports its continued development.

