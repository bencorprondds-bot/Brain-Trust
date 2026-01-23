"""
API Key Authentication Middleware
Protects the single-user API from unauthorized access when exposed to the internet.
"""

import os
from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader

# API Key header configuration
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def verify_api_key(api_key: str = Security(api_key_header)):
    """
    Verify API key for gatekeeper authentication.
    
    This is a SINGLE-USER system, but it needs protection when exposed
    to the internet (via Cloudflare Tunnel, Tailscale, or cloud hosting).
    
    Without this, anyone who discovers your URL can:
    - Drain your API credits
    - Execute arbitrary scripts from ~/.pai/skills/
    - Read your execution logs
    
    Args:
        api_key: API key from X-API-Key header
    
    Raises:
        HTTPException: If API key is missing or invalid
    
    Returns:
        str: The validated API key
    """
    expected_key = os.getenv("BRAIN_TRUST_API_KEY")
    
    if not expected_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="BRAIN_TRUST_API_KEY not configured. Set it in your .env file."
        )
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Include X-API-Key header in your request."
        )
    
    if api_key != expected_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key."
        )
    
    return api_key
