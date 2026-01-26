from typing import List, Type, Optional
from pydantic import BaseModel, Field
from crewai.tools import BaseTool
import os
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Scopes
SCOPES = ['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/documents']

# Editorial Pipeline Folder IDs
# These are loaded from environment variables (preferred) or fall back to defaults.
# To configure for your Shared Drive:
#   1. Get folder IDs from your Google Drive URLs (the long string after /folders/)
#   2. Set environment variables: DRIVE_FOLDER_INBOX, DRIVE_FOLDER_IN_DEVELOPMENT, etc.
#   3. Or update the defaults below for your setup
#
# Environment variable format: DRIVE_FOLDER_{NAME} where NAME is uppercase with underscores
# Example: DRIVE_FOLDER_IN_DEVELOPMENT=1abc123def456

def _load_folder_ids():
    """Load folder IDs from environment variables with fallback to defaults."""
    defaults = {
        'life_with_ai': '1duf6BRY-tqyWzP3gH1clfaM5B-Qqh0r5',
        'inbox': '1KzQODiGWI0DTsV6dEJHOGvniKx7nR8Ss',
        'in_development': '1fKYixOC9aDcm-XHAIHhfGj3rKlRg5b-i',
        'ready_for_review': '1Zy2ocnE4EOwpeuvu8RFrNS_WophR4ebB',
        'published': '1buuMweoHEdo17_YdR9qgXw42dpNhgyR3',
        'voice_library': '1zzD3HBIrjOAQ-L5a1WDsewroKaOzpie_',
        'agent_prompts': '1u81lD6187CGxztciR_clM4rH-9TpM1TT',
        'reference_docs': '1SKO7KfS3UUuwTiHQ1WYS0eBfVryR1Wxr',
        'workflows': '1ZGHfjdxIJPxOe_W_8iNskV9U5UkT0uAc',
        'images': '1y7yCgVcFsgWSTk4ZreuMBcgfJ91il6MO',
    }

    folder_ids = {}
    for key, default_value in defaults.items():
        env_key = f"DRIVE_FOLDER_{key.upper()}"
        folder_ids[key] = os.getenv(env_key, default_value)

    return folder_ids

FOLDER_IDS = _load_folder_ids()

# Template Document IDs - Create these manually in Google Drive
# The service account will COPY these templates to create new documents
# To set up: Create a blank Google Doc called "_BrainTrust_Template" in Life with AI folder
# and share it with your service account email
TEMPLATE_IDS = {
    'default': None,  # Set this to your template document ID (or leave None for auto-discovery)
    'article': None,  # Optional: specific template for articles
    'character': None,  # Optional: specific template for character profiles
}

# Template name pattern for auto-discovery
TEMPLATE_NAME_PATTERN = "_BrainTrust_Template"

# Cache for discovered template ID
_discovered_template_id = None


def discover_template_id() -> Optional[str]:
    """
    Auto-discover the template document by searching for files matching the template name pattern.
    Results are cached to avoid repeated API calls.
    """
    global _discovered_template_id

    # Return cached value if already discovered
    if _discovered_template_id is not None:
        return _discovered_template_id

    # Check if manually configured first
    if TEMPLATE_IDS.get('default'):
        _discovered_template_id = TEMPLATE_IDS['default']
        return _discovered_template_id

    try:
        creds = DriveAuth.authenticate()
        drive_service = build('drive', 'v3', credentials=creds)

        # Search for template document
        query = f"name contains '{TEMPLATE_NAME_PATTERN}' and mimeType = 'application/vnd.google-apps.document' and trashed = false"

        results = drive_service.files().list(
            q=query,
            pageSize=5,
            fields="files(id, name)"
        ).execute()

        files = results.get('files', [])

        if files:
            # Use the first matching template
            _discovered_template_id = files[0]['id']
            print(f"[Drive] Auto-discovered template: {files[0]['name']} (ID: {_discovered_template_id})")
            return _discovered_template_id

    except Exception as e:
        print(f"[Drive] Template auto-discovery failed: {e}")

    return None

def resolve_folder(folder_name: str) -> Optional[str]:
    """
    Resolve a folder name to its ID using semantic matching.
    Supports partial matches and common variations.
    """
    folder_name = folder_name.lower().strip()

    # Direct match
    if folder_name in FOLDER_IDS:
        return FOLDER_IDS[folder_name]

    # Semantic aliases
    aliases = {
        '01_inbox': 'inbox',
        '02_in_development': 'in_development',
        '03_ready_for_review': 'ready_for_review',
        '04_published': 'published',
        '05_voice_library': 'voice_library',
        'development': 'in_development',
        'dev': 'in_development',
        'review': 'ready_for_review',
        'for_review': 'ready_for_review',
        'voices': 'voice_library',
        'voice': 'voice_library',
        'prompts': 'agent_prompts',
        'reference': 'reference_docs',
        'refs': 'reference_docs',
        'root': 'life_with_ai',
        'main': 'life_with_ai',
    }

    if folder_name in aliases:
        return FOLDER_IDS.get(aliases[folder_name])

    # Partial match
    for key, folder_id in FOLDER_IDS.items():
        if folder_name in key or key in folder_name:
            return folder_id

    return None

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
    folder_id: str = Field(
        description="Folder to list files from. Can be a folder name (e.g., 'reference_docs', 'in_development', 'inbox') or a folder ID. Use 'root' or 'all' to list all accessible files."
    )

class DriveListTool(BaseTool):
    name: str = "Google Drive Lister"
    description: str = """Lists files and folders in a specific Google Drive folder.

    Folder names supported: inbox, in_development, ready_for_review, published,
    voice_library, reference_docs, agent_prompts, workflows, images, life_with_ai

    Use folder_id='root' or 'all' to see all accessible files."""
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
                # Try to resolve folder name to ID first
                resolved_id = resolve_folder(folder_id)
                actual_folder_id = resolved_id if resolved_id else folder_id

                # List files in specific folder
                query = f"'{actual_folder_id}' in parents and trashed = false"
            
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
    folder: str = Field(
        default="in_development",
        description="Target folder name (e.g., 'inbox', 'in_development', 'ready_for_review', 'published')"
    )
    template_id: Optional[str] = Field(
        default=None,
        description="Optional: ID of a template document to copy. If not provided, uses default template."
    )

class DriveWriteTool(BaseTool):
    name: str = "Google Doc Creator"
    description: str = """Creates a new Google Doc by copying a template and populating it with content.

    IMPORTANT: This tool requires a template document to exist in Google Drive.
    The service account copies the template (which creates a file owned by the original
    owner, bypassing quota limits) and then edits the copy with your content.

    Available folders: inbox, in_development, ready_for_review, published, voice_library,
    reference_docs, agent_prompts, workflows

    Setup: Create a blank Google Doc called "_Template_Document" in your Drive and
    set the TEMPLATE_IDS['default'] in drive_tool.py to its ID."""
    args_schema: Type[BaseModel] = DriveWriteInput

    def _run(self, title: str, content: str, folder: str = "in_development", template_id: Optional[str] = None) -> str:
        try:
            creds = DriveAuth.authenticate()
            docs_service = build('docs', 'v1', credentials=creds)
            drive_service = build('drive', 'v3', credentials=creds)

            # Resolve target folder
            target_folder_id = resolve_folder(folder)
            if not target_folder_id:
                return f"Error: Could not resolve folder '{folder}'. Available: {list(FOLDER_IDS.keys())}"

            # Get template ID (try explicit, then configured, then auto-discover)
            tpl_id = template_id or TEMPLATE_IDS.get('default') or discover_template_id()

            if tpl_id:
                # === COPY TEMPLATE APPROACH (Recommended) ===
                # This bypasses service account quota limits because the copy
                # inherits ownership from the template's owner
                copy_metadata = {
                    'name': title,
                    'parents': [target_folder_id]
                }

                copied_file = drive_service.files().copy(
                    fileId=tpl_id,
                    body=copy_metadata,
                    fields='id'
                ).execute()

                doc_id = copied_file.get('id')

                # Clear template content and insert new content
                # First, get the document to find content length
                doc = docs_service.documents().get(documentId=doc_id).execute()
                doc_content = doc.get('body', {}).get('content', [])

                # Find end index (last content element)
                end_index = 1
                for element in doc_content:
                    if 'endIndex' in element:
                        end_index = max(end_index, element['endIndex'])

                requests = []

                # Delete existing content if any (preserve first character position)
                if end_index > 2:
                    requests.append({
                        'deleteContentRange': {
                            'range': {
                                'startIndex': 1,
                                'endIndex': end_index - 1
                            }
                        }
                    })

                # Insert new content
                if content:
                    requests.append({
                        'insertText': {
                            'location': {'index': 1},
                            'text': content
                        }
                    })

                if requests:
                    docs_service.documents().batchUpdate(
                        documentId=doc_id,
                        body={'requests': requests}
                    ).execute()

                folder_display = folder.replace('_', ' ').title()
                return f"Successfully created document '{title}' in '{folder_display}' (ID: {doc_id})\nView: https://docs.google.com/document/d/{doc_id}/edit"

            else:
                # === FALLBACK: Direct creation (may fail due to quota) ===
                from googleapiclient.http import MediaIoBaseUpload
                import io

                file_metadata = {
                    'name': title,
                    'mimeType': 'application/vnd.google-apps.document',
                    'parents': [target_folder_id]
                }

                # Try upload bypass method
                media = MediaIoBaseUpload(io.BytesIO(b' '), mimetype='text/plain', resumable=True)

                doc = drive_service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id'
                ).execute()

                doc_id = doc.get('id')

                if content:
                    requests = [{
                        'insertText': {
                            'location': {'index': 1},
                            'text': content
                        }
                    }]
                    docs_service.documents().batchUpdate(
                        documentId=doc_id,
                        body={'requests': requests}
                    ).execute()

                folder_display = folder.replace('_', ' ').title()
                return f"Successfully created document '{title}' in '{folder_display}' (ID: {doc_id})\nNote: Created without template - if this fails with quota errors, please set up a template document.\nView: https://docs.google.com/document/d/{doc_id}/edit"

        except Exception as e:
            error_msg = str(e)
            if 'storageQuotaExceeded' in error_msg or 'quotaExceeded' in error_msg:
                return (
                    f"Error: Storage quota exceeded. Service accounts cannot create new files without a template.\n"
                    f"SOLUTION: Create a blank Google Doc called '_Template_Document' in your Drive, "
                    f"share it with the service account, and set TEMPLATE_IDS['default'] in drive_tool.py "
                    f"to its document ID."
                )
            return f"Error creating doc: {error_msg}"


class DriveMoveInput(BaseModel):
    file_id: str = Field(description="The ID of the file to move")
    destination_folder: str = Field(
        description="Destination folder name (e.g., 'inbox', 'in_development', 'ready_for_review', 'published')"
    )

class DriveMoveTool(BaseTool):
    name: str = "Google Drive File Mover"
    description: str = """Moves a file to a different folder in the editorial pipeline.

    Editorial Pipeline Stages:
    - inbox: New incoming content
    - in_development: Content being actively worked on
    - ready_for_review: Content awaiting editorial review
    - published: Finalized, published content

    Other folders: voice_library, reference_docs, agent_prompts, workflows, images

    Example: Move a draft from 'in_development' to 'ready_for_review' when it's ready for editing."""
    args_schema: Type[BaseModel] = DriveMoveInput

    def _run(self, file_id: str, destination_folder: str) -> str:
        try:
            creds = DriveAuth.authenticate()
            drive_service = build('drive', 'v3', credentials=creds)

            # Resolve destination folder
            dest_folder_id = resolve_folder(destination_folder)
            if not dest_folder_id:
                return f"Error: Could not resolve folder '{destination_folder}'. Available: {list(FOLDER_IDS.keys())}"

            # Get current file info (including current parents)
            file_info = drive_service.files().get(
                fileId=file_id,
                fields='id, name, parents'
            ).execute()

            file_name = file_info.get('name', 'Unknown')
            current_parents = file_info.get('parents', [])

            # Move the file (add new parent, remove old parents)
            old_parents = ','.join(current_parents) if current_parents else None

            update_params = {
                'fileId': file_id,
                'addParents': dest_folder_id,
                'fields': 'id, parents'
            }
            if old_parents:
                update_params['removeParents'] = old_parents

            drive_service.files().update(**update_params).execute()

            folder_display = destination_folder.replace('_', ' ').title()
            return f"Successfully moved '{file_name}' to '{folder_display}'"

        except Exception as e:
            return f"Error moving file: {str(e)}"


class DriveFindInput(BaseModel):
    query: str = Field(
        description="Search query - can be a file name, partial name, or content keyword"
    )
    folder: Optional[str] = Field(
        default=None,
        description="Optional: Limit search to a specific folder (e.g., 'reference_docs', 'in_development')"
    )

class DriveFindTool(BaseTool):
    name: str = "Google Drive File Finder"
    description: str = """Searches for files by name or content across Google Drive.

    Useful for finding files when you only know part of the name or are looking
    for files related to a topic.

    Examples:
    - Find character profiles: query="character" or query="Oren"
    - Find articles about a topic: query="AI ethics"
    - Find files in a specific folder: query="draft", folder="in_development"
    """
    args_schema: Type[BaseModel] = DriveFindInput

    def _run(self, query: str, folder: Optional[str] = None) -> str:
        try:
            creds = DriveAuth.authenticate()
            drive_service = build('drive', 'v3', credentials=creds)

            # Build search query
            search_parts = [
                f"name contains '{query}'",
                "trashed = false"
            ]

            # Add folder constraint if specified
            if folder:
                folder_id = resolve_folder(folder)
                if folder_id:
                    search_parts.append(f"'{folder_id}' in parents")
                else:
                    return f"Warning: Could not resolve folder '{folder}'. Searching all folders."

            search_query = " and ".join(search_parts)

            results = drive_service.files().list(
                q=search_query,
                pageSize=20,
                fields="files(id, name, mimeType, parents, modifiedTime)"
            ).execute()

            items = results.get('files', [])

            if not items:
                # Try full-text search as fallback
                fulltext_query = f"fullText contains '{query}' and trashed = false"
                if folder:
                    folder_id = resolve_folder(folder)
                    if folder_id:
                        fulltext_query += f" and '{folder_id}' in parents"

                results = drive_service.files().list(
                    q=fulltext_query,
                    pageSize=20,
                    fields="files(id, name, mimeType, parents, modifiedTime)"
                ).execute()
                items = results.get('files', [])

            if not items:
                return f"No files found matching '{query}'"

            output = f"Found {len(items)} file(s) matching '{query}':\n\n"
            for item in items:
                file_type = "📄" if item['mimeType'] == 'application/vnd.google-apps.document' else "📁" if item['mimeType'] == 'application/vnd.google-apps.folder' else "📎"
                output += f"{file_type} {item['name']}\n"
                output += f"   ID: {item['id']}\n"
                if item.get('modifiedTime'):
                    output += f"   Modified: {item['modifiedTime'][:10]}\n"

            return output

        except Exception as e:
            return f"Error searching files: {str(e)}"


class DriveRenameInput(BaseModel):
    file_id: str = Field(description="The ID of the file to rename")
    new_name: str = Field(description="The new name for the file (without extension)")

class DriveRenameTool(BaseTool):
    name: str = "Google Drive File Renamer"
    description: str = """Renames a file in Google Drive.

    Use this to enforce naming conventions. The file extension is preserved automatically.

    Naming conventions to follow:
    - Character profiles: {Name}_Character_Profile
    - Story beats: {Story_Title}_Beats
    - Drafts: {Story_Title}_Draft_{N}
    - Voice samples: {Character}_Voice_Sample
    """
    args_schema: Type[BaseModel] = DriveRenameInput

    def _run(self, file_id: str, new_name: str) -> str:
        try:
            creds = DriveAuth.authenticate()
            drive_service = build('drive', 'v3', credentials=creds)

            # Get current file info
            file_info = drive_service.files().get(
                fileId=file_id,
                fields='id, name, mimeType'
            ).execute()

            old_name = file_info.get('name', 'Unknown')

            # Update the file name
            drive_service.files().update(
                fileId=file_id,
                body={'name': new_name}
            ).execute()

            return f"Successfully renamed '{old_name}' to '{new_name}'"

        except Exception as e:
            return f"Error renaming file: {str(e)}"


class DriveMetadataInput(BaseModel):
    file_id: str = Field(description="The ID of the file to get metadata for")

class DriveMetadataTool(BaseTool):
    name: str = "Google Drive Metadata Reader"
    description: str = """Gets detailed metadata for a file in Google Drive.

    Returns: name, size, created date, modified date, owner, folder location, and MD5 hash.

    Useful for:
    - Checking when a file was last modified
    - Comparing files for duplicates (via MD5 hash)
    - Understanding file history
    """
    args_schema: Type[BaseModel] = DriveMetadataInput

    def _run(self, file_id: str) -> str:
        try:
            creds = DriveAuth.authenticate()
            drive_service = build('drive', 'v3', credentials=creds)

            file_info = drive_service.files().get(
                fileId=file_id,
                fields='id, name, mimeType, size, createdTime, modifiedTime, owners, parents, md5Checksum, webViewLink'
            ).execute()

            # Build readable output
            output = f"📄 FILE METADATA\n"
            output += f"{'═' * 40}\n\n"
            output += f"Name: {file_info.get('name', 'Unknown')}\n"
            output += f"ID: {file_info.get('id')}\n"
            output += f"Type: {file_info.get('mimeType', 'Unknown')}\n"

            if file_info.get('size'):
                size_kb = int(file_info['size']) / 1024
                output += f"Size: {size_kb:.1f} KB\n"

            if file_info.get('createdTime'):
                output += f"Created: {file_info['createdTime'][:10]}\n"

            if file_info.get('modifiedTime'):
                output += f"Modified: {file_info['modifiedTime'][:10]}\n"

            if file_info.get('owners'):
                owners = [o.get('displayName', o.get('emailAddress', 'Unknown')) for o in file_info['owners']]
                output += f"Owner: {', '.join(owners)}\n"

            if file_info.get('md5Checksum'):
                output += f"MD5 Hash: {file_info['md5Checksum']}\n"

            if file_info.get('webViewLink'):
                output += f"Link: {file_info['webViewLink']}\n"

            # Resolve parent folder name
            if file_info.get('parents'):
                parent_id = file_info['parents'][0]
                # Reverse lookup folder name
                for name, fid in FOLDER_IDS.items():
                    if fid == parent_id:
                        output += f"Folder: {name}\n"
                        break
                else:
                    output += f"Folder ID: {parent_id}\n"

            return output

        except Exception as e:
            return f"Error getting metadata: {str(e)}"


class DriveRecentChangesInput(BaseModel):
    days: int = Field(
        default=7,
        description="Number of days to look back for changes (default: 7)"
    )
    folder: Optional[str] = Field(
        default=None,
        description="Optional: Limit to a specific folder"
    )

class DriveRecentChangesTool(BaseTool):
    name: str = "Google Drive Recent Changes"
    description: str = """Lists files that were modified recently.

    Perfect for session start scans to see what changed since last time.

    Returns files sorted by modification date (newest first).
    """
    args_schema: Type[BaseModel] = DriveRecentChangesInput

    def _run(self, days: int = 7, folder: Optional[str] = None) -> str:
        try:
            from datetime import datetime, timedelta

            creds = DriveAuth.authenticate()
            drive_service = build('drive', 'v3', credentials=creds)

            # Calculate cutoff date
            cutoff = datetime.utcnow() - timedelta(days=days)
            cutoff_str = cutoff.strftime('%Y-%m-%dT%H:%M:%S')

            # Build query
            query_parts = [
                f"modifiedTime > '{cutoff_str}'",
                "trashed = false"
            ]

            if folder:
                folder_id = resolve_folder(folder)
                if folder_id:
                    query_parts.append(f"'{folder_id}' in parents")

            query = " and ".join(query_parts)

            results = drive_service.files().list(
                q=query,
                pageSize=50,
                orderBy='modifiedTime desc',
                fields="files(id, name, mimeType, modifiedTime, parents)"
            ).execute()

            items = results.get('files', [])

            if not items:
                return f"No files modified in the last {days} days."

            output = f"📋 FILES MODIFIED IN LAST {days} DAYS\n"
            output += f"{'═' * 40}\n\n"
            output += f"Found {len(items)} file(s):\n\n"

            for item in items:
                file_type = "📄" if item['mimeType'] == 'application/vnd.google-apps.document' else "📁" if item['mimeType'] == 'application/vnd.google-apps.folder' else "📎"
                mod_date = item.get('modifiedTime', '')[:10] if item.get('modifiedTime') else 'Unknown'

                # Get folder name
                folder_name = "Unknown"
                if item.get('parents'):
                    parent_id = item['parents'][0]
                    for name, fid in FOLDER_IDS.items():
                        if fid == parent_id:
                            folder_name = name
                            break

                output += f"{file_type} {item['name']}\n"
                output += f"   Modified: {mod_date} | Folder: {folder_name}\n"

            return output

        except Exception as e:
            return f"Error getting recent changes: {str(e)}"


class DrivePipelineStatusInput(BaseModel):
    pass  # No inputs needed

class DrivePipelineStatusTool(BaseTool):
    name: str = "Editorial Pipeline Status"
    description: str = """Gets the current status of the editorial pipeline.

    Shows file counts in each stage:
    - Inbox (new/unprocessed)
    - In Development (active work)
    - Ready for Review (awaiting editing)
    - Published (completed)

    Also flags any anomalies like stale files.
    """
    args_schema: Type[BaseModel] = DrivePipelineStatusInput

    def _run(self) -> str:
        try:
            from datetime import datetime, timedelta

            creds = DriveAuth.authenticate()
            drive_service = build('drive', 'v3', credentials=creds)

            pipeline_folders = ['inbox', 'in_development', 'ready_for_review', 'published']
            counts = {}
            stale_files = []
            stale_threshold = datetime.utcnow() - timedelta(days=7)

            for folder_name in pipeline_folders:
                folder_id = FOLDER_IDS.get(folder_name)
                if not folder_id:
                    continue

                results = drive_service.files().list(
                    q=f"'{folder_id}' in parents and trashed = false",
                    pageSize=100,
                    fields="files(id, name, modifiedTime)"
                ).execute()

                files = results.get('files', [])
                counts[folder_name] = len(files)

                # Check for stale files in development
                if folder_name == 'in_development':
                    for f in files:
                        if f.get('modifiedTime'):
                            mod_time = datetime.fromisoformat(f['modifiedTime'].replace('Z', '+00:00'))
                            if mod_time.replace(tzinfo=None) < stale_threshold:
                                days_old = (datetime.utcnow() - mod_time.replace(tzinfo=None)).days
                                stale_files.append((f['name'], days_old))

            # Build output
            output = "📊 PIPELINE STATUS\n"
            output += "═" * 40 + "\n\n"

            output += f"📥 Inbox:            {counts.get('inbox', 0)} items\n"
            output += f"🔧 In Development:   {counts.get('in_development', 0)} items\n"
            output += f"👁️ Ready for Review: {counts.get('ready_for_review', 0)} items\n"
            output += f"✅ Published:        {counts.get('published', 0)} items\n"

            total = sum(counts.values())
            output += f"\n   Total: {total} files in pipeline\n"

            if stale_files:
                output += f"\n⚠️ STALE FILES (>{7} days in Development):\n"
                for name, days in stale_files:
                    output += f"   - {name} ({days} days)\n"

            if counts.get('inbox', 0) > 0:
                output += f"\n📌 Note: {counts['inbox']} items in Inbox awaiting triage\n"

            return output

        except Exception as e:
            return f"Error getting pipeline status: {str(e)}"

