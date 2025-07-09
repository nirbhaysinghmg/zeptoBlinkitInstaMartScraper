import os
import logging
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client

logger = logging.getLogger(__name__)

# Attempt to load environment variables using dotenv first
project_root = Path(__file__).parents[2]  # Go up 2 levels from db/client.py to project root
dotenv_path = project_root / '.env'
load_dotenv(dotenv_path=dotenv_path)

# Directly set environment variables from the .env file content
try:
    with open(dotenv_path, 'r') as env_file:
        for line in env_file:
            line = line.strip()
            if line and not line.startswith('#'):
                key, value = line.split('=', 1)
                os.environ[key] = value
                logger.info(f"Manually set environment variable: {key}")
except Exception as e:
    logger.error(f"Error reading .env file: {str(e)}")

# Get Supabase credentials from environment variables
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://wlpjsvsolzziygrblklf.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndscGpzdnNvbHp6aXlncmJsa2xmIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDExMTQ0NjEsImV4cCI6MjA1NjY5MDQ2MX0.wUzxilPYGWEkVowoyMakU8RkRQdRYXXvv_tVUyWaHfY")

# Debug log to confirm the values being used
logger.info(f"Using SUPABASE_URL: {SUPABASE_URL}")
logger.info(f"Using SUPABASE_KEY: {SUPABASE_KEY[:10]}...")

def get_supabase_client() -> Optional[Client]:
    # Log the values being used for initialization
    logger.info(f"Initializing Supabase client with URL: {SUPABASE_URL}")
    logger.info(f"API Key (first 10 chars): {SUPABASE_KEY[:10] if SUPABASE_KEY else 'None'}...")
    
    # Check for missing or placeholder values
    if not SUPABASE_URL or not SUPABASE_KEY or \
       SUPABASE_URL == "your_supabase_url" or SUPABASE_KEY == "your_supabase_anon_key":
        logger.warning(
            "Supabase credentials not found or using placeholder values. "
            "Some functionality that requires database access will be unavailable. "
            "Set SUPABASE_URL and SUPABASE_KEY environment variables for full functionality."
        )
        return None
    
    # Ensure URL is properly formatted
    if not SUPABASE_URL.startswith(('http://', 'https://')):
        modified_url = f"https://{SUPABASE_URL}"
        logger.warning(f"URL does not include protocol, attempting with: {modified_url}")
        try:
            return create_client(modified_url, SUPABASE_KEY)
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client with modified URL: {str(e)}")
            return None
    
    # Standard initialization
    try:
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {str(e)}")
        return None

supabase = get_supabase_client()

__all__ = ["supabase", "get_supabase_client"]
