from typing import List, Type
from pydantic import BaseModel, Field
from crewai.tools import BaseTool
import os
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Scopes
SCOPES = ['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/documents']

class DriveAuth:
    """Helper to authenticate with Google Drive"""
    @staticmethod
    def authenticate():
        # First try environment variable (absolute path)
        creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        
        # If relative or not set, resolve relative to this file
        if not creds_path or not os.path.isabs(creds_path):
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            creds_path = os.path.join(base_dir, "credentials.json")
        
        if not os.path.exists(creds_path):
            raise FileNotFoundError(f"Service account key not found at: {creds_path}")
        
        creds = service_account.Credentials.from_service_account_file(
            creds_path, scopes=SCOPES
        )
        return creds

class DriveListInput(BaseModel):
    folder_id: str = Field(description="The ID of the folder to list files from. Use 'root' or 'all' to list all accessible files and folders.")

class DriveListTool(BaseTool):
    name: str = "Google Drive Lister"
    description: str = "Lists files and folders in a specific Google Drive folder. Use folder_id='root' or 'all' to see all accessible files."
    args_schema: Type[BaseModel] = DriveListInput

    def _run(self, folder_id: str = 'root') -> str:
        try:
            creds = DriveAuth.authenticate()
            service = build('drive', 'v3', credentials=creds)
            
            # For service accounts, 'root' means "list all shared files"
            if folder_id.lower() in ['root', 'all', '']:
                # List all files accessible to service account
                query = "trashed = false"
            else:
                # List files in specific folder
                query = f"'{folder_id}' in parents and trashed = false"
            
            results = service.files().list(
                q=query,
                pageSize=50,  # Increased for better coverage
                fields="nextPageToken, files(id, name, mimeType, parents)"
            ).execute()
            items = results.get('files', [])

            if not items:
                return 'No files found. The service account may not have access to any files.'
            
            # Organize by type
            folders = [i for i in items if i['mimeType'] == 'application/vnd.google-apps.folder']
            files = [i for i in items if i['mimeType'] != 'application/vnd.google-apps.folder']
            
            output = f"Found {len(folders)} folders and {len(files)} files:\n\n"
            
            output += "📁 FOLDERS:\n"
            for item in sorted(folders, key=lambda x: x['name']):
                output += f"  - {item['name']} (ID: {item['id']})\n"
            
            output += "\n📄 FILES:\n"
            for item in sorted(files, key=lambda x: x['name'])[:20]:  # First 20 files
                output += f"  - {item['name']} (ID: {item['id']})\n"
            
            if len(files) > 20:
                output += f"  ... and {len(files) - 20} more files\n"
            
            return output
        except Exception as e:
            return f"Error listing files: {str(e)}"

class DriveReadInput(BaseModel):
    file_id: str = Field(description="The ID of the Google Doc to read.")

class DriveReadTool(BaseTool):
    name: str = "Google Doc Reader"
    description: str = "Reads the text content of a Google Doc."
    args_schema: Type[BaseModel] = DriveReadInput

    def _run(self, file_id: str) -> str:
        try:
            creds = DriveAuth.authenticate()
            # For Docs, we need the docs service
            service = build('docs', 'v1', credentials=creds)
            
            document = service.documents().get(documentId=file_id).execute()
            
            # Simple text extraction
            text = ""
            for content in document.get('body').get('content'):
                if 'paragraph' in content:
                    elements = content.get('paragraph').get('elements')
                    for elem in elements:
                        if 'textRun' in elem:
                            text += elem.get('textRun').get('content')
            return text
        except Exception as e:
            return f"Error reading doc: {str(e)}"

class DriveWriteInput(BaseModel):
    title: str = Field(description="Title of the new document")
    content: str = Field(description="Text content to write into the document")

class DriveWriteTool(BaseTool):
    name: str = "Google Doc Creator"
    description: str = "Creates a new Google Doc with the specified content."
    args_schema: Type[BaseModel] = DriveWriteInput

    def _run(self, title: str, content: str) -> str:
        try:
            from googleapiclient.http import MediaIoBaseUpload
            import io
            
            creds = DriveAuth.authenticate()
            docs_service = build('docs', 'v1', credentials=creds)
            drive_service = build('drive', 'v3', credentials=creds)
            
            # Target Folder ID for '02_In_Development'
            TARGET_FOLDER_ID = '1fKYixOC9aDcm-XHAIHhfGj3rKlRg5b-i'
            
            # 1. Prepare Metadata
            file_metadata = {
                'name': title,
                'mimeType': 'application/vnd.google-apps.document',
                'parents': [TARGET_FOLDER_ID]
            }
            
            # 2. Create via Upload Bypass
            # Uploading a file (even empty) acts differently than creating a native doc from scratch
            media = MediaIoBaseUpload(io.BytesIO(b' '), mimetype='text/plain', resumable=True)
            
            doc = drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            
            doc_id = doc.get('id')
            
            # 3. Insert content (if any)
            if content:
                requests = [
                    {
                        'insertText': {
                            'location': {
                                'index': 1,
                            },
                            'text': content
                        }
                    }
                ]
                docs_service.documents().batchUpdate(documentId=doc_id, body={'requests': requests}).execute()
            
            return f"Successfully created document '{title}' in 'In_Development' (ID: {doc_id})"
        except Exception as e:
            return f"Error creating doc: {str(e)}"

