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
        # Resolve backend/credentials.json relative to this file
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        default_path = os.path.join(base_dir, "credentials.json")
        
        creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", default_path)
        if not os.path.exists(creds_path):
            raise FileNotFoundError(f"Service account key not found at: {creds_path}")
        
        creds = service_account.Credentials.from_service_account_file(
            creds_path, scopes=SCOPES
        )
        return creds

class DriveListInput(BaseModel):
    folder_id: str = Field(description="The ID of the folder to list files from. Use 'root' for top level.")

class DriveListTool(BaseTool):
    name: str = "Google Drive Lister"
    description: str = "Lists files and folders in a specific Google Drive folder."
    args_schema: Type[BaseModel] = DriveListInput

    def _run(self, folder_id: str = 'root') -> str:
        try:
            creds = DriveAuth.authenticate()
            service = build('drive', 'v3', credentials=creds)
            
            results = service.files().list(
                q=f"'{folder_id}' in parents and trashed = false",
                pageSize=10, fields="nextPageToken, files(id, name, mimeType)"
            ).execute()
            items = results.get('files', [])

            if not items:
                return 'No files found.'
            
            output = "Files found:\n"
            for item in items:
                output += f"{item['name']} ({item['id']}) - {item['mimeType']}\n"
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
            creds = DriveAuth.authenticate()
            docs_service = build('docs', 'v1', credentials=creds)
            drive_service = build('drive', 'v3', credentials=creds)
            
            # 1. Create blank doc
            doc = docs_service.documents().create(body={'title': title}).execute()
            doc_id = doc.get('documentId')
            
            # 2. Insert content
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
            
            return f"Successfully created document '{title}' (ID: {doc_id})"
        except Exception as e:
            return f"Error creating doc: {str(e)}"
