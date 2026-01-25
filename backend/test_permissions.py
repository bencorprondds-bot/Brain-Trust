
import os
import sys
import traceback
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ['https://www.googleapis.com/auth/documents', 'https://www.googleapis.com/auth/drive']
TARGET_FOLDER_ID = '1fKYixOC9aDcm-XHAIHhfGj3rKlRg5b-i' # 02_In_Development

def test_permissions():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    creds_path = os.path.join(base_dir, "credentials.json")
    
    print(f"Credentials: {creds_path}")
    print(f"Target Folder: {TARGET_FOLDER_ID}")
    
    try:
        creds = service_account.Credentials.from_service_account_file(creds_path, scopes=SCOPES)
        docs_service = build('docs', 'v1', credentials=creds)
        drive_service = build('drive', 'v3', credentials=creds)
        
        print("\nAttempting to create doc in Shared Folder...")
        
        # We cannot "create in folder" with Docs API directly in v1?
        # docs.documents.create doesn't accept parents independently?
        # Actually it does NOT. You create then move, OR use Drive API to create.
        # BUT Drive API "create" with mimeType application/vnd.google-apps.document IS key.
        
        # Strategy 1: Create with Docs API (if enabled) in root, then move? 
        # No, if API is disabled we can't create in root.
        
        # Strategy 2: Use Drive API to create a blank doc (requires valid permissions)
        # If this works, then Drive API is fine.
        # But we specifically want to test DOCS API for editing.
        
        # Let's try Docs API create first (it defaults to root).
        try:
            doc = docs_service.documents().create(body={'title': 'Permissions Test Doc'}).execute()
            doc_id = doc.get('documentId')
            print(f"   ✅ Docs API Create Success! ID: {doc_id}")
            
            # Now try to move it to the folder (to test folder permissions)
            print("   Attempting to move to target folder...")
            file = drive_service.files().get(fileId=doc_id, fields='parents').execute()
            previous_parents = ",".join(file.get('parents'))
            drive_service.files().update(
                fileId=doc_id,
                addParents=TARGET_FOLDER_ID,
                removeParents=previous_parents,
                fields='id, parents'
            ).execute()
            print("   ✅ Move Success! Folder permissions are good.")
            
            # Cleanup
            drive_service.files().delete(fileId=doc_id).execute()
            print("   (Cleaned up)")
            return True
            
        except HttpError as e:
            print(f"   ❌ API/Permission Error: {e}")
            return False

    except Exception as e:
        print(f"❌ Setup Error: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_permissions()
