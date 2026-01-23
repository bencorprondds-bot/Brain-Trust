# Security Architecture

## The Single-User Security Model

Brain Trust is a **single-user personal tool**, but that doesn't mean "no security." Here's why:

### The Threat Model

**Scenario**: You want to access Brain Trust from anywhere (laptop, phone, coffee shop).

**Solution**: Expose the API to the internet via:
- Cloudflare Tunnel
- Tailscale
- ngrok
- Cloud hosting (Railway, Render, VPS)

**Problem**: If you expose an unauthenticated API, **anyone who discovers your URL** can:
1. **Drain your API credits** - Run expensive LLM workflows
2. **Execute arbitrary code** - Scripts in `~/.pai/skills/` run with full permissions
3. **Read your data** - Access execution logs and results

### The Solution: Gatekeeper Authentication

We implement a **simple API key** that acts as a "gatekeeper":

```
┌─────────────────────────────────────────┐
│  Internet (Untrusted)                   │
└────────────────┬────────────────────────┘
                 │
                 ▼
         ┌───────────────┐
         │  API Gateway  │
         │  (Cloudflare) │
         └───────┬───────┘
                 │
                 ▼
         ┌───────────────┐
         │   Gatekeeper  │ ◄── X-API-Key header check
         │  (auth.py)    │
         └───────┬───────┘
                 │ ✅ Valid key
                 ▼
         ┌───────────────┐
         │  Brain Trust  │
         │   (FastAPI)   │
         └───────────────┘
```

## Implementation

### Backend Protection

**File**: `backend/app/core/auth.py`

```python
async def verify_api_key(api_key: str = Security(api_key_header)):
    """
    Verify API key for gatekeeper authentication.
    """
    expected_key = os.getenv("BRAIN_TRUST_API_KEY")
    
    if api_key != expected_key:
        raise HTTPException(status_code=403, detail="Invalid API key")
    
    return api_key
```

**File**: `backend/app/api/routes.py`

```python
@router.post("/run-workflow", dependencies=[Security(verify_api_key)])
async def run_workflow_endpoint(workflow: WorkflowRequest):
    # Protected endpoint - requires valid API key
    ...
```

### Frontend Integration

**File**: `frontend/app/page.tsx`

```typescript
const response = await fetch('http://127.0.0.1:8000/api/v1/run-workflow', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': process.env.NEXT_PUBLIC_BRAIN_TRUST_API_KEY,
  },
  body: JSON.stringify(payload),
});
```

## Why Not More Complex Auth?

### What We DON'T Need

❌ **User accounts** - Single user, no need for user management  
❌ **OAuth/JWT** - Overkill for personal use  
❌ **Session management** - Stateless API is simpler  
❌ **Password hashing** - API key is sufficient  

### What We DO Need

✅ **API key** - Simple, effective gatekeeper  
✅ **HTTPS** - Encrypt traffic (Cloudflare provides this)  
✅ **Rate limiting** - Prevent abuse (future enhancement)  

## Security Checklist

### Before Exposing to Internet

- [ ] Generate strong API key: `openssl rand -hex 32`
- [ ] Set `BRAIN_TRUST_API_KEY` in `backend/.env`
- [ ] Set `NEXT_PUBLIC_BRAIN_TRUST_API_KEY` in `frontend/.env.local`
- [ ] Verify `.env` files are in `.gitignore`
- [ ] Test API key protection (try request without key)
- [ ] Enable HTTPS (Cloudflare Tunnel does this automatically)

### Deployment Options

#### Option 1: Cloudflare Tunnel (Recommended)
```bash
# Install cloudflared
# https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/

# Create tunnel
cloudflared tunnel create brain-trust

# Configure tunnel
cloudflared tunnel route dns brain-trust brain-trust.yourdomain.com

# Run tunnel
cloudflared tunnel run brain-trust
```

**Pros**: Free, HTTPS included, no port forwarding  
**Cons**: Requires Cloudflare account

#### Option 2: Tailscale (Most Secure)
```bash
# Install Tailscale on server and devices
# https://tailscale.com/download

# Access via Tailscale IP (100.x.x.x)
# Only accessible from your Tailscale network
```

**Pros**: Zero-trust network, most secure  
**Cons**: Requires Tailscale on all devices

#### Option 3: VPS + nginx
```bash
# Deploy to DigitalOcean/Linode
# Configure nginx with SSL (Let's Encrypt)
# Firewall rules to allow only HTTPS
```

**Pros**: Full control  
**Cons**: More complex, costs money

## Attack Scenarios & Mitigations

### Scenario 1: Brute Force API Key

**Attack**: Attacker tries to guess your API key

**Mitigation**:
- Use long random key (32 bytes = 256 bits)
- Implement rate limiting (future)
- Monitor failed attempts in logs

### Scenario 2: API Key Leak

**Attack**: You accidentally commit `.env` to GitHub

**Mitigation**:
- `.gitignore` includes `.env`
- Use GitHub secret scanning
- Rotate key immediately if leaked

### Scenario 3: Man-in-the-Middle

**Attack**: Attacker intercepts API key in transit

**Mitigation**:
- Always use HTTPS (Cloudflare Tunnel provides this)
- Never send API key over HTTP

### Scenario 4: Malicious Script Execution

**Attack**: Attacker uploads malicious script to `~/.pai/skills/`

**Mitigation**:
- API key prevents unauthorized access
- Only YOU can add scripts (filesystem access required)
- Future: Sandboxing (Docker, gVisor)

## Future Enhancements

### Short-term
- [ ] Rate limiting (10 requests/minute)
- [ ] Request logging with IP addresses
- [ ] Automatic key rotation

### Long-term
- [ ] Script sandboxing (Docker containers)
- [ ] Cost budgets per execution
- [ ] Webhook notifications for suspicious activity

## Philosophy

**Security is about trade-offs.**

For a **personal tool**:
- ✅ Simple API key is sufficient
- ✅ HTTPS prevents eavesdropping
- ✅ Single-user = no complex auth needed

For a **SaaS product**:
- ❌ Would need OAuth, user accounts, etc.
- ❌ Would need multi-tenancy isolation
- ❌ Would need compliance (SOC 2, GDPR)

**Brain Trust is personal. Keep it simple, keep it secure.**

## Testing Security

### Test 1: API Key Required
```bash
# Should fail (403 Forbidden)
curl -X POST http://localhost:8000/api/v1/run-workflow \
  -H "Content-Type: application/json" \
  -d '{"nodes":[],"edges":[]}'

# Should succeed
curl -X POST http://localhost:8000/api/v1/run-workflow \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_key_here" \
  -d '{"nodes":[],"edges":[]}'
```

### Test 2: Invalid API Key
```bash
# Should fail (403 Forbidden)
curl -X POST http://localhost:8000/api/v1/run-workflow \
  -H "Content-Type: application/json" \
  -H "X-API-Key: wrong_key" \
  -d '{"nodes":[],"edges":[]}'
```

### Test 3: Frontend Integration
```bash
# Check frontend .env.local
cat frontend/.env.local | grep BRAIN_TRUST_API_KEY

# Should match backend .env
cat backend/.env | grep BRAIN_TRUST_API_KEY
```

## Conclusion

**Single-user ≠ No security**

The API key gatekeeper protects your personal AI assistant when exposed to the internet, without the complexity of multi-user authentication.

**Simple. Secure. Personal.**
