
import os
import sys
from pathlib import Path
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io

SCOPES = ['https://www.googleapis.com/auth/drive']

def test_export():
    base_dir = Path.home() / ".pai" / "skills"
    creds_path = base_dir / "credentials.json"
    
    creds = service_account.Credentials.from_service_account_file(str(creds_path), scopes=SCOPES)
    service = build('drive', 'v3', credentials=creds)
    
    # Try to find ANY google doc
    results = service.files().list(
        q="mimeType = 'application/vnd.google-apps.document' and trashed = false",
        pageSize=1,
        fields="files(id, name)"
    ).execute()
    
    files = results.get('files', [])
    if not files:
        print("No Google Docs found to test export.")
        return
        
    doc = files[0]
    print(f"Found Doc: {doc['name']} ({doc['id']})")
    print("Attempting export as text/plain...")
    
    try:
        request = service.files().export_media(fileId=doc['id'], mimeType='text/plain')
        file_content = io.BytesIO()
        downloader = MediaIoBaseDownload(file_content, request)
        
        done = False
        while not done:
            status, done = downloader.next_chunk()
            
        print("✅ Export successful!")
        print(f"Content preview: {file_content.getvalue()[:100]}")
    except Exception as e:
        print(f"❌ Export failed: {e}")

if __name__ == "__main__":
    test_export()
