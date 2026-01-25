
import os
import sys
from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/documents']

def check_docs_api():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    creds_path = os.path.join(base_dir, "credentials.json")
    
    try:
        creds = service_account.Credentials.from_service_account_file(creds_path, scopes=SCOPES)
        service = build('docs', 'v1', credentials=creds)
        
        # Try to creat a dummy doc to check API access
        print("Attempting to access Docs API...")
        service.documents().create(body={'title': 'API Test Doc'}).execute()
        print("✅ Success: Google Docs API is ENABLED.")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        # The error message usually contains the link to enable the API

if __name__ == "__main__":
    check_docs_api()
