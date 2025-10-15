"""
Database models for the application
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float, JSON
from sqlalchemy.sql import func
from database import Base

class Document(Base):
    """
    Model for storing parsed documents
    """
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False)  # pdf, jpg, png, etc.
    task_type = Column(String(50), nullable=False)  # parse, text, table, formula, etc.
    content = Column(Text, nullable=True)  # Extracted content
    doc_metadata = Column(JSON, nullable=True)  # Additional metadata (renamed from 'metadata' to avoid SQLAlchemy conflict)
    output_path = Column(String(500), nullable=True)  # Path to output files
    status = Column(String(50), default="pending")  # pending, processing, completed, failed
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def to_dict(self):
        """Convert model to dictionary"""
        return {
            "id": self.id,
            "filename": self.filename,
            "file_type": self.file_type,
            "task_type": self.task_type,
            "content": self.content,
            "metadata": self.doc_metadata,  # Return as 'metadata' for API compatibility
            "output_path": self.output_path,
            "status": self.status,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

class User(Base):
    """
    Model for user management
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def to_dict(self):
        """Convert model to dictionary (excluding password)"""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "full_name": self.full_name,
            "is_active": self.is_active,
            "is_superuser": self.is_superuser,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

class ProcessingJob(Base):
    """
    Model for tracking processing jobs
    """
    __tablename__ = "processing_jobs"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String(100), unique=True, nullable=False, index=True)
    user_id = Column(Integer, nullable=True)  # Optional: link to user
    job_type = Column(String(50), nullable=False)  # parse, ocr, extract, etc.
    input_file = Column(String(500), nullable=False)
    output_files = Column(JSON, nullable=True)  # List of output file paths
    status = Column(String(50), default="pending")  # pending, processing, completed, failed
    progress = Column(Float, default=0.0)  # 0.0 to 100.0
    result_data = Column(JSON, nullable=True)  # Store result data
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def to_dict(self):
        """Convert model to dictionary"""
        return {
            "id": self.id,
            "job_id": self.job_id,
            "user_id": self.user_id,
            "job_type": self.job_type,
            "input_file": self.input_file,
            "output_files": self.output_files,
            "status": self.status,
            "progress": self.progress,
            "result_data": self.result_data,
            "error_message": self.error_message,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

