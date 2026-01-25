"""Find the correct folder ID for Life with AI."""
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials

creds = Credentials.from_service_account_file(
    r'C:\Users\blues\.pai\skills\credentials.json',
    scopes=['https://www.googleapis.com/auth/drive']
)
drive = build('drive', 'v3', credentials=creds)

# Search for Life with AI folder
try:
    result = drive.files().list(
        q="name='Life with AI' and mimeType='application/vnd.google-apps.folder'",
        fields='files(id, name, parents)'
    ).execute()
    
    folders = result.get('files', [])
    if folders:
        print("Found folders:")
        for f in folders:
            print(f"  Name: {f['name']}")
            print(f"  ID: {f['id']}")
            print(f"  Parents: {f.get('parents', 'None')}")
            print()
            
            # List contents of this folder
            print(f"  Contents of {f['name']}:")
            contents = drive.files().list(
                q=f"'{f['id']}' in parents",
                pageSize=10,
                fields='files(id, name, mimeType)'
            ).execute()
            for c in contents.get('files', []):
                print(f"    - {c['name']} ({c['mimeType']})")
    else:
        print("No 'Life with AI' folder found")
        print("\nListing all accessible files:")
        all_files = drive.files().list(pageSize=10, fields='files(id, name)').execute()
        for f in all_files.get('files', []):
            print(f"  - {f['name']} (ID: {f['id']})")
            
except Exception as e:
    print(f"Error: {e}")
