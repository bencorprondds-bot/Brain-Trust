from typing import List, Type
from pydantic import BaseModel, Field
from crewai.tools import BaseTool
import os
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Scopes
SCOPES = ['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/documents']

# Shared Drive Configuration
SHARED_DRIVE_ID = '0AMpJ2pkSpYq-Uk9PVA'  # Life with AI Shared Drive

# Folder IDs (from Life with AI Shared Drive - Updated Jan 2026)
FOLDER_IDS = {
    'in_development': '1_AcAlToFkwKwG34FLij54suGOiQ68p_d',  # 02_In_Development
    'inbox': '1RKLpafuip4HgYj_bmuUfuj3ojZWNb1WZ',           # 01_Inbox
    'ready_for_review': '1va471qBT7Mogi4ymMz_zS6oW0DSQ3QJs', # 03_Ready_for_Review
    'published': '1SMKJVYbtUJdc0za5X9VD689tzo5A1-_o',       # 04_Published
    'characters': '1TNzmGFe28yzga77O34YoF_m0F1WMzcbL',      # Characters
    'reference_docs': '1rso6i2_mRFSOKmLC19EL6JtT2h1xzc2M',  # Reference_Docs
    'agent_prompts': '1JvMDwstlpXusW6lCSrRlVazCjJvtnA_Y',   # Agent_Prompts
    'workflows': '10NH-ufIi7PNNVL6SFW5ClgAJ5j2tM4iv',       # Workflows
    'world': '1Iik6DK8RDsLw-nBRTwaaJ3A8c3dP1RZP',          # World
}

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
            
            # Collect all items across all pages
            items = []
            page_token = None
            
            # Query shared drive with proper support for all drives
            if folder_id.lower() in ['root', 'all', '']:
                # List all files from Shared Drive
                query = "trashed = false"
            else:
                # List files in specific folder on Shared Drive
                query = f"'{folder_id}' in parents and trashed = false"
            
            # Paginate through all results
            while True:
                results = service.files().list(
                    q=query,
                    corpora='drive',
                    driveId=SHARED_DRIVE_ID,
                    includeItemsFromAllDrives=True,
                    supportsAllDrives=True,
                    pageSize=100,  # Increased for efficiency
                    fields="nextPageToken, files(id, name, mimeType, parents)",
                    pageToken=page_token
                ).execute()
                
                items.extend(results.get('files', []))
                page_token = results.get('nextPageToken')
                if not page_token:
                    break

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
    folder: str = Field(default="in_development", description="Target folder name: 'inbox', 'in_development', 'ready_for_review', 'published', 'characters', 'agent_prompts', 'reference_docs', 'workflows', 'world', etc.")

class DriveWriteTool(BaseTool):
    name: str = "Google Doc Creator"
    description: str = "Creates a new Google Doc with the specified content in a specific folder."
    args_schema: Type[BaseModel] = DriveWriteInput

    def _run(self, title: str, content: str, folder: str = "in_development") -> str:
        try:
            from googleapiclient.http import MediaIoBaseUpload
            import io
            
            creds = DriveAuth.authenticate()
            docs_service = build('docs', 'v1', credentials=creds)
            drive_service = build('drive', 'v3', credentials=creds)
            
            # Look up the folder ID from FOLDER_IDS
            target_folder = FOLDER_IDS.get(folder.lower())
            if not target_folder:
                available_folders = ", ".join(FOLDER_IDS.keys())
                return f"❌ Folder '{folder}' not found. Available folders: {available_folders}"
            
            # 1. Prepare Metadata
            file_metadata = {
                'name': title,
                'mimeType': 'application/vnd.google-apps.document',
                'parents': [target_folder]
            }
            
            # 2. Create via Upload Bypass
            # Uploading a file (even empty) acts differently than creating a native doc from scratch
            media = MediaIoBaseUpload(io.BytesIO(b' '), mimetype='text/plain', resumable=True)
            
            doc = drive_service.files().create(
                body=file_metadata,
                media_body=media,
                supportsAllDrives=True,
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
            
            folder_display = folder.replace('_', ' ').title()
            return f"✅ Successfully created document '{title}' in '{folder_display}' folder (ID: {doc_id})"
        except Exception as e:
            return f"❌ Error creating doc: {str(e)}"

class WordDocExportInput(BaseModel):
    file_id: str = Field(description="The ID of the Word document (.docx) to export as text")

class WordDocExportTool(BaseTool):
    name: str = "Word Document Exporter"
    description: str = "Exports Word documents (.docx files) as plain text. Use this for .docx files that can't be read with Google Docs API."
    args_schema: Type[BaseModel] = WordDocExportInput

    def _run(self, file_id: str) -> str:
        try:
            creds = DriveAuth.authenticate()
            drive_service = build('drive', 'v3', credentials=creds)
            
            # Export as plain text
            request = drive_service.files().export_media(
                fileId=file_id,
                mimeType='text/plain'
            )
            
            content = request.execute()
            text = content.decode('utf-8')
            
            if not text.strip():
                return "📄 Word document appears to be empty or contains no extractable text"
            
            return f"📄 Word document content:\n\n{text}"
        except Exception as e:
            # If export fails, try getting file metadata to provide better error
            try:
                file_metadata = drive_service.files().get(fileId=file_id, fields="name,mimeType").execute()
                mime_type = file_metadata.get('mimeType', 'unknown')
                name = file_metadata.get('name', 'unknown')
                return f"❌ Cannot export file '{name}' (type: {mime_type}). Error: {str(e)}"
            except:
                return f"❌ Error exporting Word document: {str(e)}"

class FindFolderInput(BaseModel):
    folder_name: str = Field(description="The name of the folder to find in the Shared Drive")

class FindFolderTool(BaseTool):
    name: str = "Google Drive Folder Finder"
    description: str = "Searches the Shared Drive for a folder by name. Returns the folder ID and location."
    args_schema: Type[BaseModel] = FindFolderInput

    def _run(self, folder_name: str) -> str:
        try:
            if not folder_name or not folder_name.strip():
                return "❌ Folder name cannot be empty"

            normalized = folder_name.strip().lower().replace(" ", "_")
            if "_" in normalized:
                # collapse repeated underscores
                while "__" in normalized:
                    normalized = normalized.replace("__", "_")

            # Remove numeric prefixes like 01_, 02_, etc.
            import re
            normalized = re.sub(r"^\d+_", "", normalized)

            # Direct mapping for known folder keys
            if normalized in FOLDER_IDS:
                folder_id = FOLDER_IDS[normalized]
                display_name = folder_name.strip()
                spaced_name = display_name.replace("_", " ")
                return (
                    f"✅ Found 1 folder named '{display_name}':\n"
                    f"(Display name: {spaced_name})\n\n"
                    f"📁 {display_name}\n"
                    f"   ID: {folder_id}\n"
                    f"   Parents: {SHARED_DRIVE_ID}\n"
                )

            creds = DriveAuth.authenticate()
            service = build('drive', 'v3', credentials=creds)
            
            # Search for folders with this name in the Shared Drive
            query = f"name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
            
            results = service.files().list(
                q=query,
                corpora='drive',
                driveId=SHARED_DRIVE_ID,
                includeItemsFromAllDrives=True,
                supportsAllDrives=True,
                pageSize=100,
                fields="files(id, name, parents)"
            ).execute()
            
            folders = results.get('files', [])
            
            if not folders:
                return f"❌ Folder '{folder_name}' not found in Shared Drive"
            
            output = f"✅ Found {len(folders)} folder(s) named '{folder_name}':\n\n"
            for folder in folders:
                output += f"📁 {folder['name']}\n"
                output += f"   ID: {folder['id']}\n"
                output += f"   Parents: {folder.get('parents', ['root'])[0]}\n\n"
            
            return output
        except Exception as e:
            return f"Error finding folder: {str(e)}"

class DocsEditInput(BaseModel):
    doc_id: str = Field(description="The ID of the Google Doc to edit")
    operation: str = Field(description="Operation to perform: 'read', 'append', 'insert', 'replace', or 'clear'")
    text: str = Field(default="", description="Text content for append, insert, or replace operations")
    index: int = Field(default=1, description="Index position for insert operation (1-based)")

class DocsEditTool(BaseTool):
    name: str = "Google Docs Editor"
    description: str = "Read, edit, and manage Google Docs content. Supports read, append, insert, replace, and clear operations."
    args_schema: Type[BaseModel] = DocsEditInput

    def _run(self, doc_id: str, operation: str, text: str = "", index: int = 1) -> str:
        try:
            creds = DriveAuth.authenticate()
            docs_service = build('docs', 'v1', credentials=creds)
            
            operation = operation.lower().strip()
            
            # READ operation
            if operation == 'read':
                document = docs_service.documents().get(documentId=doc_id).execute()
                content = document.get('body', {}).get('content', [])
                
                text_content = ""
                for block in content:
                    if 'paragraph' in block:
                        for element in block['paragraph'].get('elements', []):
                            if 'textRun' in element:
                                text_content += element['textRun'].get('content', '')
                
                if not text_content.strip():
                    return f"📄 Document is empty or contains only formatting"
                return f"📄 Document content:\n\n{text_content}"
            
            # APPEND operation - add text to end of document
            elif operation == 'append':
                if not text:
                    return "❌ Append requires 'text' parameter"
                
                document = docs_service.documents().get(documentId=doc_id).execute()
                end_index = document['body']['content'][-1]['endIndex']
                
                requests = [
                    {
                        'insertText': {
                            'location': {'index': end_index},
                            'text': text
                        }
                    }
                ]
                docs_service.documents().batchUpdate(documentId=doc_id, body={'requests': requests}).execute()
                return f"✅ Appended {len(text)} characters to document"
            
            # INSERT operation - insert text at specific position
            elif operation == 'insert':
                if not text:
                    return "❌ Insert requires 'text' parameter"
                
                requests = [
                    {
                        'insertText': {
                            'location': {'index': index},
                            'text': text
                        }
                    }
                ]
                docs_service.documents().batchUpdate(documentId=doc_id, body={'requests': requests}).execute()
                return f"✅ Inserted {len(text)} characters at position {index}"
            
            # REPLACE operation - replace all content
            elif operation == 'replace':
                if not text:
                    return "❌ Replace requires 'text' parameter"
                
                document = docs_service.documents().get(documentId=doc_id).execute()
                body_content = document['body']['content']
                
                # Find the end index of document content
                end_index = 1
                for block in body_content:
                    if 'endIndex' in block:
                        end_index = block['endIndex']
                
                requests = [
                    {
                        'deleteContentRange': {
                            'range': {
                                'startIndex': 1,
                                'endIndex': end_index
                            }
                        }
                    },
                    {
                        'insertText': {
                            'location': {'index': 1},
                            'text': text
                        }
                    }
                ]
                docs_service.documents().batchUpdate(documentId=doc_id, body={'requests': requests}).execute()
                return f"✅ Replaced document content with {len(text)} characters"
            
            # CLEAR operation - delete all content
            elif operation == 'clear':
                document = docs_service.documents().get(documentId=doc_id).execute()
                body_content = document['body']['content']
                
                end_index = 1
                for block in body_content:
                    if 'endIndex' in block:
                        end_index = block['endIndex']
                
                requests = [
                    {
                        'deleteContentRange': {
                            'range': {
                                'startIndex': 1,
                                'endIndex': end_index
                            }
                        }
                    }
                ]
                docs_service.documents().batchUpdate(documentId=doc_id, body={'requests': requests}).execute()
                return f"✅ Cleared all content from document"
            
            else:
                valid_ops = "read, append, insert, replace, clear"
                return f"❌ Invalid operation '{operation}'. Valid operations: {valid_ops}"
                
        except Exception as e:
            return f"❌ Error editing document: {str(e)}"