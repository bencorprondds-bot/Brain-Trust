"""
Test script to verify Google Docs API read/write access.
Lists documents in the folder and tests editing an existing one.

NOTE: Service accounts have storage quota limits - they can EDIT existing 
files but may not be able to CREATE new ones. Documents should be created 
by the user (Ben) and then the service account edits them.
"""
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
import os

SCOPES = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/documents'
]

def main():
    creds_path = os.path.join(os.path.dirname(__file__), 'credentials.json')
    creds = Credentials.from_service_account_file(creds_path, scopes=SCOPES)
    
    drive = build('drive', 'v3', credentials=creds)
    docs = build('docs', 'v1', credentials=creds)
    
    print("1. Finding 'Life with AI' folder...")
    results = drive.files().list(
        q="name='Life with AI' and mimeType='application/vnd.google-apps.folder'",
        fields='files(id, name)'
    ).execute()
    
    folders = results.get('files', [])
    if not folders:
        print("   ERROR: Could not find folder.")
        return
    
    folder_id = folders[0]['id']
    print(f"   Found folder ID: {folder_id}")
    
    print("\n2. Listing Google Docs in folder...")
    docs_list = drive.files().list(
        q=f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.document'",
        fields='files(id, name)',
        pageSize=10
    ).execute()
    
    doc_files = docs_list.get('files', [])
    if not doc_files:
        print("   No Google Docs found in folder.")
        print("   Please create a test document manually in 'Life with AI' folder.")
        return
    
    print(f"   Found {len(doc_files)} document(s):")
    for i, f in enumerate(doc_files):
        print(f"      [{i}] {f['name']} (ID: {f['id']})")
    
    # Pick the first doc to test
    test_doc = doc_files[0]
    doc_id = test_doc['id']
    print(f"\n3. Testing READ on '{test_doc['name']}'...")
    
    doc = docs.documents().get(documentId=doc_id).execute()
    title = doc.get('title', 'Untitled')
    content = doc.get('body', {}).get('content', [])
    
    # Count characters
    char_count = 0
    for element in content:
        if 'paragraph' in element:
            for text_run in element['paragraph'].get('elements', []):
                if 'textRun' in text_run:
                    char_count += len(text_run['textRun'].get('content', ''))
    
    print(f"   Title: {title}")
    print(f"   Character count: {char_count}")
    print("   ✅ READ access confirmed!")
    
    print(f"\n4. Testing WRITE on '{test_doc['name']}'...")
    # Append a comment at the end of the document
    end_index = content[-1].get('endIndex', 1) if content else 1
    
    test_text = "\n\n[Brain Trust Test: Write access verified!]\n"
    requests = [
        {
            'insertText': {
                'location': {'index': end_index - 1},
                'text': test_text
            }
        }
    ]
    
    try:
        docs.documents().batchUpdate(
            documentId=doc_id,
            body={'requests': requests}
        ).execute()
        print("   ✅ WRITE access confirmed!")
        print(f"   Appended test text to document.")
        print(f"\n🎉 SUCCESS! Full read/write access working.")
        print(f"   View: https://docs.google.com/document/d/{doc_id}/edit")
    except Exception as e:
        print(f"   ❌ WRITE failed: {e}")

if __name__ == '__main__':
    main()
