"""Test workflow API with TELOS context injection."""
import requests
import json
import os
from dotenv import load_dotenv

load_dotenv("../.env")

API_KEY = os.getenv("BRAIN_TRUST_API_KEY")
BASE_URL = "http://127.0.0.1:8000"

def test_health():
    """Test health endpoint."""
    response = requests.get(f"{BASE_URL}/health")
    print(f"Health check: {response.json()}")
    return response.status_code == 200

def test_workflow():
    """Test workflow endpoint with a simple agent."""
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": API_KEY
    }
    
    workflow = {
        "nodes": [
            {
                "id": "agent-1",
                "type": "agentNode",
                "data": {
                    "name": "TELOS Test Agent",
                    "role": "Context Verifier",
                    "goal": "Confirm that TELOS context is loaded and describe what mission, goals, and beliefs you received",
                    "backstory": "You are a test agent verifying the Brain Trust TELOS integration works correctly."
                }
            }
        ],
        "edges": []
    }
    
    print(f"\nSending workflow request...")
    print(f"Using API Key: {API_KEY[:8]}...")
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/run-workflow",
            headers=headers,
            json=workflow,
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"\n✅ Workflow executed successfully!")
            print(f"Duration: {result.get('duration', 'N/A')}s")
            print(f"Agents: {result.get('agent_count', 'N/A')}")
            print(f"Tasks: {result.get('task_count', 'N/A')}")
            print(f"\nResult:\n{result.get('result', 'No result')}")
            return True
        else:
            print(f"\n❌ Workflow failed: {response.status_code}")
            print(response.text)
            return False
            
    except requests.exceptions.Timeout:
        print("❌ Request timed out after 60 seconds")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("BRAIN TRUST TELOS INTEGRATION TEST")
    print("=" * 50)
    
    if test_health():
        test_workflow()
    else:
        print("Health check failed - is the backend running?")
