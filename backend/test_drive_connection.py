"""Test Google Drive connection - find shared files."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv("../.env")

from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/documents']

def test_drive():
    print("=" * 60)
    print("GOOGLE DRIVE - SHARED FILES TEST")
    print("=" * 60)
    
    # Authenticate
    base_dir = os.path.dirname(os.path.abspath(__file__))
    creds_path = os.path.join(base_dir, "credentials.json")
    creds = service_account.Credentials.from_service_account_file(creds_path, scopes=SCOPES)
    
    print(f"✅ Authenticated as: {creds.service_account_email}")
    
    service = build('drive', 'v3', credentials=creds)
    
    # List ALL files the service account can see (not just in 'root')
    print("\n📂 Files shared with service account:")
    results = service.files().list(
        pageSize=30,
        fields="files(id, name, mimeType, parents)",
        q="trashed = false"
    ).execute()
    
    items = results.get('files', [])
    
    if not items:
        print("   No files found. Make sure you shared the folder with the service account email.")
        return
    
    # Organize by folders
    folders = {}
    files = []
    
    for item in items:
        if item['mimeType'] == 'application/vnd.google-apps.folder':
            folders[item['id']] = item['name']
            print(f"   📁 {item['name']} (ID: {item['id']})")
        else:
            files.append(item)
    
    print(f"\n📄 Documents found: {len(files)}")
    for item in files[:15]:  # First 15 files
        print(f"   - {item['name']}")
        print(f"     Type: {item['mimeType']}")
        print(f"     ID: {item['id']}")
    
    if len(files) > 15:
        print(f"   ... and {len(files) - 15} more files")
    
    return folders

if __name__ == "__main__":
    test_drive()
