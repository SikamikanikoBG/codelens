## [0.6.1] - 2025-06-14

### Added
- Bumped version to 0.6.1
- Added Verbose option for detailed debugging
- Added custome LLM provider

### Enhanced
- Updated version information in all relevant files

### Technical
- Ensured consistency across all version references

## [0.6.0] - 2025-06-13

### Added
- Improved speed efficiency performance with optimized Tree-sitter integration
- Enhanced parsing engine for faster code analysis (up to 2x improvement)
- Added support for Python 3.12 in all dependencies and configurations

### Enhanced
- Optimized file filtering and path handling for large repositories
- Improved memory usage during analysis operations
- Refactored core analyzer classes for better performance

### Technical
- Updated Tree-sitter dependencies to latest versions (0.20.0)
- Added Python 3.12 compatibility checks in all modules
- Enhanced benchmarking tools for performance testing

## [0.5.16] - 2025-05-26

### Added
- Intelligent size reduction for large codebases (>10,000 LOC)
- Condensed formatting automatically applied to reduce analysis output by 60-75%
- Smart filtering of verbose elements while preserving essential architectural information

### Enhanced
- File analysis formatting now adapts based on total project size
- TODO sections grouped by priority with summary counts for large projects
- Function listings limited to complex functions (complexity > 5) in large codebases
- Import/export statements filtered out for large projects to reduce noise

### Technical
- Added `is_large_codebase` detection based on total LOC threshold
- Enhanced formatters with size-aware conditional rendering
- Preserved all critical business logic and architectural insights

## [0.5.15] - 2025-05-25

### Added
- Real-time progress bars for analysis operations with file-by-file progress indicators
- System information context (OS, Python version, architecture) for enhanced LLM suggestions
- Enhanced LLM integration with improved instruction format for effortless code editing
- Two-step workflow: AI requests current files before suggesting edits for 100% accuracy
- Search-and-replace format for all code suggestions to minimize editing effort
- Progress tracking for tree generation and full content export operations

### Changed
- Improved user experience with visual progress indicators during long operations
- Enhanced system prompt with better workflow instructions for AI interactions
- Progress bars now show current file being processed and elapsed time
- Better feedback during analysis with spinner animations and percentage completion

### Fixed
- Fixed AnalysisResult initialization error with tree parameter
- Improved error handling for tree generation and progress tracking
- Enhanced stability during long-running analysis operations

## [0.5.14] - 2025-05-25

### Added
- Added comprehensive default ignores for Python, JavaScript, Node.js, TypeScript, and other top 15 popular languages
- Enhanced exclusions for system files and directories created by various languages
- Extended `should_ignore` functionality to exclude subfolders based on default ignores
- Added specific exclusions for Next.js files (.next directory and next-env.d.ts)

### Changed
- Improved .gitignore handling and refactored cli.py for better ignore patterns

### Fixed
- N/A

## [0.5.12] - 2025-04-10

### Added
- Improved folder scanning UI with real-time progress bar and cancellation option
- Added version update notification and automatic update feature in menu
- Enhanced ChatGPT integration with URL query parameter for pre-populating content

### Changed
- Optimized directory scanning process for large repositories
- Improved user feedback during scanning with detailed progress information
- Enhanced visual indicators for scanning progress with animation

### Fixed
- Fixed UI freezing during scanning of large repositories
- Improved cancellation mechanism for directory scanning
- Enhanced error handling during scanning process

## [0.5.11] - 2025-04-09

### Changed
- Simplified file selection interface: Space key now always performs full selection with all sub-elements
- Removed partial selection functionality for more intuitive user experience
- Updated menu controls and documentation to reflect the simplified selection model

## [0.5.10] - 2025-04-09

### Fixed
- Fixed critical issues with directory selection logic for more reliable file inclusion/exclusion
- Improved handling of parent-child relationships in partially selected directories
- Enhanced recursive selection and exclusion to properly handle all edge cases
- Fixed inconsistencies in selection state indicators for better user experience
- Corrected file selection behavior for files within common directories

### Changed
- Optimized directory traversal for better performance with large repositories
- Improved error handling during recursive operations to prevent crashes
- Enhanced visual feedback for selection states with clearer indicators

## [0.5.9] - 2025-04-08

### Added
- Implemented smarter toggling mechanism with partial selection of directories
- Added new visual indicator [~] for partially selected directories
- Implemented Ctrl+Space shortcut for fully selecting directories and all contents
- Enhanced parent-child relationship tracking for more intuitive selection behavior
- Added automatic parent directory state updates based on children selection

### Changed
- Improved directory selection UI with clearer visual indicators
- Enhanced menu controls with better documentation of selection options
- Updated state persistence to include partial selection information

## [0.5.8] - 2025-04-08

### Added
- Implemented partial directory selection with new [~] indicator for more granular control
- Added Ctrl+Space shortcut for fully selecting directories and all their contents
- Enhanced directory selection with smarter parent-child relationship tracking

### Fixed
- Fixed issue with recursive selection of children when including previously excluded directories
- Improved directory selection logic to properly handle common directories
- Enhanced recursive inclusion to ensure all children are properly selected

## [0.5.7] - 2025-04-08

### Performance Improvements
- Introduced performance flags for directory scanning
- Optimized menu interactions for large repositories
- Reduced unnecessary filesystem operations
- Implemented lazy scanning and caching mechanisms

### Added
- New `scan_complete` and `dirty_scan` flags in menu state management
- Enhanced directory selection with more efficient tracking
- Improved recursive inclusion/exclusion logic

### Changed
- Refactored directory scanning to minimize redundant operations
- Updated menu state management for better performance
- Optimized file selection and exclusion processes

### Fixed
- Resolved performance bottlenecks in large project directory scanning
- Improved memory efficiency in directory traversal
- Fixed inconsistent directory selection behavior

## [0.5.5] - 2025-04-08

### Added
- Implemented recursive directory selection for improved usability
- Added automatic selection/deselection of all subdirectories and files when toggling a directory

### Changed
- Improved UI to clearly indicate recursive selection behavior
- Enhanced status messages to show recursive selection functionality
- Updated controls description to reflect recursive selection capability

### Fixed
- Fixed inconsistent selection behavior when toggling directories
- Improved directory traversal logic for more intuitive selection experience

## [0.5.4] - 2025-04-08

### Added
- Added ability to toggle exclusion of common directories in the interactive menu
- Implemented explicit selection of directories that would normally be excluded
- Added visual indicators for explicitly selected directories

### Fixed
- Fixed missing path_str conversion in menu rendering logic
- Improved menu UI with clearer selection indicators
- Enhanced status messages to show both excluded and explicitly included items

## [0.5.3] - 2025-04-07

### Added
- Expanded directory exclusion list for improved file selection
- Added comprehensive exclusion patterns for Python, JavaScript, Java, and other languages
- Added automatic exclusion of the .codelens directory

### Fixed
- Improved menu selection logic for better handling of excluded directories
- Fixed issue with common directories being selected by default

## [0.5.2] - 2025-04-07

### Fixed
- Implemented lazy loading for SQL Server analyzer to prevent crashes when ODBC drivers are missing
- Improved error handling for SQL-related functionality
- Added graceful degradation when SQL dependencies are not available

## [0.5.1] - 2025-03-23

### Fixed
- Added pyperclip dependency for clipboard operations with LLM providers
- Improved error handling for missing dependencies
- Fixed runtime package installation issues

## [0.5.0] - 2025-03-23

### Added
- Added option to open analysis results directly in LLM providers (Claude, ChatGPT, Gemini)
- Implemented cross-platform browser content sharing for LLM providers
- Added 'none' option for LLM provider to skip browser opening
- Enhanced system prompt with formatting instructions for developers
- Added comprehensive tests for menu, drawing, and CLI filtering modules
- Added validation and debug logging for file selection and filtering

### Changed
- Improved menu usability with Escape key, section indicators, and UI cleanup
- Enhanced LLM provider integration with clipboard and improved user guidance
- Simplified LLM provider file copying with single clipboard message
- Consolidated utility functions and removed duplicated code

### Fixed
- Fixed missing subprocess import in cli.py
- Corrected option cursor and LLM provider handling in menu navigation
- Fixed LLM provider option handling and browser opening
- Fixed undefined `result_dict` reference in `_combine_fs_results`
- Simplified result combination logic in CLI filtering
- Fixed test failures in CLI filtering and result combination
- Added missing curses import in test_menu.py
- Fixed conftest and import paths for proper test coverage

## [0.4.1] - 2025-03-17

### Added
- Made interactive mode the default interface
- Added version check notification for newer PyPI versions
- Integrated CLI arguments into the interactive interface

### Changed
- Improved user experience with always-on interactive menu
- Settings now persist between runs in the interactive menu

## [0.4.0] - 2025-01-22

### Added
- Interactive file selection menu for targeted analysis
- Persistent selection state between runs
- Support for hidden files/directories in the selection menu
- Improved handling of excluded paths in full content export

### Changed
- All files are now included by default in interactive mode
- Enhanced terminal compatibility for Windows and Unix systems

### Fixed
- Fixed menu display issues with terminal encoding
- Resolved issues with interactive selection not being respected in analysis
- Fixed handling of paths with special characters

## [0.3.0] - 2025-01-15

### Added
- Enable analysis of SQL files and objects.

### Changed
- Updated pre-commit hook installation script for better compatibility.
- Improved code metrics aggregation for more accurate insights.
- Enhanced documentation coverage and clarity.

### Fixed
- Resolved issues with directory deletion and creation in the output process.
- Fixed bugs related to CLI error handling and debug mode.
- Addressed minor formatting issues in the generated analysis reports.

## [0.2.1] - 2025-01-08

### Added
- n/a

### Changed
- n/a

### Fixed
- Minor documentation improvements.

## [0.2.0] - 2025-01-08

### Added
- Added support for the `--full` feature in the CLI to export full file contents in token-limited chunks.
- Integrated pre-commit hook for running tests before committing.
## [0.2.1] - 2025-01-08

### Added
- n/a

### Changed
- n/a

### Fixed
- Minor documentation improvements.

## [0.2.0] - 2025-01-08

### Added
- Added support for the `--full` feature in the CLI to export full file contents in token-limited chunks.
- Integrated pre-commit hook for running tests before committing.
- Enhanced test cases for improved coverage and reliability.

### Changed
- Improved CLI usability for handling large projects with seamless file content exports.

### Fixed
- Minor performance improvements in the `ProjectAnalyzer` for better insights generation.

## [0.1.1] - 2025-01-07

### Added
- Python requirements lowered to 3.6.

### Changed
- n/a

### Fixed
- n/a

## [0.1.0] - 2025-01-07

### Added
- Initial version.

### Changed
- n/a

### Fixed
- n/a
