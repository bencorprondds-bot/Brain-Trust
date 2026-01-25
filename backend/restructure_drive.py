"""
Librarian: Execute Drive Folder Restructure
Creates missing folders and moves files to proper locations.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/drive']

# Known folder IDs from audit
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
    'Images for the blog': '1y7yCgVcFsgWSTk4ZreuMBcgfJ91il6MO',
}

# Files to move
FILES_TO_MOVE = {
    # Character profiles to move to Characters folder
    'Oren_Torres_Character_Profile': '1mwQllCMUnnLO2tulRHXOBMYDTu0B56Cl4o8gmVbUPi8',
    'Arun_Pichai_Character_Profile': '1-CD--k0kuVKMsJe0mX4xR-bhCmMmU28U-smIPHpTTK0',
}

def create_folder(service, name, parent_id):
    """Create a folder in Drive."""
    file_metadata = {
        'name': name,
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [parent_id]
    }
    folder = service.files().create(body=file_metadata, fields='id, name').execute()
    print(f"✅ Created folder: {name} (ID: {folder['id']})")
    return folder['id']

def move_file(service, file_id, old_parent_id, new_parent_id, file_name):
    """Move a file from one folder to another."""
    try:
        # Update the file's parents
        service.files().update(
            fileId=file_id,
            addParents=new_parent_id,
            removeParents=old_parent_id,
            fields='id, parents'
        ).execute()
        print(f"✅ Moved: {file_name} → new folder")
        return True
    except Exception as e:
        print(f"❌ Failed to move {file_name}: {e}")
        return False

def get_file_parent(service, file_id):
    """Get the parent folder ID of a file."""
    try:
        file = service.files().get(fileId=file_id, fields='parents').execute()
        return file.get('parents', [None])[0]
    except:
        return None

def folder_exists(service, name, parent_id):
    """Check if a folder exists."""
    query = f"name = '{name}' and '{parent_id}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    files = results.get('files', [])
    if files:
        return files[0]['id']
    return None

def main():
    print("=" * 70)
    print("LIBRARIAN: EXECUTING DRIVE RESTRUCTURE")
    print("=" * 70)
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    creds_path = os.path.join(base_dir, "credentials.json")
    creds = service_account.Credentials.from_service_account_file(creds_path, scopes=SCOPES)
    service = build('drive', 'v3', credentials=creds)
    
    # ========================================
    # STEP 1: Create missing folders
    # ========================================
    print("\n📁 STEP 1: Creating missing folders...")
    
    new_folders = {}
    
    # Create Characters folder under Reference_Docs
    ref_docs_id = FOLDERS.get('Reference_Docs')
    if ref_docs_id:
        existing = folder_exists(service, 'Characters', ref_docs_id)
        if existing:
            new_folders['Characters'] = existing
            print(f"   📁 Characters already exists (ID: {existing})")
        else:
            new_folders['Characters'] = create_folder(service, 'Characters', ref_docs_id)
        
        # Create Style_Guides folder
        existing = folder_exists(service, 'Style_Guides', ref_docs_id)
        if existing:
            new_folders['Style_Guides'] = existing
            print(f"   📁 Style_Guides already exists (ID: {existing})")
        else:
            new_folders['Style_Guides'] = create_folder(service, 'Style_Guides', ref_docs_id)
        
        # Create World folder
        existing = folder_exists(service, 'World', ref_docs_id)
        if existing:
            new_folders['World'] = existing
            print(f"   📁 World already exists (ID: {existing})")
        else:
            new_folders['World'] = create_folder(service, 'World', ref_docs_id)
    
    # Create Assets folder under Life with AI root
    life_with_ai_id = FOLDERS.get('Life with AI')
    if life_with_ai_id:
        existing = folder_exists(service, 'Assets', life_with_ai_id)
        if existing:
            new_folders['Assets'] = existing
            print(f"   📁 Assets already exists (ID: {existing})")
        else:
            new_folders['Assets'] = create_folder(service, 'Assets', life_with_ai_id)
    
    # ========================================
    # STEP 2: Move character profiles
    # ========================================
    print("\n📄 STEP 2: Moving character profiles to Characters folder...")
    
    characters_folder_id = new_folders.get('Characters')
    if characters_folder_id:
        for file_name, file_id in FILES_TO_MOVE.items():
            old_parent = get_file_parent(service, file_id)
            if old_parent:
                move_file(service, file_id, old_parent, characters_folder_id, file_name)
            else:
                print(f"   ⚠️ Could not find parent for {file_name}")
    
    # ========================================
    # STEP 3: Summary
    # ========================================
    print("\n" + "=" * 70)
    print("RESTRUCTURE COMPLETE")
    print("=" * 70)
    
    print("\nNew folders created:")
    for name, folder_id in new_folders.items():
        print(f"   📁 {name}: {folder_id}")
    
    print("\nFiles moved:")
    for name in FILES_TO_MOVE.keys():
        print(f"   📄 {name} → Characters/")
    
    print("\n✅ Drive restructure complete!")

if __name__ == "__main__":
    main()
