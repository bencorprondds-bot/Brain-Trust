"""Explore Life with AI Shared Drive folder structure."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/documents']

# Shared Drive Configuration
SHARED_DRIVE_ID = '0AMpJ2pkSpYq-Uk9PVA'  # Life with AI Shared Drive

# Folder IDs from Shared Drive (Updated Jan 2026)
FOLDERS = {
    'system': '1_85nRX4isDeoshv98bFL3ARljJ4LTkT0',
    'inbox': '1RKLpafuip4HgYj_bmuUfuj3ojZWNb1WZ',
    'in_development': '1_AcAlToFkwKwG34FLij54suGOiQ68p_d',
    'ready_for_review': '1va471qBT7Mogi4ymMz_zS6oW0DSQ3QJs',
    'beta_readers': '1HwyGuQroOXsxQPJ1paCyTcdv6h14hPXs',
    'published': '1SMKJVYbtUJdc0za5X9VD689tzo5A1-_o',
    'characters': '1TNzmGFe28yzga77O34YoF_m0F1WMzcbL',
    'reference_docs': '1rso6i2_mRFSOKmLC19EL6JtT2h1xzc2M',
    'agent_prompts': '1JvMDwstlpXusW6lCSrRlVazCjJvtnA_Y',
    'workflows': '10NH-ufIi7PNNVL6SFW5ClgAJ5j2tM4iv',
}

def explore_folder(service, folder_name, folder_id, indent=0):
    """List contents of a folder in Shared Drive."""
    prefix = "  " * indent
    print(f"{prefix}📁 {folder_name}/")
    
    results = service.files().list(
        q=f"'{folder_id}' in parents and trashed = false",
        corpora='drive',
        driveId=SHARED_DRIVE_ID,
        includeItemsFromAllDrives=True,
        supportsAllDrives=True,
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
    print("LIFE WITH AI SHARED DRIVE - FOLDER STRUCTURE")
    print("=" * 60)
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    creds_path = os.path.join(base_dir, "credentials.json")
    creds = service_account.Credentials.from_service_account_file(creds_path, scopes=SCOPES)
    service = build('drive', 'v3', credentials=creds)
    
    # Explore key folders
    for folder_name in ['in_development', 'ready_for_review', 'reference_docs', 'agent_prompts']:
        if folder_name in FOLDERS:
            explore_folder(service, folder_name.replace('_', ' ').title(), FOLDERS[folder_name])
            print()

if __name__ == "__main__":
    main()
