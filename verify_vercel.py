
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

print("Starting Vercel Simulation...")

# Mock environment variables
os.environ["JANITOR_AI_PROVIDER"] = "groq"
os.environ["GROQ_API_KEY"] = "mock_key"

# Mock filesystem to simulate read-only current directory
def mock_touch(self, *args, **kwargs):
    if ".write_test" in str(self):
        raise PermissionError("Read-only file system")
    return None

def mock_mkdir(self, *args, **kwargs):
    if "static" in str(self) or "templates" in str(self):
        raise PermissionError("Read-only file system (mkdir)")
    return None # Allow others or pass through

print("Simulating Read-only file system...")
with patch('pathlib.Path.touch', new=mock_touch), \
     patch('pathlib.Path.mkdir', new=mock_mkdir):
    try:
        print("Importing app...")
        from app import app
        
        print("Import successful. Checking configuration...")
        from janitor.config import Config
        config = Config.load()
        print(f"Config loaded. AI Provider: {config.ai.provider}")
        
        print("Checking database configuration...")
        from janitor.db.session import get_db_url, init_db
        db_url = get_db_url()
        print(f"DB URL resolved to: {db_url}")
        
        if "/tmp/" not in db_url and "postgres" not in db_url:
            print("WARNING: DB URL does not seem to point to /tmp or postgres in read-only mode!")
        else:
            print("DB URL correctly falls back to /tmp or uses postgres.")
            
        print("Initializing DB...")
        init_db()
        print("DB Initialized successfully.")
        
        print("Vercel Simulation Passed!")
        
    except Exception as e:
        print(f"\nCRASH DETECTED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
