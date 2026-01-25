"""
Test the Librarian agent's Drive capabilities.
Verifies folder listing, file discovery, and document reading.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv("../.env")

import requests
import json

API_KEY = os.getenv("BRAIN_TRUST_API_KEY")
BASE_URL = "http://127.0.0.1:8000"

def test_librarian_workflow():
    """Test the Librarian agent via workflow API."""
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": API_KEY
    }
    
    # Librarian workflow - inventory the Drive
    workflow = {
        "nodes": [
            {
                "id": "librarian-1",
                "type": "agentNode",
                "data": {
                    "name": "The Librarian",
                    "role": "Librarian",  # Triggers Drive tools auto-assignment
                    "goal": "Inventory the Life with AI Google Drive. Find the style guide document, read its contents, and report a summary of what it contains.",
                    "backstory": """You are Iris, The Librarian. You are meticulous, thoughtful, and take pride in maintaining order. 
                    
Your job is to:
1. List all folders in the Life with AI Drive
2. Find the Style Guide document (look in Style_Guides folder or search for 'style' in names)
3. Read and summarize the style guide contents
4. Report what you find

Use your Google Drive tools to explore the folder structure and read documents.""",
                    "model": "gemini-2.0-flash"
                }
            }
        ],
        "edges": []
    }
    
    print("=" * 60)
    print("LIBRARIAN AGENT TEST")
    print("=" * 60)
    print("\nSending workflow to test Librarian...")
    print(f"Using API Key: {API_KEY[:8]}...")
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/run-workflow",
            headers=headers,
            json=workflow,
            timeout=120
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"\n✅ Workflow executed successfully!")
            print(f"Duration: {result.get('duration', 'N/A'):.2f}s")
            print(f"Agents: {result.get('agent_count', 'N/A')}")
            print(f"Tasks: {result.get('task_count', 'N/A')}")
            print(f"\n{'='*60}")
            print("LIBRARIAN REPORT")
            print("="*60)
            print(result.get('result', 'No result'))
            return True
        else:
            print(f"\n❌ Workflow failed: {response.status_code}")
            print(response.text)
            return False
            
    except requests.exceptions.Timeout:
        print("❌ Request timed out after 120 seconds")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    test_librarian_workflow()
