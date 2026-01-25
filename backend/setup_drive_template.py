#!/usr/bin/env python3
"""
Setup script for Google Drive template document.

This script helps you create and configure the template document required
for the Librarian (Iris) to create new files in Google Drive.

WHY TEMPLATES ARE NEEDED:
Service accounts have storage quota limits and cannot create new files
in user-owned My Drive folders. However, they CAN:
  1. Copy existing files (the copy inherits ownership from the original)
  2. Edit files they have access to
  3. Move files between folders

By copying a template document, we bypass the quota limitation because
the new file is owned by YOU, not the service account.

USAGE:
  python setup_drive_template.py

This will:
  1. Check if a template already exists
  2. Create a new template document if needed
  3. Output the template ID for you to copy into drive_tool.py
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/documents']

# Template document name (used to find existing templates)
TEMPLATE_NAME = "_BrainTrust_Template"

# Known folder IDs
FOLDER_IDS = {
    'life_with_ai': '1duf6BRY-tqyWzP3gH1clfaM5B-Qqh0r5',
    'in_development': '1fKYixOC9aDcm-XHAIHhfGj3rKlRg5b-i',
}


def get_credentials():
    """Get service account credentials."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    creds_path = os.path.join(base_dir, "credentials.json")

    if not os.path.exists(creds_path):
        print(f"ERROR: credentials.json not found at {creds_path}")
        sys.exit(1)

    return service_account.Credentials.from_service_account_file(creds_path, scopes=SCOPES)


def find_existing_template(drive_service):
    """Look for an existing template document."""
    query = f"name = '{TEMPLATE_NAME}' and mimeType = 'application/vnd.google-apps.document' and trashed = false"

    results = drive_service.files().list(
        q=query,
        fields="files(id, name, owners)"
    ).execute()

    files = results.get('files', [])
    return files[0] if files else None


def create_template_instructions():
    """Print instructions for manual template creation."""
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    MANUAL TEMPLATE SETUP REQUIRED                           ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  The service account cannot create the template (quota limits).             ║
║  Please follow these steps:                                                  ║
║                                                                              ║
║  1. Open Google Drive in your browser                                       ║
║                                                                              ║
║  2. Navigate to your "Life with AI" folder                                  ║
║                                                                              ║
║  3. Create a new Google Doc with the EXACT name:                            ║
║     _BrainTrust_Template                                                    ║
║                                                                              ║
║  4. Leave it blank (or add placeholder text that will be replaced)          ║
║                                                                              ║
║  5. Share the document with your service account email:                     ║
║     (Check your credentials.json for 'client_email')                        ║
║     Give it "Editor" access                                                 ║
║                                                                              ║
║  6. Run this script again to verify and get the template ID                 ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
""")


def main():
    print("=" * 70)
    print("BRAIN TRUST - GOOGLE DRIVE TEMPLATE SETUP")
    print("=" * 70)

    creds = get_credentials()
    print(f"\n✅ Authenticated as: {creds.service_account_email}")

    drive_service = build('drive', 'v3', credentials=creds)

    # Check for existing template
    print(f"\n🔍 Looking for existing template '{TEMPLATE_NAME}'...")
    template = find_existing_template(drive_service)

    if template:
        template_id = template['id']
        print(f"\n✅ TEMPLATE FOUND!")
        print(f"   Name: {template['name']}")
        print(f"   ID: {template_id}")

        print("\n" + "=" * 70)
        print("NEXT STEP: Update drive_tool.py")
        print("=" * 70)
        print(f"""
Open: backend/app/tools/drive_tool.py

Find this section (around line 35):

    TEMPLATE_IDS = {{
        'default': None,  # Set this to your template document ID
        ...
    }}

Change it to:

    TEMPLATE_IDS = {{
        'default': '{template_id}',
        'article': '{template_id}',
        'character': '{template_id}',
    }}

Save the file and restart the Brain Trust backend.
""")

        # Test that we can copy the template
        print("\n🧪 Testing template copy...")
        try:
            test_copy = drive_service.files().copy(
                fileId=template_id,
                body={'name': '_TEST_COPY_DELETE_ME'}
            ).execute()

            test_id = test_copy['id']
            print(f"   ✅ Successfully copied template (test file ID: {test_id})")

            # Clean up test file
            drive_service.files().delete(fileId=test_id).execute()
            print("   ✅ Cleaned up test file")
            print("\n🎉 Template system is ready! Iris can now create documents.")

        except Exception as e:
            print(f"   ❌ Copy test failed: {e}")
            print("   Make sure the template is shared with the service account as 'Editor'")

    else:
        print("\n❌ No template found.")
        create_template_instructions()

        # Show service account email for sharing
        print(f"\nService account email to share with:")
        print(f"   {creds.service_account_email}")

        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
