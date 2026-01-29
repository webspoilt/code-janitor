"""
Database configuration and session management.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session, declarative_base
from pathlib import Path

# Base class for models
Base = declarative_base()

def get_db_url():
    """Get database URL from environment or default to local SQLite."""
    # Check for Render or generic DATABASE_URL
    url = os.getenv("DATABASE_URL")
    if url:
        # Fix for some postgres providers using 'postgres://' instead of 'postgresql://'
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        return url
    
    # Default to local SQLite
    # Check if current directory is writable
    try:
        # Try creating a dummy file to test writability
        test_file = Path(".write_test")
        test_file.touch()
        test_file.unlink()
        db_path = Path("janitor.db").absolute()
    except (OSError, PermissionError):
        # Fallback to /tmp which is usually writable in serverless/cloud envs
        db_path = Path("/tmp/janitor.db")
    
    return f"sqlite:///{db_path}"

# Create engine
engine = create_engine(
    get_db_url(),
    connect_args={"check_same_thread": False} if "sqlite" in get_db_url() else {}
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Initialize database tables."""
    # Import models here to ensure they are registered with Base
    from janitor.db.models import AnalysisRecord  # noqa: F401
    Base.metadata.create_all(bind=engine)

def get_db():
    """Dependency for FastAPI to get DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
