"""
Database models.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, JSON, Text, Boolean
from janitor.db.session import Base

class AnalysisRecord(Base):
    """Record of a code analysis job."""
    __tablename__ = "analysis_records"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # metrics
    total_issues = Column(Integer, default=0)
    security_issues_count = Column(Integer, default=0)
    code_smells_count = Column(Integer, default=0)
    
    # JSON data for full report
    issues_data = Column(JSON)  # Stores the full analysis result structure
    
    # Refactoring status
    was_refactored = Column(Boolean, default=False)
    refactored_code = Column(Text, nullable=True)

class HardwareLog(Base):
    """Log of hardware usage stats (optional history)."""
    __tablename__ = "hardware_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    cpu_percent = Column(Integer)
    ram_percent = Column(Integer)
    gpu_memory_used = Column(Integer)
