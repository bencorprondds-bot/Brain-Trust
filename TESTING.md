# Testing Guide for Brain-Trust

## Quick Start

```bash
# Install test dependencies
pip install -r backend/requirements.txt

# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest backend/test_librarian_pytest.py -v

# Run specific test
pytest backend/test_librarian_pytest.py::TestLibrarianDriveAccess::test_list_shared_drive_folders -v
```

## Test Organization

### Test Markers

Tests are organized with markers for easy filtering:

```bash
# Run only unit tests (fast, no external dependencies)
pytest -m unit

# Run only integration tests
pytest -m integration

# Run only agent tests
pytest -m agents

# Run Drive API tests
pytest -m drive

# Skip slow tests
pytest -m "not slow"

# Combine markers
pytest -m "integration and not slow"
```

### Test Types

- **Unit Tests** (`@pytest.mark.unit`): Fast, no external dependencies
- **Integration Tests** (`@pytest.mark.integration`): Require API/services running
- **Drive Tests** (`@pytest.mark.drive`): Interact with Google Drive
- **Agent Tests** (`@pytest.mark.agents`): Test CrewAI agents
- **Slow Tests** (`@pytest.mark.slow`): Take significant time (>30s)

## Running Tests

### Basic Commands

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=backend/app --cov-report=html
open htmlcov/index.html

# Run specific test class
pytest backend/test_librarian_pytest.py::TestLibrarianDriveAccess

# Run tests matching keyword
pytest -k "librarian"
pytest -k "drive"

# Stop on first failure (useful for debugging)
pytest -x

# Show local variables in tracebacks
pytest --showlocals

# Run tests in parallel (requires pytest-xdist)
pytest -n auto
```

## Environment & Credentials

These tests require local secrets and should never be committed to git.

### Required Variables

- `BRAIN_TRUST_API_KEY` (API auth for the backend)
- `GOOGLE_API_KEY` or `GEMINI_API_KEY` (Gemini LLM access)

### Optional Variables

- `BRAIN_TRUST_API_URL` (defaults to `http://127.0.0.1:8000`)
- `GOOGLE_APPLICATION_CREDENTIALS` (absolute path to your Google service account JSON)
- `BRAIN_TRUST_MAX_ITER` (Librarian agent retry cap; default: 2)

### Service Account JSON

Place your Google service account JSON locally and keep it out of git. Either:

- Set `GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/credentials.json`, or
- Save it at `backend/credentials.json` (ignored by `.gitignore`).

### Example (local shell)

```bash
export BRAIN_TRUST_API_KEY=...your key...
export GOOGLE_API_KEY=...your key...
export GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/credentials.json
export BRAIN_TRUST_MAX_ITER=2
```

### Watch Mode

```bash
# Re-run tests when files change (requires pytest-watch)
pip install pytest-watch
ptw
```

## VS Code Integration

### Run Tests in VS Code

1. Open Command Palette (`Ctrl+Shift+P` or `Cmd+Shift+P`)
2. Type "Python: Configure Tests"
3. Select "pytest"
4. Select "backend" as root directory

Now you can:
- Click ▶ icon next to test functions to run them
- See test results inline in the editor
- Set breakpoints and debug tests
- View test explorer in sidebar

### Keyboard Shortcuts

- `Ctrl+;` - Run all tests
- `Ctrl+Shift+;` - Debug test at cursor

## Writing New Tests

### Test File Structure

```python
"""
Test description here.

Run with:
    pytest backend/test_myfeature.py -v
"""
import pytest

# Mark all tests in this module
pytestmark = [pytest.mark.integration, pytest.mark.myfeature]

class TestMyFeature:
    """Group related tests together."""
    
    def test_something(self, api_headers, base_url):
        """Test should have descriptive name."""
        # Arrange
        data = {"key": "value"}
        
        # Act
        result = do_something(data)
        
        # Assert
        assert result == expected
```

### Using Fixtures

Common fixtures available (from `conftest.py`):

- `api_key` - Brain Trust API key
- `base_url` - API base URL
- `api_headers` - Standard headers for requests
- `shared_drive_id` - Life with AI Shared Drive ID
- `google_credentials_path` - Path to credentials.json
- `sample_workflow` - Generic workflow JSON
- `librarian_workflow` - Librarian-specific workflow

### Parametrized Tests

Run same test with different inputs:

```python
@pytest.mark.parametrize("input,expected", [
    ("inbox", "1RKLpafuip4HgYj_bmuUfuj3ojZWNb1WZ"),
    ("published", "1SMKJVYbtUJdc0za5X9VD689tzo5A1-_o"),
])
def test_folder_lookup(input, expected):
    from app.tools.drive_tool import FOLDER_IDS
    assert FOLDER_IDS[input] == expected
```

## Debugging Tests

### With VS Code Debugger

1. Set breakpoint in test file
2. Right-click test function
3. Select "Debug Test"

### With Print Statements

```bash
# Pytest captures output by default
# Use -s flag to see print statements
pytest -s backend/test_mytest.py

# Or use --capture=no in pytest.ini (already configured)
```

### With pdb

```python
def test_something():
    import pdb; pdb.set_trace()  # Breakpoint
    # ... test code
```

## Test Coverage

```bash
# Generate coverage report
pytest --cov=backend/app --cov-report=html

# View in browser
open htmlcov/index.html

# Show missing lines in terminal
pytest --cov=backend/app --cov-report=term-missing
```

## Continuous Integration

Tests automatically skip if:
- Brain Trust API is not running (for integration tests)
- Google credentials not found (for Drive tests)
- Required environment variables missing

## Common Issues

### API Not Running

```
SKIPPED [1] conftest.py:140: Brain Trust API not running at http://127.0.0.1:8000
```

**Solution**: Start the API server first
```bash
cd backend
uvicorn app.main:app --reload
```

### Google Credentials Not Found

```
SKIPPED [1] conftest.py:146: Google credentials not found
```

**Solution**: Set `GOOGLE_APPLICATION_CREDENTIALS` environment variable
```bash
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
```

### Import Errors

```
ImportError: No module named 'app'
```

**Solution**: Run pytest from project root, not backend folder
```bash
# ✅ Correct
cd /workspaces/Brain-Trust
pytest

# ❌ Wrong
cd /workspaces/Brain-Trust/backend
pytest
```

## Best Practices

1. **Test Organization**: Group related tests in classes
2. **Descriptive Names**: Test names should describe what they test
3. **Use Fixtures**: Avoid duplicating setup code
4. **Mark Tests**: Use markers for filtering
5. **Keep Tests Fast**: Mock external dependencies when possible
6. **One Assert Per Test**: Test one thing at a time
7. **AAA Pattern**: Arrange, Act, Assert

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Pytest Fixtures](https://docs.pytest.org/en/stable/fixture.html)
- [Parametrize Tests](https://docs.pytest.org/en/stable/parametrize.html)
- [VS Code Python Testing](https://code.visualstudio.com/docs/python/testing)
