import os
from supabase import create_client, Client

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

def get_supabase_client() -> Client:
    """Initialize and return Supabase client."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("SUPABASE_URL and SUPABASE_KEY environment variables must be set")
    return create_client(SUPABASE_URL, SUPABASE_KEY)

def init_supabase_tables():
    """Initialize Supabase tables if they don't exist."""
    client = get_supabase_client()
    
    try:
        client.table("users").select("*").limit(1).execute()
        return True
    except Exception as e:
        print(f"Supabase tables not initialized: {e}")
        return False
