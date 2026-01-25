# Brain Trust v2.5 - Personal AI Empowerment Tool

**A context-aware, multi-agent orchestration platform for YOUR personal use.**

## Philosophy

Brain Trust is a **personal empowerment tool**, not a SaaS product. It's designed for:
- ✅ **Single-user**: One person, one `~/.pai/` directory
- ✅ **Self-sovereign**: Your data stays on your machine
- ✅ **Forkable**: Clone it, customize it, make it yours
- ✅ **Shareable**: Share your fork with others to empower them

This is YOUR AI assistant that knows YOUR mission, uses YOUR tools, and remembers YOUR work.

## 🚨 System Capabilities (Read First)
> [!IMPORTANT]
> **AI Agents:** Before starting any session, you **MUST** read [SYSTEM_CAPABILITIES.md](SYSTEM_CAPABILITIES.md) to understand verified integrations and available tools.
> **Human User:** Update that file when adding new features.

## Quick Start

### 1. Set Up Your Personal Context

```bash
# Create your ~/.pai/ directory
mkdir -p ~/.pai/context
mkdir -p ~/.pai/skills
mkdir -p ~/.pai/logs

# Copy example files
cp examples/telos_context/* ~/.pai/context/
cp examples/skills/* ~/.pai/skills/

# Make scripts executable
chmod +x ~/.pai/skills/*.py

# Customize YOUR context
nano ~/.pai/context/MISSION.md  # Define YOUR mission
nano ~/.pai/context/GOALS.md    # Set YOUR goals
nano ~/.pai/context/BELIEFS.md  # State YOUR values
```

### 2. Install & Run

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

### 3. Use It

1. Open http://localhost:3000
2. Design a workflow with agent nodes
3. Click "RUN WORKFLOW"
4. Agents execute with YOUR context from `~/.pai/`
5. Check `~/.pai/logs/` for human-readable execution logs

## What Makes This Personal?

### Your Context (TELOS Layer)

Every agent you create automatically receives YOUR context:

```markdown
# ~/.pai/context/MISSION.md
I am building an AI-powered platform to automate my research workflow...

# ~/.pai/context/BELIEFS.md
- Privacy: My data stays local
- Transparency: All AI actions must be logged
- Cost-consciousness: Respect my API budget
```

When an agent runs, it sees:
```
# USER CONTEXT (TELOS LAYER)

## Mission
I am building an AI-powered platform to automate my research workflow...

## Core Beliefs & Constraints
- Privacy: My data stays local...

---

# AGENT INSTRUCTIONS
<your agent's specific task>
```

### Your Tools (Script Skills)

Drop a Python/Bash script in `~/.pai/skills/` and it becomes a tool:

```python
#!/usr/bin/env python3
# NAME: my_custom_tool
# DESCRIPTION: Does something specific to my workflow
# PARAM: input (str) - What to process

import sys
# Your custom logic here
```

No server restart needed. The agent finds it automatically.

### Your Memory (Dual Logs)

Every execution is logged in TWO places:
1. **Supabase** (structured, queryable)
2. **`~/.pai/logs/YYYY-MM-DD.md`** (human-readable, git-friendly)

You can read your logs like a journal:
```markdown
# Execution Log - 2026-01-23

## [13:02:15] Workflow Execution
- **Agents**: 3
- **Duration**: 45.2s
- **Status**: Success

### Summary
Research completed successfully...
```

## Architecture

```
┌─────────────────────────────────────┐
│    React Flow Frontend (Browser)    │
└────────────────┬────────────────────┘
                 │ HTTP + WebSocket
┌────────────────▼────────────────────┐
│         FastAPI Backend              │
│  ┌──────────────────────────────┐   │
│  │  Context Bridge (TELOS)      │   │
│  │  Loads ~/.pai/context/*.md   │   │
│  └──────────────────────────────┘   │
│  ┌──────────────────────────────┐   │
│  │  Skill Bridge (Scripts)      │   │
│  │  Scans ~/.pai/skills/        │   │
│  └──────────────────────────────┘   │
│  ┌──────────────────────────────┐   │
│  │  Memory Bridge (Journaling)  │   │
│  │  Writes ~/.pai/logs/*.md     │   │
│  └──────────────────────────────┘   │
└─────────────────────────────────────┘
         │                    │
         ▼                    ▼
   ┌──────────┐        ┌──────────┐
   │ Supabase │        │ ~/.pai/  │
   │    DB    │        │  logs/   │
   └──────────┘        └──────────┘
```

## File Structure

```
~/.pai/                          # YOUR personal AI directory
├── context/                     # YOUR context (TELOS)
│   ├── MISSION.md              # YOUR mission
│   ├── GOALS.md                # YOUR goals
│   ├── BELIEFS.md              # YOUR values
│   └── IDENTITY.md             # YOUR profile
├── skills/                      # YOUR custom tools
│   ├── web_search.py
│   ├── file_analyzer.py
│   └── <your_custom_scripts>
└── logs/                        # YOUR execution history
    ├── 2026-01-23.md
    └── 2026-01-24.md

Brain Trust/                     # The application (git repo)
├── backend/
│   ├── app/
│   │   ├── core/
│   │   │   ├── context_loader.py    # Loads YOUR context
│   │   │   ├── journaling.py        # Logs YOUR executions
│   │   │   └── workflow_parser.py
│   │   ├── tools/
│   │   │   └── script_execution_tool.py  # Runs YOUR scripts
│   │   └── api/
│   │       └── routes.py
│   └── requirements.txt
├── frontend/
└── examples/                    # Templates to get started
    ├── telos_context/
    └── skills/
```

## Sharing & Forking

### To Share This Tool

1. **Fork the repo**: `git clone <your-fork>`
2. **Customize for yourself**: Edit `~/.pai/context/*.md`
3. **Add your tools**: Drop scripts in `~/.pai/skills/`
4. **Share your fork**: Others can clone and customize

### What NOT to Share

- ❌ Your `~/.pai/` directory (personal data)
- ❌ Your `.env` file (API keys)
- ❌ Your Supabase credentials

### What TO Share

- ✅ Your fork of the Brain Trust repo
- ✅ Example scripts (in `examples/skills/`)
- ✅ Documentation improvements
- ✅ New features/bridges

## Customization Ideas

### 1. Add Your Own Context Files

```bash
# Add domain-specific context
echo "# Research Methodology\n..." > ~/.pai/context/RESEARCH.md

# Update context_loader.py to load it
```

### 2. Create Workflow-Specific Tools

```bash
# Create a tool for your specific workflow
cat > ~/.pai/skills/my_workflow.py << 'EOF'
#!/usr/bin/env python3
# NAME: my_workflow
# DESCRIPTION: Automates my daily research routine
# PARAM: topic (str) - Research topic

# Your custom automation here
EOF

chmod +x ~/.pai/skills/my_workflow.py
```

### 3. Customize Agent Prompts

Edit `backend/app/core/context_loader.py` to change how context is injected into agent prompts.

## Security: The Gatekeeper Model

### Single-User ≠ No Security

Brain Trust is a **personal tool**, but if you want to access it from anywhere (laptop, phone, coffee shop), you need to expose it to the internet. This requires **gatekeeper authentication**.

### How It Works

```
Internet → Cloudflare Tunnel → API Key Check → Brain Trust
                                      ↓
                                 ✅ Valid key
                                 ❌ Reject (403)
```

### Why API Key?

**Without authentication**, anyone who discovers your URL can:
- ❌ Drain your API credits (expensive LLM calls)
- ❌ Execute arbitrary scripts from `~/.pai/skills/`
- ❌ Read your execution logs

**With API key**:
- ✅ Simple gatekeeper protection
- ✅ No complex user management
- ✅ Sufficient for personal use

### Setup

1. **Generate a strong key**:
   ```bash
   openssl rand -hex 32
   ```

2. **Set in backend** (`backend/.env`):
   ```bash
   BRAIN_TRUST_API_KEY=your_generated_key
   ```

3. **Set in frontend** (`frontend/.env.local`):
   ```bash
   NEXT_PUBLIC_BRAIN_TRUST_API_KEY=your_generated_key
   ```

4. **Test protection**:
   ```bash
   # Should fail (403)
   curl -X POST http://localhost:8000/api/v1/run-workflow \
     -H "Content-Type: application/json" \
     -d '{"nodes":[],"edges":[]}'
   
   # Should succeed
   curl -X POST http://localhost:8000/api/v1/run-workflow \
     -H "Content-Type: application/json" \
     -H "X-API-Key: your_key_here" \
     -d '{"nodes":[],"edges":[]}'
   ```

See [SECURITY.md](docs/SECURITY.md) for full details.

---

## Git-Ops: Version Control Your Context

> [!IMPORTANT]
> **This section is for CLOUD DEPLOYMENT mode**
> 
> For local development, you can edit `~/.pai/` directly without Git.
> Git becomes the source of truth when you want always-on cloud deployment.

### The Problem

You want to access Brain Trust from anywhere, but `~/.pai/` is local to one machine.

### The Solution: Git as Canonical Source

**Initialize YOUR context as a versioned repo**:
```bash
cd ~/.pai/
git init
git add context/ skills/
git commit -m "Initial context"
git remote add origin git@github.com:yourusername/my-telos.git
git push -u origin main
```

### Deployment Modes

| Mode | Source of Truth | Use Case |
|------|----------------|----------|
| **Local Dev** | `~/.pai/` filesystem | Hacking on laptop |
| **Cloud Deploy** | Git repo → `~/.pai/` clone | Always-on agents |

### Cloud Deployment Workflow

**On your laptop** (development):
```bash
cd ~/.pai/
nano context/MISSION.md  # Update your mission
git commit -am "Updated mission for Q1 2026"
git push
```

**On your server** (automatic sync):
```bash
# Option 1: Cron job (every 5 minutes)
*/5 * * * * cd ~/.pai && git pull origin main

# Option 2: GitHub webhook (instant)
# See docs/DEPLOYMENT_MODES.md for webhook setup
```

**On server startup** (Dockerfile):
```dockerfile
# Clone context at container startup
RUN git clone https://github.com/you/my-telos.git /root/.pai/
```

### Benefits

- ✅ **Backup**: Your context is version-controlled
- ✅ **Always-on**: Server stays running even when laptop is closed
- ✅ **Sync**: Update from laptop, server auto-pulls
- ✅ **History**: See how your mission evolved
- ✅ **Rollback**: Revert to previous context

### The Key Insight

**Same code, same paths, different deployment context.**

Brain Trust reads from `~/.pai/context/*.md` whether it's:
- A standalone directory (local dev)
- A git clone (cloud deploy)

The code doesn't care. The difference is operational.

### Security

> [!WARNING]
> **Use a PRIVATE repository**
> 
> Your `~/.pai/` directory contains:
> - Your mission, goals, beliefs (personal)
> - Your custom scripts (potentially sensitive)
> - Your execution logs (may contain private data)
> 
> **Never push to a public repo!**

See [DEPLOYMENT_MODES.md](docs/DEPLOYMENT_MODES.md) for complete deployment guide.

---

## Deployment Options

### Option 1: Cloudflare Tunnel (Recommended)

**Pros**: Free, HTTPS included, no port forwarding  
**Setup**:
```bash
# Install cloudflared
# https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/

cloudflared tunnel create brain-trust
cloudflared tunnel route dns brain-trust brain-trust.yourdomain.com
cloudflared tunnel run brain-trust
```

### Option 2: Tailscale (Most Secure)

**Pros**: Zero-trust network, only accessible from your devices  
**Setup**:
```bash
# Install Tailscale on server and devices
# https://tailscale.com/download

# Access via Tailscale IP (100.x.x.x)
```

### Option 3: VPS + Docker

**Pros**: Full control  
**Setup**:
```bash
# Deploy to DigitalOcean/Linode
# Use Docker Compose
# Configure nginx with SSL (Let's Encrypt)
```

See [SECURITY.md](docs/SECURITY.md) for detailed deployment guides.

---

### By Design
- **Single-user**: Not built for multi-tenancy
- **Local-first**: Requires filesystem access
- **Self-hosted**: Not a cloud SaaS

### Technical
- **File locking**: Concurrent executions may conflict
- **Script security**: Scripts run with full permissions
- **Cache staleness**: Context cached for 60s

## Production Deployment

For personal use, deploy with:
- **Docker Compose** (easiest)
- **Home server** + Tailscale/Cloudflare Tunnel
- **VPS** (DigitalOcean, Linode)

NOT recommended:
- ❌ Vercel/Netlify (no filesystem)
- ❌ AWS Lambda (ephemeral storage)
- ❌ Multi-tenant SaaS (wrong design)

## Philosophy: Why Personal?

AI should empower individuals, not centralize power. Brain Trust is:

- **Transparent**: You can read every log, every prompt, every decision
- **Controllable**: You define the mission, goals, and constraints
- **Extensible**: You add tools without asking permission
- **Portable**: Your `~/.pai/` directory is YOUR data

This is YOUR AI assistant. Make it yours.

## Next Steps

1. **Customize your context**: Edit `~/.pai/context/*.md`
2. **Add your first tool**: Create a script in `~/.pai/skills/`
3. **Run your first workflow**: Design agents that use YOUR context
4. **Read your logs**: Check `~/.pai/logs/` to see what happened
5. **Fork and share**: Help others build their own AI assistants

---

**Remember**: This is a personal empowerment tool. Clone it, customize it, make it yours. Then share your fork to empower others.
