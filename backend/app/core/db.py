import os
from supabase import create_client, Client
from typing import Dict, Any, List, Optional
from datetime import datetime

class SupabaseManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SupabaseManager, cls).__new__(cls)
            cls._instance.client = cls._connect()
        return cls._instance

    @staticmethod
    def _connect() -> Optional[Client]:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        
        if not url or not key:
            print("WARNING: SUPABASE_URL or SUPABASE_KEY not found. Persistence disabled.")
            return None
            
        try:
            return create_client(url, key)
        except Exception as e:
            print(f"ERROR: Failed to connect to Supabase: {e}")
            return None

    def save_execution(self, workflow_data: Dict, result: Any, agents_count: int):
        """Logs a workflow execution to the 'executions' table."""
        if not self.client:
            return
            
        try:
            data = {
                "timestamp": datetime.utcnow().isoformat(),
                "workflow_snapshot": workflow_data,
                "result_summary": str(result),
                "agents_active": agents_count
            }
            # Assuming table 'executions' exists (from schema.sql)
            self.client.table("executions").insert(data).execute()
            print("✅ Execution saved to Supabase.")
        except Exception as e:
            print(f"❌ Failed to save execution log: {e}")

    def get_history(self, limit: int = 10) -> List[Dict]:
        """Fetches recent execution logs."""
        if not self.client:
            return []
            
        try:
            response = self.client.table("executions").select("*").order("timestamp", desc=True).limit(limit).execute()
            return response.data
        except Exception as e:
            print(f"❌ Failed to fetch history: {e}")
            return []
