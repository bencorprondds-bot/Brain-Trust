from typing import List, Type
from pydantic import BaseModel, Field
from crewai.tools import BaseTool
import os
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Scopes
SCOPES = ['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/documents']

# =============================================================================
# SHARED DRIVE CONFIGURATION - Life with AI
# =============================================================================
SHARED_DRIVE_ID = '0AMpJ2pkSpYq-Uk9PVA'

# Canonical folder IDs from the Shared Drive
FOLDER_IDS = {
    # Editorial Pipeline
    'system': '1_85nRX4isDeoshv98bFL3ARljJ4LTkT0',
    'inbox': '1RKLpafuip4HgYj_bmuUfuj3ojZWNb1WZ',
    'in_development': '1_AcAlToFkwKwG34FLij54suGOiQ68p_d',
    'ready_for_review': '1va471qBT7Mogi4ymMz_zS6oW0DSQ3QJs',
    'beta_readers': '1HwyGuQroOXsxQPJ1paCyTcdv6h14hPXs',
    'published': '1SMKJVYbtUJdc0za5X9VD689tzo5A1-_o',
    # Characters
    'characters': '1TNzmGFe28yzga77O34YoF_m0F1WMzcbL',
    'character_in_development': '1I4KaPh3PPKyQoRnYDJ_miWxvaMWToF8R',
    # Reference & Assets
    'agent_prompts': '1JvMDwstlpXusW6lCSrRlVazCjJvtnA_Y',
    'voice_library': '1UuJOd9eM_V_jn4LH_pG_fybZOGcz4CEU',
    'workflows': '10NH-ufIi7PNNVL6SFW5ClgAJ5j2tM4iv',
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
    folder_id: str = Field(default='root', description="The ID of the folder to list, OR a folder name like 'inbox', 'in_development', 'characters'. Use 'root' or 'all' to list all files.")
    search_query: str = Field(default='', description="Optional: Search for files by name. Example: 'Arun' will find all files with 'Arun' in the name.")

class DriveListTool(BaseTool):
    name: str = "Google Drive Lister"
    description: str = "Lists and searches files in Google Drive. Can list folder contents or search by filename. Use search_query to find files like 'Arun' or 'style guide'."
    args_schema: Type[BaseModel] = DriveListInput

    def _run(self, folder_id: str = 'root', search_query: str = '') -> str:
        try:
            creds = DriveAuth.authenticate()
            service = build('drive', 'v3', credentials=creds)

            # Resolve folder name to ID if needed
            resolved_folder_id = folder_id
            if folder_id.lower() in FOLDER_IDS:
                resolved_folder_id = FOLDER_IDS[folder_id.lower()]
            elif folder_id.lower().replace(' ', '_') in FOLDER_IDS:
                resolved_folder_id = FOLDER_IDS[folder_id.lower().replace(' ', '_')]

            # Build query
            query_parts = ["trashed = false"]

            # Add search filter if provided
            if search_query:
                query_parts.append(f"name contains '{search_query}'")

            query = " and ".join(query_parts)

            # For 'root' or 'all', search entire Shared Drive
            if folder_id.lower() in ['root', 'all', '']:
                results = service.files().list(
                    q=query,
                    corpora='drive',
                    driveId=SHARED_DRIVE_ID,
                    includeItemsFromAllDrives=True,
                    supportsAllDrives=True,
                    pageSize=100,
                    fields="nextPageToken, files(id, name, mimeType, parents)"
                ).execute()
            else:
                # List files in specific folder
                folder_query = f"'{resolved_folder_id}' in parents and {query}"
                results = service.files().list(
                    q=folder_query,
                    includeItemsFromAllDrives=True,
                    supportsAllDrives=True,
                    pageSize=100,
                    fields="nextPageToken, files(id, name, mimeType, parents)"
                ).execute()

            items = results.get('files', [])

            if not items:
                if search_query:
                    return f"No files found matching '{search_query}'. Try a different search term."
                return 'No files found in this location.'

            # Organize by type
            folders = [i for i in items if i['mimeType'] == 'application/vnd.google-apps.folder']
            files = [i for i in items if i['mimeType'] != 'application/vnd.google-apps.folder']

            search_msg = f" matching '{search_query}'" if search_query else ""
            output = f"Found {len(folders)} folders and {len(files)} files{search_msg}:\n\n"

            if folders:
                output += "📁 FOLDERS:\n"
                for item in sorted(folders, key=lambda x: x['name']):
                    output += f"  - {item['name']} (ID: {item['id']})\n"

            if files:
                output += "\n📄 FILES:\n"
                for item in sorted(files, key=lambda x: x['name'])[:30]:
                    # Show file type indicator
                    mime = item.get('mimeType', '')
                    if 'document' in mime:
                        icon = "[Doc]"
                    elif 'spreadsheet' in mime:
                        icon = "[Sheet]"
                    elif mime.endswith('.document'):
                        icon = "[GDoc]"
                    elif 'wordprocessingml' in mime or item['name'].endswith('.docx'):
                        icon = "[Word]"
                    elif item['name'].endswith('.md'):
                        icon = "[MD]"
                    elif item['name'].endswith('.pdf'):
                        icon = "[PDF]"
                    else:
                        icon = "[File]"
                    output += f"  {icon} {item['name']} (ID: {item['id']})\n"

                if len(files) > 30:
                    output += f"  ... and {len(files) - 30} more files\n"

            return output
        except Exception as e:
            return f"Error listing files: {str(e)}"

class DriveReadInput(BaseModel):
    file_id: str = Field(description="The ID of the file to read. Works with Google Docs, Word docs (.docx), and text files (.md, .txt).")

class DriveReadTool(BaseTool):
    name: str = "Google Doc Reader"
    description: str = "Reads text content from files. Supports Google Docs (native), Word documents (.docx), and text files (.md, .txt)."
    args_schema: Type[BaseModel] = DriveReadInput

    def _run(self, file_id: str) -> str:
        try:
            creds = DriveAuth.authenticate()
            drive_service = build('drive', 'v3', credentials=creds)

            # First, get file metadata to determine type
            file_meta = drive_service.files().get(
                fileId=file_id,
                fields='name, mimeType',
                supportsAllDrives=True
            ).execute()

            mime_type = file_meta.get('mimeType', '')
            file_name = file_meta.get('name', '')

            # Handle native Google Docs
            if mime_type == 'application/vnd.google-apps.document':
                docs_service = build('docs', 'v1', credentials=creds)
                document = docs_service.documents().get(documentId=file_id).execute()

                text = ""
                for content in document.get('body', {}).get('content', []):
                    if 'paragraph' in content:
                        elements = content.get('paragraph').get('elements', [])
                        for elem in elements:
                            if 'textRun' in elem:
                                text += elem.get('textRun').get('content', '')
                return text if text.strip() else "(Document is empty)"

            # Handle Word docs (.docx) - export as plain text
            elif mime_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' or file_name.endswith('.docx'):
                # Export as plain text
                response = drive_service.files().export(
                    fileId=file_id,
                    mimeType='text/plain'
                ).execute()
                return response.decode('utf-8') if isinstance(response, bytes) else str(response)

            # Handle text files (.md, .txt) - download directly
            elif mime_type.startswith('text/') or file_name.endswith(('.md', '.txt', '.json')):
                response = drive_service.files().get_media(
                    fileId=file_id
                ).execute()
                return response.decode('utf-8') if isinstance(response, bytes) else str(response)

            # Handle PDFs - can't read directly, but inform user
            elif mime_type == 'application/pdf' or file_name.endswith('.pdf'):
                return f"Cannot read PDF files directly. File: {file_name}"

            # Unknown type - try to export as text
            else:
                try:
                    response = drive_service.files().export(
                        fileId=file_id,
                        mimeType='text/plain'
                    ).execute()
                    return response.decode('utf-8') if isinstance(response, bytes) else str(response)
                except Exception:
                    return f"Cannot read file type: {mime_type}. File: {file_name}"

        except Exception as e:
            return f"Error reading file: {str(e)}"

class DriveWriteInput(BaseModel):
    title: str = Field(description="Title of the new document")
    content: str = Field(default='', description="Text content to write into the document. Can be empty for blank docs.")
    target_folder: str = Field(default='in_development', description="Target folder: 'inbox', 'in_development', 'ready_for_review', 'published', 'characters', etc.")

class DriveWriteTool(BaseTool):
    name: str = "Google Doc Creator"
    description: str = "Creates a new Google Doc in the specified folder. Use target_folder to choose: 'inbox', 'in_development', 'ready_for_review', 'published', 'characters', etc."
    args_schema: Type[BaseModel] = DriveWriteInput

    def _run(self, title: str, content: str = '', target_folder: str = 'in_development') -> str:
        try:
            from googleapiclient.http import MediaIoBaseUpload
            import io

            creds = DriveAuth.authenticate()
            docs_service = build('docs', 'v1', credentials=creds)
            drive_service = build('drive', 'v3', credentials=creds)

            # Resolve folder name to ID
            folder_key = target_folder.lower().replace(' ', '_')
            if folder_key in FOLDER_IDS:
                target_folder_id = FOLDER_IDS[folder_key]
                folder_display_name = folder_key.replace('_', ' ').title()
            else:
                # If it looks like an ID (long string), use it directly
                if len(target_folder) > 20:
                    target_folder_id = target_folder
                    folder_display_name = "specified folder"
                else:
                    # Default to in_development
                    target_folder_id = FOLDER_IDS['in_development']
                    folder_display_name = "In Development"

            # 1. Prepare Metadata
            file_metadata = {
                'name': title,
                'mimeType': 'application/vnd.google-apps.document',
                'parents': [target_folder_id]
            }

            # 2. Create via Upload Bypass (with Shared Drive support)
            media = MediaIoBaseUpload(io.BytesIO(b' '), mimetype='text/plain', resumable=True)

            doc = drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id',
                supportsAllDrives=True
            ).execute()

            doc_id = doc.get('id')

            # 3. Insert content (if any)
            if content and content.strip():
                requests = [
                    {
                        'insertText': {
                            'location': {'index': 1},
                            'text': content
                        }
                    }
                ]
                docs_service.documents().batchUpdate(documentId=doc_id, body={'requests': requests}).execute()

            doc_url = f"https://docs.google.com/document/d/{doc_id}/edit"
            return f"Successfully created document '{title}' in '{folder_display_name}' folder.\nID: {doc_id}\nURL: {doc_url}"
        except Exception as e:
            return f"Error creating doc: {str(e)}"

