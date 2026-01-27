"""
Simulates an "Editor Agent" workflow using the new skills.
1. Finds a document in 'Life with AI'
2. Reads content using story_writer
3. Checks style using style_checker
4. Appends the style report back to the document
"""
import sys
import os

# Add skills to path
skills_path = os.path.expanduser("~/.pai/skills")
sys.path.append(skills_path)

try:
    import story_writer
    import style_checking as style_checker
except ImportError as e:
    print(f"Error importing skills: {e}")
    sys.exit(1)

def main():
    print("🤖 EDITOR AGENT SIMULATION STARTING...\n")
    
    # 1. Find a target document
    print("1. Searching for documents...")
    # Use the correct Shared Drive folder ID for 'in_development'
    folder_id = "1_AcAlToFkwKwG34FLij54suGOiQ68p_d"  # 02_In_Development from Shared Drive
    # Actually, let's just search by name to be safe
    from googleapiclient.discovery import build
    from google.oauth2.service_account import Credentials
    
    # We can use story_writer's service getter if we want, but let's trust the search for now.
    # Let's try to list using the skill first.
    output = story_writer.list_docs(folder_id)
    if "Error" in output or "No Google Docs" in output:
        # Fallback: search for the folder again to get fresh ID
        print("   Re-acquiring folder ID...")
        drive, _, _ = story_writer.get_services()
        results = drive.files().list(
            q="name='Life with AI' and mimeType='application/vnd.google-apps.folder'",
            fields='files(id)'
        ).execute()
        files = results.get('files', [])
        if not files:
            print("❌ Critical: 'Life with AI' folder not found.")
            return
        folder_id = files[0]['id']
        print(f"   Found Folder ID: {folder_id}")
        output = story_writer.list_docs(folder_id)

    print(output)
    
    # Parse the first doc ID from output (simple parsing)
    lines = output.splitlines()
    doc_id = None
    doc_name = None
    
    for i, line in enumerate(lines):
        if "ID:" in line:
            doc_id = line.split("ID:")[1].strip()
            doc_name = lines[i-1].strip('- ')
            break
            
    if not doc_id:
        print("❌ No documents found to test.")
        return
        
    print(f"✅ Target selected: '{doc_name}' ({doc_id})")
    
    # 2. Read content
    print(f"\n2. Reading document...")
    content = story_writer.read_doc(doc_id)
    print(f"   Read {len(content)} characters.")
    
    # 3. Check style
    print(f"\n3. Checking style rules...")
    report = style_checker.check_text(content)
    print(f"   Report generated:\n{report}")
    
    # 4. Append report to doc
    print(f"\n4. Appending report to document...")
    timestamp = "Automated Check"
    append_text = f"\n\n---\n**Editor Agent Report**\n{report}\n---"
    
    result = story_writer.append_text(doc_id, append_text)
    print(f"   {result}")
    
    print("\n🎉 SIMULATION COMPLETE.")
    print(f"   Check your document here: https://docs.google.com/document/d/{doc_id}/edit")

if __name__ == "__main__":
    main()
