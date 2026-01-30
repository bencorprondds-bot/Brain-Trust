# Willow MCP

A Model Context Protocol (MCP) server that transforms Claude Desktop into a persistent creative writing partner. Willow gives Claude access to your Google Drive documents, maintains memory across sessions, and provides multi-perspective editorial feedback.

## Features

- **Google Drive Integration**: Read, write, search, and organize documents in your shared Drive
- **Persistent Memory**: Projects, lessons learned, and creative preferences survive across sessions and machines
- **Editorial Chorus**: Get feedback from multiple AI personas (harsh critic, supportive reader, copy editor, etc.)
- **Cross-Machine Sync**: Work from home or office - your context follows you via cloud storage

## Architecture

```
┌─────────────────────┐         ┌─────────────────────┐
│   Claude Desktop    │  ←───→  │   Willow MCP        │
│   (Opus 4.5)        │  JSON   │   (this server)     │
└─────────────────────┘         └─────────────────────┘
                                         │
                    ┌────────────────────┼────────────────────┐
                    ↓                    ↓                    ↓
           ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
           │ Google Drive │    │   Supabase   │    │ Anthropic API│
           │  (Documents) │    │   (Memory)   │    │   (Chorus)   │
           └──────────────┘    └──────────────┘    └──────────────┘
```

## Prerequisites

- [Claude Desktop](https://claude.ai/download) with Claude Max subscription
- [Node.js](https://nodejs.org/) 18 or higher
- A [Supabase](https://supabase.com/) project (free tier works)
- Google Cloud service account with Drive API access
- Anthropic API key (for chorus features)

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/bencorprondds-bot/Willow-MCP.git
cd Willow-MCP
npm install
```

### 2. Set up Supabase

1. Create a new Supabase project (or use existing)
2. Go to SQL Editor in Supabase dashboard
3. Run the migration script:

```bash
cat migrations/001_memory_schema.sql
# Copy and paste into Supabase SQL Editor, then run
```

4. Get your project URL and service role key from Settings > API

### 3. Configure environment

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-service-role-key

# Google Drive
GOOGLE_CREDENTIALS_PATH=/path/to/service-account.json
DRIVE_FOLDER_INBOX=folder-id
DRIVE_FOLDER_IN_DEVELOPMENT=folder-id
# ... etc

# Anthropic (for chorus)
ANTHROPIC_API_KEY=sk-ant-...
```

### 4. Configure Claude Desktop

Edit your Claude Desktop config file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "willow": {
      "command": "node",
      "args": ["/full/path/to/Willow-MCP/index.js"],
      "env": {
        "SUPABASE_URL": "https://your-project.supabase.co",
        "SUPABASE_KEY": "your-service-role-key",
        "GOOGLE_CREDENTIALS_PATH": "/path/to/credentials.json",
        "DRIVE_FOLDER_INBOX": "folder-id",
        "DRIVE_FOLDER_IN_DEVELOPMENT": "folder-id",
        "DRIVE_FOLDER_READY_FOR_REVIEW": "folder-id",
        "DRIVE_FOLDER_PUBLISHED": "folder-id",
        "DRIVE_FOLDER_CHARACTERS": "folder-id",
        "DRIVE_FOLDER_REFERENCE_DOCS": "folder-id",
        "DRIVE_FOLDER_WORLD": "folder-id",
        "ANTHROPIC_API_KEY": "sk-ant-..."
      }
    }
  }
}
```

### 5. Restart Claude Desktop

Quit and reopen Claude Desktop. You should see "willow" in the MCP servers list.

## Usage

### Starting a Session

Begin each creative session by asking Claude to initialize:

> "Start a new creative session" or "Let's work on the Arun story"

Claude will call `memory_start_session` and retrieve your context.

### Working with Documents

```
"List my documents in the in_development folder"
"Read the latest Arun draft"
"Save this as 'Arun Chapter 2' in in_development"
"Move Arun Chapter 1 to published"
```

### Getting Feedback

```
"Get feedback from the harsh critic on this scene"
"Run a full review with all personas"
"Give me 3 quick takes on whether this opening works"
```

### Recording What You Learn

```
"Record a lesson: present tense works better for Arun's internal monologue"
"Show me my creative preferences"
"What lessons have I learned about pacing?"
```

### Ending a Session

```
"End session - we finished the first draft of chapter 2"
```

Claude will save a summary for next time.

## Available Tools

### Drive Tools

| Tool | Description |
|------|-------------|
| `drive_list_files` | List files in a folder |
| `drive_read_file` | Read document content |
| `drive_write_file` | Create or update a document |
| `drive_search` | Search files by name/content |
| `drive_move_file` | Move file between folders |

### Memory Tools

| Tool | Description |
|------|-------------|
| `memory_start_session` | Initialize session with context |
| `memory_end_session` | Save session summary |
| `memory_get_project` | Get project details |
| `memory_update_project` | Update project status |
| `memory_create_project` | Create new project |
| `memory_list_projects` | List all projects |
| `memory_record_lesson` | Record creative insight |
| `memory_get_lessons` | Retrieve lessons/preferences |
| `memory_record_feedback` | Store feedback received |
| `memory_search` | Search across all memory |

### Chorus Tools

| Tool | Description |
|------|-------------|
| `chorus_get_feedback` | Feedback from one persona |
| `chorus_full_review` | Multi-persona review |
| `chorus_quick_takes` | Multiple quick reactions |
| `chorus_consensus` | Synthesize feedback |
| `chorus_list_personas` | List available personas |

## Editorial Personas

- **harsh_critic**: Identifies weaknesses, plot holes, pacing issues
- **supportive_reader**: Focuses on what's working, emotional resonance
- **copy_editor**: Clarity, redundancy, grammar, tightening prose
- **genre_expert**: Genre conventions, tropes, market positioning
- **character_analyst**: Voice consistency, motivation, authenticity
- **devil_advocate**: Challenges assumptions, alternative interpretations

## Multi-Machine Setup

Both machines need:

1. Clone this repo
2. Run `npm install`
3. Same Claude Desktop config (with correct local paths)
4. Same Supabase credentials (cloud-synced memory)
5. Same Google credentials (or separate service accounts with shared Drive access)

Memory syncs automatically via Supabase. Documents sync via Google Drive.

## Cost Considerations

- **Claude Desktop**: Covered by your Max subscription ($100/mo)
- **Supabase**: Free tier is sufficient for personal use
- **Google Drive**: Free with Google account
- **Anthropic API**: Chorus uses Haiku (~$0.001 per review)

Typical session: ~$0.01-0.05 in API costs for chorus feedback.

## Troubleshooting

### MCP server not appearing in Claude Desktop

1. Check config file path is correct
2. Ensure Node.js path is correct (`which node`)
3. Check Claude Desktop logs for errors
4. Restart Claude Desktop completely

### Google Drive authentication errors

1. Verify service account has Drive API enabled
2. Check credentials file path in config
3. Ensure service account has access to shared drive

### Memory not persisting

1. Check Supabase connection (URL and key)
2. Verify tables were created (run migration)
3. Check Supabase logs for errors

## Development

```bash
# Run in development mode with auto-reload
npm run dev

# Test tools manually
node index.js
```

## License

MIT

## Related

- [Brain Trust](https://github.com/bencorprondds-bot/Brain-Trust) - Multi-agent creative system (automated)
- [Model Context Protocol](https://modelcontextprotocol.io/) - MCP documentation
