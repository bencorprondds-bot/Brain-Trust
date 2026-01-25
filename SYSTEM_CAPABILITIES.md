# SYSTEM CAPABILITIES & INTEGRATIONS

> [!IMPORTANT]
> **PROTOCOL: START OF SESSION**
> AI Agents MUST read this file at the beginning of every session to understand current capabilities.
>
> **PROTOCOL: END OF SESSION**
> AI Agents MUST update this file before the final commit/push if any new capabilities or integrations were added.

---

## 🔍 Purpose
This file is the **SOURCE OF TRUTH** for what the Brain Trust system can actually do. It prevents re-implementation of existing features and ensures all agents are aware of the available toolset.

## ✅ Verified Integrations

### 1. Google Drive (Librarian Agent)
The system has full read/write access to the "Life with AI" Google Drive.
- **Status**: Operational
- **Key Capabilities**:
  - List folders and files (`explore_drive.py`)
  - Move files to organize them (`organize_drive.py`)
  - Folder ID mapping for: `Inbox`, `Characters`, `World`, `Story_Drafts`
- **Primary Agent**: The Librarian

### 2. TELOS Context System
The system loads personal user context from `~/.pai/context/`.
- **Status**: Operational
- **Files Loaded**: `MISSION.md`, `GOALS.md`, `BELIEFS.md`, `IDENTITY.md`

### 3. Script Execution (Skills)
The system can execute custom Python scripts located in `~/.pai/skills/`.
- **Status**: Operational (Protected against `WinError 193`)
- **Verified Skills**: `project_status.py`, `echo_test.py`

### 4. Memory (Dual Logging)
All workflow executions are logged to both **Supabase** and **Local Files** (`~/.pai/logs/`).

---

## 🛠️ Tool Registry

| Tool Name | Type | Location | Description |
|-----------|------|----------|-------------|
| `script_execution_tool` | Core | `backend/app/tools/` | Runs `~/.pai/skills/*.py` |
| `organize_drive` | Skill | `~/.pai/skills/organize_drive.py` | Drive cleanup & organization |
| `explore_drive` | Skill | `~/.pai/skills/explore_drive.py` | List folder contents |
| `story_writer` | Skill | `~/.pai/skills/story_writer.py` | Read Google Docs text (Write disabled) |
| `style_checker` | Skill | `~/.pai/skills/style_checker.py` | Analyze doc against Style Guide |

---

## ⚠️ Known Limitations
1. **Docs API Unavailable**: The Service Account cannot create or edit Google Docs (403 Forbidden).
2. **Editorial Strategy**: Agents should **READ** content from Drive, perform analysis/drafting locally, and provide the result as text output for the user to copy-paste. **Do not attempt to write directly to Docs.**
