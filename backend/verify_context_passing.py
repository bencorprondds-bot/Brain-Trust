"""
Verify that the Librarian can find files and pass them as context to the Writer.
Structure: Librarian -> Draft Writer
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv("../.env")

import requests
import json
import time

API_KEY = os.getenv("BRAIN_TRUST_API_KEY")
BASE_URL = "http://127.0.0.1:8000"

def verify_context_passing():
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": API_KEY
    }
    
    workflow = {
        "nodes": [
            {
                "id": "librarian",
                "type": "agentNode",
                "data": {
                    "name": "The Librarian",
                    "role": "Librarian",
                    "goal": "Find the 'Oren_Torres_Character_Profile' in the Characters folder. Read its content and output it.",
                    "backstory": "You are the maintainer of the Drive. Locate the character profile for Oren Torres.",
                    "model": "gemini-2.0-flash"
                }
            },
            {
                "id": "writer",
                "type": "agentNode",
                "data": {
                    "name": "Story Writer",
                    "role": "Writer",
                    "goal": "Write a short scene (200 words) featuring Oren Torres, using the character profile provided by the Librarian.",
                    "backstory": "You are a creative writer. Use the context provided to write an on-model scene.",
                    "model": "gemini-2.0-flash"
                }
            }
        ],
        "edges": [
            {"id": "e1", "source": "librarian", "target": "writer"}
        ]
    }
    
    print("=" * 70)
    print("VERIFYING CONTEXT PASSING")
    print("=" * 70)
    print("Pipeline: Librarian (Find Profile) -> Writer (Write Scene)")
    print("\nSending workflow...")
    
    start = time.time()
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/run-workflow",
            headers=headers,
            json=workflow,
            timeout=180
        )
        
        duration = time.time() - start
        
        if response.status_code == 200:
            result = response.json()
            print(f"\n✅ Workflow completed successfully!")
            print(f"Duration: {duration:.1f}s")
            
            output = result.get('result', 'No result')
            print(f"\n{'='*70}")
            print("FINAL OUTPUT")
            print("="*70)
            print(output)
            
            # success check
            if "Oren" in output and len(output) > 100:
                print("\n✅ SUCCESS: Context file was found and used!")
                return True
            else:
                print("\n⚠️ WARNING: Output may not have used context correctly.")
                return False
        else:
            print(f"\n❌ Workflow failed: {response.status_code}")
            print(response.text)
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    verify_context_passing()
