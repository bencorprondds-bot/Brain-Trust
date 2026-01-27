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

# Shared Drive Configuration
SHARED_DRIVE_ID = '0AMpJ2pkSpYq-Uk9PVA'  # Life with AI Shared Drive

# Known folder IDs from Shared Drive audit (Updated Jan 2026)
FOLDERS = {
    'system': '1_85nRX4isDeoshv98bFL3ARljJ4LTkT0',
    'inbox': '1RKLpafuip4HgYj_bmuUfuj3ojZWNb1WZ',
    'in_development': '1_AcAlToFkwKwG34FLij54suGOiQ68p_d',
    'ready_for_review': '1va471qBT7Mogi4ymMz_zS6oW0DSQ3QJs',
    'beta_readers': '1HwyGuQroOXsxQPJ1paCyTcdv6h14hPXs',
    'published': '1SMKJVYbtUJdc0za5X9VD689tzo5A1-_o',
    'voice_library': '1UuJOd9eM_V_jn4LH_pG_fybZOGcz4CEU',
    'agent_prompts': '1JvMDwstlpXusW6lCSrRlVazCjJvtnA_Y',
    'reference_docs': '1rso6i2_mRFSOKmLC19EL6JtT2h1xzc2M',
    'workflows': '10NH-ufIi7PNNVL6SFW5ClgAJ5j2tM4iv',
    'characters': '1TNzmGFe28yzga77O34YoF_m0F1WMzcbL',
    'style_guides': '1C9nV3VsO19MzcLq0B2CE4G1_1m-1W0V0',
    'world': '1Iik6DK8RDsLw-nBRTwaaJ3A8c3dP1RZP',
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
