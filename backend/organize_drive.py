"""
Librarian: Comprehensive Drive Organization
Moves all documents to appropriate folders, checks for empty/redundant folders.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from google.oauth2 import service_account
from googleapiclient.discovery import build
from collections import defaultdict

SCOPES = ['https://www.googleapis.com/auth/drive']

# Shared Drive Configuration
SHARED_DRIVE_ID = '0AMpJ2pkSpYq-Uk9PVA'  # Life with AI Shared Drive

# Folder IDs from Life with AI Shared Drive (Updated Jan 2026)
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

# Track moves
moves_made = []
empty_folders = []
all_folders = {}
all_files = []

def get_all_items(service):
    """Get all files and folders from Shared Drive."""
    items = []
    page_token = None
    
    while True:
        results = service.files().list(
            q="trashed = false",
            corpora='drive',
            driveId=SHARED_DRIVE_ID,
            includeItemsFromAllDrives=True,
            supportsAllDrives=True,
            pageSize=200,
            fields="nextPageToken, files(id, name, mimeType, parents)",
            pageToken=page_token
        ).execute()
        
        items.extend(results.get('files', []))
        page_token = results.get('nextPageToken')
        if not page_token:
            break
    
    return items

def move_file(service, file_id, old_parent, new_parent, file_name, reason):
    """Move a file to a new folder on Shared Drive."""
    try:
        service.files().update(
            fileId=file_id,
            addParents=new_parent,
            removeParents=old_parent,
            supportsAllDrives=True,
            fields='id, parents'
        ).execute()
        
        old_name = all_folders.get(old_parent, 'Root')
        new_name = all_folders.get(new_parent, 'Unknown')
        
        moves_made.append({
            'file': file_name,
            'from': old_name,
            'to': new_name,
            'reason': reason
        })
        print(f"   ✅ Moved: {file_name}")
        print(f"      {old_name} → {new_name}")
        return True
    except Exception as e:
        print(f"   ❌ Failed: {file_name} - {e}")
        return False

def categorize_file(name, mime_type):
    """Determine where a file should go based on name and type."""
    name_lower = name.lower()
    
    # Character profiles
    if 'character' in name_lower or 'profile' in name_lower:
        if 'voice' in name_lower:
            return 'Voice_Library', 'Voice profile'
        return 'Characters', 'Character profile'
    
    # Voice/style files
    if 'voice' in name_lower and 'template' not in name_lower:
        return 'Voice_Library', 'Voice sample'
    
    # Style guides and templates
    if 'style' in name_lower or 'guide' in name_lower:
        return 'Style_Guides', 'Style guide'
    if 'editor' in name_lower or 'copy' in name_lower or 'polish' in name_lower:
        return 'Agent_Prompts', 'Agent prompt'
    if 'scalpel' in name_lower or 'line-editor' in name_lower:
        return 'Agent_Prompts', 'Agent prompt'
    if 'template' in name_lower:
        return 'Agent_Prompts', 'Template'
    
    # Images
    if mime_type.startswith('image/'):
        return 'Assets', 'Image file'
    if 'blog post' in name_lower or 'screenshot' in name_lower:
        return 'Assets', 'Blog image'
    
    # PDFs - likely research
    if mime_type == 'application/pdf':
        return 'Reference_Docs', 'PDF document'
    
    # Workflow files
    if 'workflow' in name_lower or mime_type == 'application/json':
        return 'Workflows', 'Workflow file'
    
    # World-building content
    if any(x in name_lower for x in ['economic', 'timeline', 'evolution', 'realistic', 'infrastructure']):
        return 'World', 'World-building'
    
    return None, None  # Don't move if unsure

def check_empty_folders(service, all_items):
    """Check for empty folders."""
    folder_contents = defaultdict(list)
    
    for item in all_items:
        if item.get('parents'):
            for parent in item['parents']:
                folder_contents[parent].append(item['name'])
    
    folders = [i for i in all_items if i['mimeType'] == 'application/vnd.google-apps.folder']
    
    for folder in folders:
        if folder['id'] not in folder_contents:
            empty_folders.append({
                'name': folder['name'],
                'id': folder['id']
            })

def main():
    print("=" * 70)
    print("LIBRARIAN: COMPREHENSIVE DRIVE ORGANIZATION")
    print("=" * 70)
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    creds_path = os.path.join(base_dir, "credentials.json")
    creds = service_account.Credentials.from_service_account_file(creds_path, scopes=SCOPES)
    service = build('drive', 'v3', credentials=creds)
    
    print("\n📂 Fetching all files and folders...")
    all_items = get_all_items(service)
    
    # Build folder map
    for item in all_items:
        if item['mimeType'] == 'application/vnd.google-apps.folder':
            all_folders[item['id']] = item['name']
    
    # Separate files from folders
    files = [i for i in all_items if i['mimeType'] != 'application/vnd.google-apps.folder']
    folders = [i for i in all_items if i['mimeType'] == 'application/vnd.google-apps.folder']
    
    print(f"   Found {len(files)} files and {len(folders)} folders")
    
    # ========================================
    # STEP 1: Move files to appropriate folders
    # ========================================
    print("\n" + "=" * 70)
    print("STEP 1: ORGANIZING FILES")
    print("=" * 70)
    
    # Get target folder IDs
    target_folders = {}
    for item in all_items:
        if item['mimeType'] == 'application/vnd.google-apps.folder':
            target_folders[item['name']] = item['id']
    
    # Update FOLDERS with discovered IDs
    FOLDERS.update(target_folders)
    
    # Process files
    for file in files:
        name = file['name']
        mime = file['mimeType']
        current_parent = file.get('parents', [None])[0]
        current_folder_name = all_folders.get(current_parent, 'Root')
        
        # Determine target folder
        target_folder, reason = categorize_file(name, mime)
        
        if target_folder and target_folder in FOLDERS:
            target_id = FOLDERS[target_folder]
            
            # Only move if not already there
            if current_parent != target_id:
                print(f"\n📄 {name}")
                print(f"   Currently in: {current_folder_name}")
                print(f"   Should be in: {target_folder} ({reason})")
                
                if current_parent:
                    move_file(service, file['id'], current_parent, target_id, name, reason)
    
    # ========================================
    # STEP 2: Check for empty folders
    # ========================================
    print("\n" + "=" * 70)
    print("STEP 2: CHECKING FOR EMPTY FOLDERS")
    print("=" * 70)
    
    # Re-fetch to get updated structure
    all_items_updated = get_all_items(service)
    check_empty_folders(service, all_items_updated)
    
    if empty_folders:
        print("\n⚠️  Empty folders found (you may want to delete):")
        for folder in empty_folders:
            print(f"   📁 {folder['name']} (ID: {folder['id']})")
    else:
        print("\n✅ No empty folders found")
    
    # ========================================
    # STEP 3: Summary Report
    # ========================================
    print("\n" + "=" * 70)
    print("ORGANIZATION SUMMARY")
    print("=" * 70)
    
    if moves_made:
        print(f"\n📋 Files moved: {len(moves_made)}")
        print("-" * 50)
        for move in moves_made:
            print(f"   📄 {move['file']}")
            print(f"      FROM: {move['from']}")
            print(f"      TO:   {move['to']}")
            print(f"      WHY:  {move['reason']}")
            print()
    else:
        print("\n✅ No files needed to be moved - everything is already organized!")
    
    print("\n" + "=" * 70)
    print("EMPTY FOLDERS (for manual review)")
    print("=" * 70)
    if empty_folders:
        for folder in empty_folders:
            print(f"   📁 {folder['name']}")
            print(f"      ID: {folder['id']}")
    else:
        print("   None found")
    
    print("\n✅ Organization complete!")

if __name__ == "__main__":
    main()
