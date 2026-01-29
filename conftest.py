"""
Pytest configuration and shared fixtures for Brain-Trust tests.
"""
import os
import sys
import pytest
from dotenv import load_dotenv

# Fix Windows console encoding for emoji support
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except AttributeError:
        # Python < 3.7 fallback
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Load environment variables
load_dotenv(".env")

# Add backend to path
backend_path = os.path.join(os.path.dirname(__file__), "backend")
sys.path.insert(0, backend_path)


# ============================================================================
# FIXTURES - Shared test data and setup
# ============================================================================

@pytest.fixture(scope="session")
def api_key():
    """Brain Trust API key for testing."""
    key = os.getenv("BRAIN_TRUST_API_KEY")
    if not key:
        pytest.skip("BRAIN_TRUST_API_KEY not found in environment")
    return key


@pytest.fixture(scope="session")
def base_url():
    """Base URL for Brain Trust API."""
    return os.getenv("BRAIN_TRUST_API_URL", "http://127.0.0.1:8000")


@pytest.fixture(scope="session")
def google_credentials_path():
    """Path to Google service account credentials."""
    path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "credentials.json")
    if not os.path.exists(path):
        pytest.skip(f"Google credentials not found at {path}")
    return path


@pytest.fixture(scope="session")
def shared_drive_id():
    """Life with AI Shared Drive ID."""
    return "0AMpJ2pkSpYq-Uk9PVA"


@pytest.fixture
def api_headers(api_key):
    """Standard API headers for requests."""
    return {
        "Content-Type": "application/json",
        "X-API-Key": api_key
    }


@pytest.fixture
def sample_workflow():
    """Sample workflow JSON for testing."""
    return {
        "nodes": [
            {
                "id": "test-agent-1",
                "type": "agentNode",
                "data": {
                    "name": "Test Agent",
                    "role": "Assistant",
                    "goal": "Test the workflow system",
                    "backstory": "A test agent for validation",
                    "model": "gemini-2.0-flash"
                }
            }
        ],
        "edges": []
    }


@pytest.fixture
def librarian_workflow(shared_drive_id):
    """Librarian agent workflow for testing."""
    return {
        "nodes": [
            {
                "id": "librarian-1",
                "type": "agentNode",
                "data": {
                    "name": "Test Librarian",
                    "role": "Librarian",
                    "goal": "Test Drive access and file discovery",
                    "backstory": "A test Librarian agent for validating Drive tools",
                    "model": "gemini-2.0-flash"
                }
            }
        ],
        "edges": []
    }


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def is_api_running(base_url: str) -> bool:
    """Check if the Brain Trust API is running."""
    import requests
    try:
        response = requests.get(f"{base_url}/health", timeout=2)
        return response.status_code == 200
    except:
        return False


# ============================================================================
# PYTEST HOOKS
# ============================================================================

def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "requires_api: Test requires Brain Trust API to be running"
    )
    config.addinivalue_line(
        "markers", "requires_google: Test requires Google credentials"
    )


def pytest_collection_modifyitems(config, items):
    """Auto-skip tests based on environment."""
    base_url = os.getenv("BRAIN_TRUST_API_URL", "http://127.0.0.1:8000")
    
    for item in items:
        # Skip tests requiring API if it's not running
        if "requires_api" in item.keywords:
            if not is_api_running(base_url):
                item.add_marker(
                    pytest.mark.skip(reason=f"Brain Trust API not running at {base_url}")
                )
        
        # Skip tests requiring Google creds if not available
        if "requires_google" in item.keywords:
            creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "credentials.json")
            if not os.path.exists(creds_path):
                item.add_marker(
                    pytest.mark.skip(reason="Google credentials not found")
                )
