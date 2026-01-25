
import os
import sys
import traceback
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ['https://www.googleapis.com/auth/documents', 'https://www.googleapis.com/auth/drive']

def debug_docs_api():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    creds_path = os.path.join(base_dir, "credentials.json")
    
    print(f"Credentials: {creds_path}")
    
    try:
        creds = service_account.Credentials.from_service_account_file(creds_path, scopes=SCOPES)
        
        # Test 1: Docs API Service Build
        print("\n1. Building Docs Service...")
        docs_service = build('docs', 'v1', credentials=creds)
        print("   ✅ Service built.")
        
        # Test 2: Create Doc in Root
        print("\n2. Attempting to create doc in Service Account Root...")
        try:
            doc = docs_service.documents().create(body={'title': 'Brain Trust API Check'}).execute()
            print(f"   ✅ Success! Doc ID: {doc.get('documentId')}")
            # Cleanup
            drive_service = build('drive', 'v3', credentials=creds)
            drive_service.files().delete(fileId=doc.get('documentId')).execute()
            print("   (Cleaned up test file)")
            return True
        except HttpError as e:
            print(f"   ❌ HttpError: {e}")
            print(f"   Reason: {e.reason}")
            print(f"   Details: {e.content}")
            return False
        except Exception as e:
            print(f"   ❌ Unknown Error: {e}")
            traceback.print_exc()
            return False

    except Exception as e:
        print(f"❌ Setup Error: {e}")
        return False

if __name__ == "__main__":
    debug_docs_api()
