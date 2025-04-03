# Merge Request: Add Markdown to Lark Document Conversion Feature

## Description
This merge request adds functionality to convert Markdown content to Lark document blocks, enabling the creation of formatted documents in Lark through the MCP server. The feature includes comprehensive test coverage and improved project structure.

## Changes
### New Features
- Added Markdown to Lark document block conversion functionality
- Implemented support for various Markdown elements:
  - Headings
  - Lists (ordered and unordered)
  - Code blocks
  - Links
  - Tables
  - Quotes
  - Text styles (bold, italic, strikethrough)
  - Todo lists

### New Files
- `src/mcp_lark_doc_manage/markdown_converter.py`: Core Markdown conversion logic
- `src/mcp_lark_doc_manage/__main__.py`: Module entry point
- `test_create_doc.py`: Integration test for document creation
- Comprehensive test suite in `tests/markdown_conversion/`:
  - Test cases for each Markdown element type
  - Test data in both Markdown and expected JSON formats
  - Test configuration and fixtures

### Modified Files
- `src/mcp_lark_doc_manage/server.py`: Added document creation functionality
- `src/mcp_lark_doc_manage/__init__.py`: Updated imports and exports
- `pyproject.toml`: Updated dependencies and project configuration
- `README.md` and `README_zh.md`: Updated documentation
- `.gitignore`: Updated to exclude test artifacts
- `.vscode/settings.json` and `.vscode/launch.json`: Added development configuration

### Removed Files
- `.DS_Store`
- `.coverage`
- `uv.lock`

## Technical Details
### Markdown Conversion
- Implemented a robust Markdown parser using `mistune`
- Created structured block hierarchy for Lark documents
- Added support for nested elements and complex formatting
- Implemented proper handling of special characters and escaping

### Testing
- Added comprehensive unit tests for each Markdown element
- Included integration tests for document creation
- Added test data fixtures for consistent testing
- Implemented test environment configuration

### Development Setup
- Added VSCode configuration for development
- Updated project dependencies
- Improved project structure and organization

## Impact
- New feature: Markdown to Lark document conversion
- No breaking changes to existing functionality
- Improved project maintainability and testability
- Enhanced development experience

## Checklist
- [x] Implemented Markdown conversion functionality
- [x] Added comprehensive test coverage
- [x] Updated documentation
- [x] Added development configuration
- [x] Verified all tests pass
- [x] Checked code style and formatting
- [x] Updated dependencies
- [x] Removed unnecessary files

## Related Issues
- Closes #XXX (Replace with actual issue number if applicable)

## Notes
- The feature requires the `mistune` package for Markdown parsing
- Test data is included for reference and future maintenance
- VSCode configuration is optional but recommended for development 