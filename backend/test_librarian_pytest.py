"""
Pytest version of Librarian agent tests.
Tests Drive capabilities: folder listing, file discovery, document reading.

Run with:
    pytest backend/test_librarian_pytest.py -v
    pytest backend/test_librarian_pytest.py -k "test_list" -v
    pytest backend/test_librarian_pytest.py --markers
"""
import pytest
import requests


# Mark all tests in this module
pytestmark = [
    pytest.mark.integration,
    pytest.mark.agents,
    pytest.mark.drive,
    pytest.mark.requires_api
]


class TestLibrarianDriveAccess:
    """Test Librarian agent's Google Drive capabilities."""
    
    def test_list_shared_drive_folders(self, base_url, api_headers, librarian_workflow):
        """Test that Librarian can list all folders in Shared Drive."""
        # Modify workflow to list folders
        librarian_workflow["nodes"][0]["data"]["goal"] = (
            "List all folders in the Life with AI Shared Drive"
        )
        
        response = requests.post(
            f"{base_url}/api/v1/run-workflow",
            headers=api_headers,
            json=librarian_workflow,
            timeout=60
        )
        
        assert response.status_code == 200, f"API error: {response.text}"
        result = response.json()
        
        # Verify response structure
        assert "final_output" in result
        assert "agent_count" in result
        assert result["agent_count"] == 1
        
        # Verify folders were found
        output = result["final_output"]
        assert "folder" in output.lower() or "📁" in output
        
    
    def test_find_arun_character_files(self, base_url, api_headers, librarian_workflow):
        """Test that Librarian can find files referencing Arun character."""
        librarian_workflow["nodes"][0]["data"]["goal"] = (
            "Find all files that reference 'Arun' in their names. "
            "List the file names and their IDs."
        )
        
        response = requests.post(
            f"{base_url}/api/v1/run-workflow",
            headers=api_headers,
            json=librarian_workflow,
            timeout=60
        )
        
        assert response.status_code == 200
        result = response.json()
        
        output = result["final_output"].lower()
        assert "arun" in output, "Should mention Arun files"
    
    
    def test_read_google_doc(self, base_url, api_headers, librarian_workflow):
        """Test that Librarian can read a Google Doc's content."""
        # Use a known test document ID
        test_doc_id = "1RQVe897C5ZB5mVf8dNqvL69h9O_3su44SfP0KADfQQ0"  # New Document in Inbox
        
        librarian_workflow["nodes"][0]["data"]["goal"] = (
            f"Read the contents of document ID {test_doc_id} and summarize what you find"
        )
        
        response = requests.post(
            f"{base_url}/api/v1/run-workflow",
            headers=api_headers,
            json=librarian_workflow,
            timeout=60
        )
        
        assert response.status_code == 200
        result = response.json()
        
        # Should successfully read document
        assert "error" not in result["final_output"].lower()
    
    
    @pytest.mark.slow
    def test_export_word_document(self, base_url, api_headers, librarian_workflow):
        """Test that Librarian can export Word documents as text."""
        # Arun story beats.docx
        word_doc_id = "1K1Uz02MJLaaKqko1EgTnUtxzny72dKzx"
        
        librarian_workflow["nodes"][0]["data"]["goal"] = (
            f"Export Word document ID {word_doc_id} and show me its content"
        )
        
        response = requests.post(
            f"{base_url}/api/v1/run-workflow",
            headers=api_headers,
            json=librarian_workflow,
            timeout=90
        )
        
        assert response.status_code == 200
        result = response.json()
        
        output = result["final_output"]
        # Should have content, not an error
        assert len(output) > 100, "Should contain exported text"
        assert "error" not in output.lower()


class TestLibrarianFileOperations:
    """Test Librarian's file creation and organization capabilities."""
    
    @pytest.mark.integration
    @pytest.mark.requires_api
    def test_create_document_in_inbox(self, base_url, api_headers, librarian_workflow):
        """Test creating a new document in Inbox folder."""
        librarian_workflow["nodes"][0]["data"]["goal"] = (
            "Create a new Google Doc titled 'Test Document' "
            "in the Inbox folder with content 'This is a test.'"
        )
        
        response = requests.post(
            f"{base_url}/api/v1/run-workflow",
            headers=api_headers,
            json=librarian_workflow,
            timeout=60
        )
        
        assert response.status_code == 200
        result = response.json()
        
        output = result["final_output"]
        assert "created" in output.lower() or "✅" in output
        # Should include document ID
        assert "1" in output  # Document IDs start with "1"


# ============================================================================
# UNIT TESTS - Fast tests without external dependencies
# ============================================================================

@pytest.mark.unit
class TestDriveToolConfiguration:
    """Unit tests for Drive tool configuration."""
    
    def test_shared_drive_id_constant(self):
        """Verify shared drive ID is correctly configured."""
        from app.tools.drive_tool import SHARED_DRIVE_ID
        
        assert SHARED_DRIVE_ID == "0AMpJ2pkSpYq-Uk9PVA"
        assert len(SHARED_DRIVE_ID) > 0
    
    
    def test_folder_ids_mapping(self):
        """Verify folder IDs dictionary is properly populated."""
        from app.tools.drive_tool import FOLDER_IDS
        
        # Check key folders exist
        required_folders = ['inbox', 'in_development', 'ready_for_review', 'published']
        for folder in required_folders:
            assert folder in FOLDER_IDS, f"Missing folder: {folder}"
            assert len(FOLDER_IDS[folder]) > 0, f"Empty ID for {folder}"


# ============================================================================
# PARAMETRIZED TESTS - Run same test with different inputs
# ============================================================================

@pytest.mark.integration
@pytest.mark.parametrize("folder_name,folder_key", [
    ("Inbox", "inbox"),
    ("In_Development", "in_development"),
    ("Characters", "characters"),
])
def test_find_folder_by_name(base_url, api_headers, librarian_workflow, folder_name, folder_key):
    """Test finding folders by name (parametrized)."""
    librarian_workflow["nodes"][0]["data"]["goal"] = (
        f"Find the folder named '{folder_name}' and show its ID"
    )
    
    response = requests.post(
        f"{base_url}/api/v1/run-workflow",
        headers=api_headers,
        json=librarian_workflow,
        timeout=60
    )
    
    assert response.status_code == 200
    result = response.json()
    
    # Should mention the folder
    output = result["final_output"].lower()
    assert folder_name.lower().replace("_", " ") in output
