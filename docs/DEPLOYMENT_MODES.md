# Deployment Modes

Brain Trust supports two deployment modes with **different sources of truth**:

## Mode 1: Local Development

**Source of Truth**: `~/.pai/` on your local machine  
**Use Case**: Hacking on your laptop, testing workflows, developing new skills

```bash
# Your ~/.pai/ is the canonical source
cd ~/.pai/
nano context/MISSION.md  # Edit directly
# Changes take effect immediately (60s cache)
```

**Characteristics**:
- ✅ Fast iteration
- ✅ No git required
- ❌ Not accessible when laptop lid is closed
- ❌ No backup/history

---

## Mode 2: Cloud Deployment (Always-On)

**Source of Truth**: Git repository → cloned to container's `~/.pai/`  
**Use Case**: Always-on agents, access from anywhere, production deployment

```bash
# 1. Initialize YOUR context as a versioned repo
cd ~/.pai/
git init
git add context/ skills/
git commit -m "Initial context"
git remote add origin git@github.com:you/my-telos.git
git push -u origin main

# 2. Server clones repo at startup
# In your Dockerfile or startup script:
git clone git@github.com:you/my-telos.git ~/.pai/

# 3. Update workflow
# On laptop:
cd ~/.pai/
nano context/MISSION.md
git commit -am "Updated mission"
git push

# On server (automatic via webhook or cron):
cd ~/.pai/
git pull origin main
# Brain Trust picks up changes (60s cache)
```

**Characteristics**:
- ✅ Always-on (server doesn't sleep)
- ✅ Access from anywhere
- ✅ Version history & rollback
- ✅ Backup via Git
- ⚠️ Requires git push/pull workflow

---

## Comparison

| Aspect | Local Dev | Cloud Deploy |
|--------|-----------|--------------|
| **Source of Truth** | `~/.pai/` filesystem | Git repo |
| **Accessibility** | Only when laptop on | Always (24/7) |
| **Update Method** | Direct file edit | Git push → pull |
| **Backup** | None (manual) | Git history |
| **Use Case** | Development | Production |
| **Complexity** | Simple | Moderate |

---

## Hybrid Workflow (Recommended)

**Develop locally, deploy to cloud**:

```bash
# 1. Develop on laptop (Local Mode)
cd ~/.pai/
nano context/MISSION.md
# Test with local Brain Trust instance

# 2. Commit when satisfied
git add context/MISSION.md
git commit -m "Refined mission statement"
git push

# 3. Server auto-pulls (Cloud Mode)
# Via webhook or cron job every 5 minutes:
cd ~/.pai/ && git pull origin main
```

**Best of both worlds**:
- ✅ Fast local iteration
- ✅ Always-on cloud deployment
- ✅ Git as canonical source for production

---

## Implementation Details

### Local Dev Setup

```bash
mkdir -p ~/.pai/{context,skills,logs}
cp examples/telos_context/* ~/.pai/context/
cp examples/skills/* ~/.pai/skills/
chmod +x ~/.pai/skills/*.py
```

### Cloud Deploy Setup

**Option A: Manual Clone**
```bash
# On server
git clone git@github.com:you/my-telos.git ~/.pai/
cd ~/.pai/
git config pull.rebase false  # Merge strategy
```

**Option B: Dockerfile**
```dockerfile
FROM python:3.11

# Clone TELOS context at build time
ARG GITHUB_TOKEN
RUN git clone https://${GITHUB_TOKEN}@github.com/you/my-telos.git /root/.pai/

# Install Brain Trust
COPY backend /app/backend
WORKDIR /app/backend
RUN pip install -r requirements.txt

# Startup script pulls latest context
COPY startup.sh /startup.sh
RUN chmod +x /startup.sh

CMD ["/startup.sh"]
```

**startup.sh**:
```bash
#!/bin/bash
cd ~/.pai/
git pull origin main
cd /app/backend
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**Option C: Kubernetes Init Container**
```yaml
initContainers:
- name: sync-context
  image: alpine/git
  command:
  - sh
  - -c
  - |
    cd /pai
    if [ -d .git ]; then
      git pull origin main
    else
      git clone https://github.com/you/my-telos.git .
    fi
  volumeMounts:
  - name: pai-volume
    mountPath: /pai
```

---

## Auto-Sync Strategies

### Strategy 1: Cron Job (Simple)

```bash
# On server, add to crontab
*/5 * * * * cd ~/.pai && git pull origin main
```

**Pros**: Simple, no dependencies  
**Cons**: 5-minute delay, no immediate updates

### Strategy 2: Webhook (Recommended)

```python
# Add to backend/app/api/routes.py
@router.post("/webhook/sync-context")
async def sync_context(request: Request):
    """
    GitHub webhook endpoint to sync context on push.
    
    Configure in GitHub:
    Settings → Webhooks → Add webhook
    Payload URL: https://your-domain.com/api/v1/webhook/sync-context
    Secret: Set WEBHOOK_SECRET in .env
    """
    import hmac
    import hashlib
    import subprocess
    
    # Verify webhook signature
    signature = request.headers.get("X-Hub-Signature-256")
    secret = os.getenv("WEBHOOK_SECRET").encode()
    body = await request.body()
    expected = "sha256=" + hmac.new(secret, body, hashlib.sha256).hexdigest()
    
    if not hmac.compare_digest(signature, expected):
        raise HTTPException(status_code=403, detail="Invalid signature")
    
    # Pull latest context
    result = subprocess.run(
        ["git", "pull", "origin", "main"],
        cwd=Path.home() / ".pai",
        capture_output=True,
        text=True
    )
    
    # Invalidate context cache
    from app.core.context_loader import ContextLoader
    ContextLoader().invalidate_cache()
    
    return {"status": "synced", "output": result.stdout}
```

**Pros**: Instant updates, efficient  
**Cons**: Requires webhook setup

### Strategy 3: File Watcher (Advanced)

```python
# Add to backend/app/main.py
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class ContextWatcher(FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path.endswith('.md'):
            # Invalidate cache when TELOS files change
            from app.core.context_loader import ContextLoader
            ContextLoader().invalidate_cache()

# Start watcher on startup
observer = Observer()
observer.schedule(ContextWatcher(), str(Path.home() / ".pai" / "context"), recursive=False)
observer.start()
```

**Pros**: Instant updates, works with any file change  
**Cons**: Requires watchdog library, more complex

---

## The Canonical Source Question

### For Local Dev
**Answer**: `~/.pai/` filesystem is canonical

### For Cloud Deploy
**Answer**: Git repo is canonical, `~/.pai/` is a working copy

### The Key Insight

**Same code, same paths, different deployment context.**

The Brain Trust code doesn't care whether `~/.pai/` is:
- A standalone directory (local dev)
- A git clone (cloud deploy)

It just reads from `~/.pai/context/*.md` and `~/.pai/skills/*`.

---

## Migration Path

### From Local to Cloud

```bash
# 1. Your existing local setup
cd ~/.pai/
# You have: context/, skills/, logs/

# 2. Initialize git
git init
git add context/ skills/
git commit -m "Initial context"

# 3. Push to GitHub (PRIVATE repo!)
git remote add origin git@github.com:you/my-telos.git
git push -u origin main

# 4. Deploy to cloud
# Server clones the repo to its own ~/.pai/
# Now you have two copies:
# - Laptop: ~/.pai/ (local dev)
# - Server: ~/.pai/ (cloud deploy, synced from git)
```

### From Cloud to Local

```bash
# Clone your existing cloud context
git clone git@github.com:you/my-telos.git ~/.pai/

# Now you can develop locally
cd ~/.pai/
nano context/MISSION.md
git commit -am "Updated locally"
git push  # Syncs to cloud
```

---

## Resolving the Contradiction

**The document previously said**: `~/.pai/` is the source of truth  
**The reality is**: It depends on deployment mode

**The fix**: This document now clarifies:
- **Local dev**: `~/.pai/` is canonical
- **Cloud deploy**: Git repo is canonical, `~/.pai/` is a clone

**Both modes use the same code paths**. The difference is operational, not architectural.

---

## Recommendation

**Start with Local Dev, graduate to Cloud Deploy when ready:**

1. **Week 1**: Develop locally, iterate fast
2. **Week 2**: Initialize git, push to GitHub
3. **Week 3**: Deploy to cloud, set up auto-sync
4. **Week 4+**: Hybrid workflow (develop locally, deploy to cloud)

**The progression is natural and doesn't require code changes.**
