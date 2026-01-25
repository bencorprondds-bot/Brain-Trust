"""Explore Life with AI folder structure."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/documents']

# Folder IDs from previous scan
FOLDERS = {
    'Life with AI': '1duf6BRY-tqyWzP3gH1clfaM5B-Qqh0r5',
    '01_Inbox': '1KzQODiGWI0DTsV6dEJHOGvniKx7nR8Ss',
    '02_In_Development': '1fKYixOC9aDcm-XHAIHhfGj3rKlRg5b-i',
    '03_Ready_for_Review': '1Zy2ocnE4EOwpeuvu8RFrNS_WophR4ebB',
    '04_Published': '1buuMweoHEdo17_YdR9qgXw42dpNhgyR3',
    '05_Voice_Library': '1zzD3HBIrjOAQ-L5a1WDsewroKaOzpie_',
    'Agent_Prompts': '1u81lD6187CGxztciR_clM4rH-9TpM1TT',
    'Reference_Docs': '1SKO7KfS3UUuwTiHQ1WYS0eBfVryR1Wxr',
    'Workflows': '1ZGHfjdxIJPxOe_W_8iNskV9U5UkT0uAc',
}

def explore_folder(service, folder_name, folder_id, indent=0):
    """List contents of a folder."""
    prefix = "  " * indent
    print(f"{prefix}📁 {folder_name}/")
    
    results = service.files().list(
        q=f"'{folder_id}' in parents and trashed = false",
        pageSize=20,
        fields="files(id, name, mimeType)"
    ).execute()
    
    items = results.get('files', [])
    
    for item in items:
        if item['mimeType'] == 'application/vnd.google-apps.folder':
            explore_folder(service, item['name'], item['id'], indent + 1)
        elif item['mimeType'] == 'application/vnd.google-apps.document':
            print(f"{prefix}  📄 {item['name']}")
        else:
            ext = item['name'].split('.')[-1] if '.' in item['name'] else 'file'
            print(f"{prefix}  📎 {item['name']}")

def main():
    print("=" * 60)
    print("LIFE WITH AI - FOLDER STRUCTURE")
    print("=" * 60)
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    creds_path = os.path.join(base_dir, "credentials.json")
    creds = service_account.Credentials.from_service_account_file(creds_path, scopes=SCOPES)
    service = build('drive', 'v3', credentials=creds)
    
    # Explore key folders
    for folder_name in ['02_In_Development', '03_Ready_for_Review', 'Reference_Docs', 'Agent_Prompts']:
        if folder_name in FOLDERS:
            explore_folder(service, folder_name, FOLDERS[folder_name])
            print()

if __name__ == "__main__":
    main()
