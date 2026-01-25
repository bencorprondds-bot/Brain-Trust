"""Read existing agent prompts from Google Drive Agent_Prompts folder."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io

SCOPES = ['https://www.googleapis.com/auth/drive']

# File IDs from previous scan
FILES = {
    'Dev Editor': '1nKWbHTS7bzSmH4tWq9DmsNyvKq05HotZ',
    'Atlas (Continuity)': '17M2T7jR6Mo0u7XPcV96H8njSjxdnhoAl',
}

def read_file_content(service, file_id, file_name):
    """Download and read a text file from Drive."""
    request = service.files().get_media(fileId=file_id)
    file_content = io.BytesIO()
    downloader = MediaIoBaseDownload(file_content, request)
    
    done = False
    while not done:
        status, done = downloader.next_chunk()
    
    content = file_content.getvalue().decode('utf-8')
    return content

def main():
    print("=" * 60)
    print("READING AGENT PROMPTS FROM GOOGLE DRIVE")
    print("=" * 60)
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    creds_path = os.path.join(base_dir, "credentials.json")
    creds = service_account.Credentials.from_service_account_file(creds_path, scopes=SCOPES)
    service = build('drive', 'v3', credentials=creds)
    
    for name, file_id in FILES.items():
        print(f"\n{'='*60}")
        print(f"📄 {name}")
        print("=" * 60)
        try:
            content = read_file_content(service, file_id, name)
            print(content)
        except Exception as e:
            print(f"Error reading {name}: {e}")

if __name__ == "__main__":
    main()
