# Merge Request: Add Testing and Automated CI/CD Workflow

## Overview
This PR adds comprehensive testing frameworks, code coverage tools, and automated build and release processes, improving the project's quality and maintainability.

## Main Changes
1. **GitHub Actions Workflows**:
   - Added `publish-package.yml`: Automatically publishes Python package to PyPI when PR is merged to main branch
   - Added `python-app.yml`: Runs tests and code quality checks

2. **Testing Framework**:
   - Added multiple test modules covering server components, authentication flow, and OAuth functionality
   - Implemented `test_auth_coverage.py` for complete authentication logic testing
   - Added modules for testing server components and API calls

3. **Coverage Tools**:
   - Added `run_coverage.py` script to simplify test coverage analysis
   - Added configuration for generating coverage reports for CI/CD process

4. **Project Configuration**:
   - Updated dependencies and configuration in `pyproject.toml`
   - Added `pytest.ini` configuration file to optimize test execution
   - Added `setup.py` to support package publishing

## Technical Details
- Test coverage increased from 0% to 67%
- New tests use AsyncMock and MagicMock to simulate asynchronous function calls
- Tests ensure the correctness of token validation, OAuth flow, document operations, and other key functionality
- GitHub Actions will automatically publish new versions to PyPI after PR merges, without manual intervention

## How to Test
Run tests locally using the following command:
```bash
python run_coverage.py -vxs
```

## Notes
- `PYPI_API_TOKEN` needs to be added to GitHub Secrets to enable automatic publishing
- Tests use environment variable simulation and do not affect actual API calls
- Coverage reports are generated in the `coverage_html` directory

## Related Issues/Tasks
- Resolved the issue of low test coverage
- Simplified the release process and improved project maintainability
- Established testing infrastructure for future feature development 