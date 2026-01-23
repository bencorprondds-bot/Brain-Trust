# Environment Variables

## Backend (.env)

Create `backend/.env` with the following variables:

```bash
# API Keys for LLM providers
GEMINI_API_KEY=your_gemini_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here

# Supabase (for execution logging)
SUPABASE_URL=your_supabase_url_here
SUPABASE_KEY=your_supabase_key_here

# CRITICAL: API Key for gatekeeper authentication
# Generate a strong random key: openssl rand -hex 32
BRAIN_TRUST_API_KEY=your_secure_random_key_here
```

## Frontend (.env.local)

Create `frontend/.env.local` with:

```bash
# Must match the backend BRAIN_TRUST_API_KEY
NEXT_PUBLIC_BRAIN_TRUST_API_KEY=your_secure_random_key_here
```

## Generating a Secure API Key

```bash
# Linux/Mac
openssl rand -hex 32

# Windows (PowerShell)
[Convert]::ToBase64String((1..32 | ForEach-Object { Get-Random -Maximum 256 }))

# Or use any password generator
# Example: https://www.random.org/strings/
```

## Security Notes

> [!CAUTION]
> **Never commit your .env files to git!**
> 
> They are already in `.gitignore`, but double-check before pushing.

> [!WARNING]
> **The API key is required for remote access**
> 
> Without it, anyone who discovers your URL can:
> - Drain your API credits
> - Execute arbitrary scripts from `~/.pai/skills/`
> - Read your execution logs

## Access Patterns

### Local Development (No Internet Exposure)
- API key is still required (good practice)
- Only accessible from `localhost`

### Remote Access (Cloudflare Tunnel, Tailscale, etc.)
- API key is **CRITICAL**
- Protects against unauthorized access
- Include `X-API-Key` header in all requests

### Git-Ops Workflow
```bash
# On your laptop
cd ~/.pai/
git init
git add context/ skills/
git commit -m "Update mission"
git push origin main

# On your server
cd ~/.pai/
git pull origin main
# Brain Trust automatically picks up changes (60s cache)
```
