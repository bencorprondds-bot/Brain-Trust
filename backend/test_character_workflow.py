"""
Multi-Agent Simulation: Librarian + Editor
Goal: Create/Edit a Character Profile for 'Nexus' in the correct folder.

Workflow:
1. Librarian (Iris): Locates 'Life with AI/02_In_Development/Characters'.
2. Editor: Checks for 'Nexus_Profile' doc in that folder.
3. Editor: If found, reads -> appends -> checks style.
          If not found, prompts User to create it (due to Service Account quota).
"""
import sys
import os
import time

# Add skills to path
skills_path = os.path.expanduser("~/.pai/skills")
sys.path.append(skills_path)

try:
    import story_writer
    import style_checking
except ImportError as e:
    print(f"Error importing skills: {e}")
    sys.exit(1)

def get_drive_service():
    drive, _, error = story_writer.get_services()
    if error:
        print(f"Authentication Error: {error}")
        sys.exit(1)
    return drive

def librarian_find_folder(drive, parent_id, folder_name):
    """Librarian searches for a specific folder within a parent."""
    query = f"'{parent_id}' in parents and mimeType='application/vnd.google-apps.folder' and name='{folder_name}' and trashed=false"
    results = drive.files().list(q=query, fields='files(id, name)').execute()
    files = results.get('files', [])
    if files:
        return files[0]
    return None

def editor_find_doc(drive, parent_id, doc_name):
    """Editor searches for a document."""
    query = f"'{parent_id}' in parents and mimeType='application/vnd.google-apps.document' and name='{doc_name}' and trashed=false"
    results = drive.files().list(q=query, fields='files(id, name)').execute()
    files = results.get('files', [])
    if files:
        return files[0]
    return None

def main():
    print("🤖 SIMULATION: Librarian (Iris) + Editor Agents")
    print("==============================================")
    
    drive = get_drive_service()
    
    # --- PHASE 1: LIBRARIAN ---
    print("\n[Librarian] 🔎 Locating 'Life with AI' root...")
    # Find Root
    root = librarian_find_folder(drive, 'root', 'Life with AI')
    
    # Fallback: Search blindly if not in root (shared with me)
    if not root:
        results = drive.files().list(q="name='Life with AI' and mimeType='application/vnd.google-apps.folder'", fields='files(id, name)').execute()
        files = results.get('files', [])
        if files: result = files[0]
        else: result = None
        root = result

    if not root:
        print("❌ [Librarian] Critical: 'Life with AI' folder not found.")
        return

    print(f"✅ Found Root: {root['name']} ({root['id']})")
    
    # Traverse Path: 02_In_Development -> Characters
    current_folder = root
    target_path = ["02_In_Development", "Characters"]
    
    for name in target_path:
        print(f"[Librarian] 🔎 Looking for '{name}'...")
        found = librarian_find_folder(drive, current_folder['id'], name)
        
        if found:
            print(f"   found: {found['name']}")
            current_folder = found
        else:
            print(f"❌ [Librarian] Folder '{name}' NOT found in '{current_folder['name']}'.")
            print(f"   ⚠️ Action Required: Please create folder '{name}' inside '{current_folder['name']}'.")
            return

    characters_folder_id = current_folder['id']
    print(f"✅ [Librarian] Target Reached: 'Characters' ({characters_folder_id})")
    
    # --- PHASE 2: EDITOR ---
    doc_name = "Nexus_Profile"
    print(f"\n[Editor] 📝 Checking for document: '{doc_name}'...")
    
    doc = editor_find_doc(drive, characters_folder_id, doc_name)
    
    if not doc:
        print(f"❌ [Editor] Document '{doc_name}' not found.")
        print(f"   ⚠️ Service Accounts cannot create new files.")
        print(f"   👉 PLEASE CREATE a Google Doc named '{doc_name}' in the 'Characters' folder manually.")
        return
        
    print(f"✅ [Editor] Found Document: {doc['name']} ({doc['id']})")
    
    # Edit Workflow
    print("\n[Editor] Reading content...")
    content = story_writer.read_doc(doc['id'])
    
    print("[Editor] Checking style...")
    style_report = style_checking.check_text(content)
    print(f"   Style Report: {style_report.splitlines()[0]}")
    
    print("[Editor] Appending character update...")
    update_text = "\n\n---\n**Character Update (Agent)**\n*Status*: Online\n*Role*: Central Connector\n*Note*: Verified by Librarian.\n---"
    
    result = story_writer.append_text(doc['id'], update_text)
    print(f"   {result}")
    
    print("\nSUCCESS! Workflow completed.")
    print(f"View here: https://docs.google.com/document/d/{doc['id']}/edit")

if __name__ == "__main__":
    main()
