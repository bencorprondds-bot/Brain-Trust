"""
API client utilities for the Legion CLI.
"""

import os
import requests
from typing import Dict, Any, Optional


class APIClient:
    """Simple API client for the Brain Trust backend."""

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        api_key: Optional[str] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or os.getenv("BRAIN_TRUST_API_KEY", "")
        self.session = requests.Session()
        self.session.headers["X-API-Key"] = self.api_key

    def get(self, endpoint: str, **params) -> Dict[str, Any]:
        """Make a GET request."""
        url = f"{self.base_url}{endpoint}"
        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def post(self, endpoint: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Make a POST request."""
        url = f"{self.base_url}{endpoint}"
        response = self.session.post(url, json=data)
        response.raise_for_status()
        return response.json()

    # Convenience methods

    def intent(self, message: str, auto_execute: bool = False) -> Dict[str, Any]:
        """Send intent to Willow."""
        return self.post("/api/v2/intent", {
            "message": message,
            "auto_execute": auto_execute,
        })

    def approve(self, plan_id: str) -> Dict[str, Any]:
        """Approve a plan."""
        return self.post("/api/v2/intent/approve", {
            "plan_id": plan_id,
            "action": "approve",
        })

    def capabilities(self) -> Dict[str, Any]:
        """Get capabilities."""
        return self.get("/api/v2/capabilities")

    def status(self) -> Dict[str, Any]:
        """Get Legion status."""
        return self.get("/api/v2/status")

    def run_evals(self, model: str, category: str = None) -> Dict[str, Any]:
        """Run evaluations."""
        data = {"model": model}
        if category:
            data["categories"] = [category]
        return self.post("/api/v1/evals/run", data)


_client: Optional[APIClient] = None


def get_api_client() -> APIClient:
    """Get the singleton API client."""
    global _client
    if _client is None:
        _client = APIClient()
    return _client
