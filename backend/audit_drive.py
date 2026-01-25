"""Comprehensive audit of Life with AI Google Drive folder structure."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/drive']

def get_all_files(service, folder_id=None, path=""):
    """Recursively get all files and folders."""
    query = "trashed = false"
    if folder_id:
        query = f"'{folder_id}' in parents and trashed = false"
    
    results = service.files().list(
        q=query,
        pageSize=100,
        fields="files(id, name, mimeType, parents, modifiedTime, size)"
    ).execute()
    
    items = results.get('files', [])
    all_items = []
    
    for item in items:
        item['path'] = f"{path}/{item['name']}" if path else item['name']
        all_items.append(item)
        
        if item['mimeType'] == 'application/vnd.google-apps.folder':
            # Recursively get contents
            children = get_all_files(service, item['id'], item['path'])
            all_items.extend(children)
    
    return all_items

def print_tree(items):
    """Print folder structure as tree."""
    # Build tree structure
    tree = {}
    for item in items:
        parts = item['path'].split('/')
        current = tree
        for i, part in enumerate(parts[:-1]):
            if part not in current:
                current[part] = {'__children': {}}
            current = current[part]['__children']
        
        name = parts[-1]
        is_folder = item['mimeType'] == 'application/vnd.google-apps.folder'
        icon = "📁" if is_folder else get_icon(item['mimeType'])
        current[name] = {
            '__info': f"{icon} {name}",
            '__id': item['id'],
            '__type': item['mimeType'],
            '__children': {} if is_folder else None
        }
    
    def print_level(node, indent=0):
        for key, value in sorted(node.items()):
            if key.startswith('__'):
                continue
            info = value.get('__info', key)
            print("  " * indent + info)
            if value.get('__children'):
                print_level(value['__children'], indent + 1)
    
    print_level(tree)

def get_icon(mime_type):
    """Get icon for file type."""
    if 'document' in mime_type:
        return "📄"
    elif 'spreadsheet' in mime_type:
        return "📊"
    elif 'image' in mime_type:
        return "🖼️"
    elif 'json' in mime_type:
        return "📋"
    elif 'text' in mime_type:
        return "📝"
    else:
        return "📎"

def main():
    print("=" * 70)
    print("LIFE WITH AI - COMPLETE DRIVE AUDIT")
    print("=" * 70)
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    creds_path = os.path.join(base_dir, "credentials.json")
    creds = service_account.Credentials.from_service_account_file(creds_path, scopes=SCOPES)
    service = build('drive', 'v3', credentials=creds)
    
    print("\n📂 Fetching all files and folders...\n")
    
    # Get all files (no parent filter = all shared files)
    all_items = get_all_files(service)
    
    # Separate folders and files
    folders = [i for i in all_items if i['mimeType'] == 'application/vnd.google-apps.folder']
    files = [i for i in all_items if i['mimeType'] != 'application/vnd.google-apps.folder']
    
    print(f"Total folders: {len(folders)}")
    print(f"Total files: {len(files)}")
    
    print("\n" + "=" * 70)
    print("FOLDER STRUCTURE")
    print("=" * 70 + "\n")
    
    # Print all folders
    for folder in sorted(folders, key=lambda x: x['path']):
        depth = folder['path'].count('/')
        print("  " * depth + f"📁 {folder['name']} [{folder['id'][:8]}...]")
    
    print("\n" + "=" * 70)
    print("ALL FILES BY FOLDER")
    print("=" * 70)
    
    # Group files by parent folder
    folder_map = {f['id']: f['name'] for f in folders}
    
    files_by_folder = {}
    for file in files:
        parent = file.get('parents', ['root'])[0] if file.get('parents') else 'root'
        parent_name = folder_map.get(parent, 'Root')
        if parent_name not in files_by_folder:
            files_by_folder[parent_name] = []
        files_by_folder[parent_name].append(file)
    
    for folder_name, folder_files in sorted(files_by_folder.items()):
        print(f"\n📁 {folder_name}/")
        for f in sorted(folder_files, key=lambda x: x['name']):
            icon = get_icon(f['mimeType'])
            size = f.get('size', 'N/A')
            print(f"   {icon} {f['name']}")
            print(f"      ID: {f['id']}")
            print(f"      Type: {f['mimeType']}")
    
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    # Count by type
    type_counts = {}
    for f in files:
        t = f['mimeType'].split('.')[-1] if '.' in f['mimeType'] else f['mimeType']
        type_counts[t] = type_counts.get(t, 0) + 1
    
    print("\nFiles by type:")
    for t, count in sorted(type_counts.items(), key=lambda x: -x[1]):
        print(f"  {t}: {count}")

if __name__ == "__main__":
    main()
