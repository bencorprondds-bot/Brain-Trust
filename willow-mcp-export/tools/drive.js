/**
 * Google Drive Tools
 *
 * Provides read/write/list access to Google Drive for Claude Desktop
 */

import { google } from 'googleapis';

// Folder IDs for "Life with AI" shared drive
const FOLDER_IDS = {
  inbox: process.env.DRIVE_FOLDER_INBOX,
  in_development: process.env.DRIVE_FOLDER_IN_DEVELOPMENT,
  ready_for_review: process.env.DRIVE_FOLDER_READY_FOR_REVIEW,
  published: process.env.DRIVE_FOLDER_PUBLISHED,
  characters: process.env.DRIVE_FOLDER_CHARACTERS,
  reference_docs: process.env.DRIVE_FOLDER_REFERENCE_DOCS,
  world: process.env.DRIVE_FOLDER_WORLD,
};

// Initialize Google Drive client
let driveClient = null;
let docsClient = null;

async function getClients() {
  if (driveClient && docsClient) {
    return { drive: driveClient, docs: docsClient };
  }

  const credentialsPath = process.env.GOOGLE_CREDENTIALS_PATH;
  if (!credentialsPath) {
    throw new Error('GOOGLE_CREDENTIALS_PATH environment variable not set');
  }

  const auth = new google.auth.GoogleAuth({
    keyFile: credentialsPath,
    scopes: [
      'https://www.googleapis.com/auth/drive',
      'https://www.googleapis.com/auth/documents',
    ],
  });

  driveClient = google.drive({ version: 'v3', auth });
  docsClient = google.docs({ version: 'v1', auth });

  return { drive: driveClient, docs: docsClient };
}

// Tool definitions
export const driveTools = [
  {
    name: 'drive_list_files',
    description:
      'List files in a Google Drive folder. Use this to see what documents exist.',
    inputSchema: {
      type: 'object',
      properties: {
        folder: {
          type: 'string',
          description:
            'Folder name: inbox, in_development, ready_for_review, published, characters, reference_docs, world',
          enum: Object.keys(FOLDER_IDS),
        },
        limit: {
          type: 'number',
          description: 'Maximum number of files to return (default 20)',
          default: 20,
        },
      },
      required: ['folder'],
    },
  },
  {
    name: 'drive_read_file',
    description:
      'Read the contents of a Google Doc. Returns the full text content.',
    inputSchema: {
      type: 'object',
      properties: {
        file_id: {
          type: 'string',
          description: 'The Google Drive file ID',
        },
      },
      required: ['file_id'],
    },
  },
  {
    name: 'drive_write_file',
    description:
      'Create a new Google Doc or update an existing one.',
    inputSchema: {
      type: 'object',
      properties: {
        title: {
          type: 'string',
          description: 'Document title',
        },
        content: {
          type: 'string',
          description: 'Document content (plain text or markdown)',
        },
        folder: {
          type: 'string',
          description: 'Target folder',
          enum: Object.keys(FOLDER_IDS),
          default: 'in_development',
        },
        file_id: {
          type: 'string',
          description:
            'Optional: existing file ID to update instead of creating new',
        },
      },
      required: ['title', 'content'],
    },
  },
  {
    name: 'drive_search',
    description:
      'Search for files by name or content across all folders.',
    inputSchema: {
      type: 'object',
      properties: {
        query: {
          type: 'string',
          description: 'Search query (searches file names and content)',
        },
        limit: {
          type: 'number',
          description: 'Maximum results (default 10)',
          default: 10,
        },
      },
      required: ['query'],
    },
  },
  {
    name: 'drive_move_file',
    description:
      'Move a file from one folder to another (e.g., from in_development to published).',
    inputSchema: {
      type: 'object',
      properties: {
        file_id: {
          type: 'string',
          description: 'The file ID to move',
        },
        to_folder: {
          type: 'string',
          description: 'Destination folder',
          enum: Object.keys(FOLDER_IDS),
        },
      },
      required: ['file_id', 'to_folder'],
    },
  },
];

// Tool handlers
export async function handleDriveTool(name, args) {
  const { drive, docs } = await getClients();

  switch (name) {
    case 'drive_list_files': {
      const folderId = FOLDER_IDS[args.folder];
      if (!folderId) {
        throw new Error(`Unknown folder: ${args.folder}`);
      }

      const response = await drive.files.list({
        q: `'${folderId}' in parents and trashed = false`,
        pageSize: args.limit || 20,
        fields: 'files(id, name, mimeType, modifiedTime, size)',
        orderBy: 'modifiedTime desc',
      });

      const files = response.data.files || [];
      const fileList = files
        .map(
          (f) =>
            `- ${f.name} (ID: ${f.id}, Modified: ${f.modifiedTime})`
        )
        .join('\n');

      return {
        content: [
          {
            type: 'text',
            text:
              files.length > 0
                ? `Files in ${args.folder}:\n${fileList}`
                : `No files found in ${args.folder}`,
          },
        ],
      };
    }

    case 'drive_read_file': {
      // Get file metadata first
      const meta = await drive.files.get({
        fileId: args.file_id,
        fields: 'name, mimeType',
      });

      let content;
      if (meta.data.mimeType === 'application/vnd.google-apps.document') {
        // Google Doc - use Docs API
        const doc = await docs.documents.get({
          documentId: args.file_id,
        });

        // Extract text from document
        content = extractTextFromDoc(doc.data);
      } else {
        // Regular file - download content
        const response = await drive.files.get(
          { fileId: args.file_id, alt: 'media' },
          { responseType: 'text' }
        );
        content = response.data;
      }

      return {
        content: [
          {
            type: 'text',
            text: `# ${meta.data.name}\n\n${content}`,
          },
        ],
      };
    }

    case 'drive_write_file': {
      const folderId = FOLDER_IDS[args.folder || 'in_development'];

      if (args.file_id) {
        // Update existing document
        await docs.documents.batchUpdate({
          documentId: args.file_id,
          requestBody: {
            requests: [
              {
                deleteContentRange: {
                  range: {
                    startIndex: 1,
                    endIndex: 2147483647, // Max int - delete all
                  },
                },
              },
              {
                insertText: {
                  location: { index: 1 },
                  text: args.content,
                },
              },
            ],
          },
        });

        // Optionally update title
        await drive.files.update({
          fileId: args.file_id,
          requestBody: { name: args.title },
        });

        return {
          content: [
            {
              type: 'text',
              text: `Updated document "${args.title}" (ID: ${args.file_id})`,
            },
          ],
        };
      } else {
        // Create new document
        const doc = await docs.documents.create({
          requestBody: { title: args.title },
        });

        const docId = doc.data.documentId;

        // Add content
        if (args.content) {
          await docs.documents.batchUpdate({
            documentId: docId,
            requestBody: {
              requests: [
                {
                  insertText: {
                    location: { index: 1 },
                    text: args.content,
                  },
                },
              ],
            },
          });
        }

        // Move to target folder
        await drive.files.update({
          fileId: docId,
          addParents: folderId,
          fields: 'id, parents',
        });

        return {
          content: [
            {
              type: 'text',
              text: `Created document "${args.title}" in ${args.folder || 'in_development'} (ID: ${docId})`,
            },
          ],
        };
      }
    }

    case 'drive_search': {
      const response = await drive.files.list({
        q: `fullText contains '${args.query}' and trashed = false`,
        pageSize: args.limit || 10,
        fields: 'files(id, name, mimeType, modifiedTime, parents)',
        orderBy: 'modifiedTime desc',
      });

      const files = response.data.files || [];
      const fileList = files
        .map((f) => `- ${f.name} (ID: ${f.id})`)
        .join('\n');

      return {
        content: [
          {
            type: 'text',
            text:
              files.length > 0
                ? `Search results for "${args.query}":\n${fileList}`
                : `No files found matching "${args.query}"`,
          },
        ],
      };
    }

    case 'drive_move_file': {
      const toFolderId = FOLDER_IDS[args.to_folder];
      if (!toFolderId) {
        throw new Error(`Unknown folder: ${args.to_folder}`);
      }

      // Get current parents
      const file = await drive.files.get({
        fileId: args.file_id,
        fields: 'parents, name',
      });

      // Move file
      await drive.files.update({
        fileId: args.file_id,
        addParents: toFolderId,
        removeParents: file.data.parents.join(','),
        fields: 'id, parents',
      });

      return {
        content: [
          {
            type: 'text',
            text: `Moved "${file.data.name}" to ${args.to_folder}`,
          },
        ],
      };
    }

    default:
      throw new Error(`Unknown drive tool: ${name}`);
  }
}

// Helper to extract text from Google Doc structure
function extractTextFromDoc(doc) {
  let text = '';
  const content = doc.body?.content || [];

  for (const element of content) {
    if (element.paragraph) {
      for (const el of element.paragraph.elements || []) {
        if (el.textRun) {
          text += el.textRun.content;
        }
      }
    }
  }

  return text;
}
