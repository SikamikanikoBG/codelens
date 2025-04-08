## [0.5.7] - 2025-04-08

### Added
- Optimized menu performance for large repositories

### Changed
- Improved directory exclusion logic to only scan once at initialization
- Enhanced recursive selection to work with existing data structures
- Reduced filesystem operations for better performance

### Fixed
- Fixed performance issues with constant rescanning of directories
- Improved responsiveness in large repositories
- Optimized memory usage for directory selection

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
