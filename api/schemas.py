"""
Pydantic schemas for request/response validation
"""
from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, Field

# Document Schemas
class DocumentBase(BaseModel):
    filename: str
    file_type: str
    task_type: str
    content: Optional[str] = None
    metadata: Optional[dict] = None  # API uses 'metadata', mapped to 'doc_metadata' in DB

class DocumentCreate(DocumentBase):
    pass

class DocumentUpdate(BaseModel):
    filename: Optional[str] = None
    content: Optional[str] = None
    metadata: Optional[dict] = None  # API uses 'metadata', mapped to 'doc_metadata' in DB
    status: Optional[str] = None
    error_message: Optional[str] = None

class DocumentResponse(DocumentBase):
    id: int
    output_path: Optional[str] = None
    status: str
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# User Schemas
class UserBase(BaseModel):
    username: str
    email: str  # Simplified: using str instead of EmailStr to avoid extra dependency
    full_name: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    email: Optional[str] = None  # Simplified: using str instead of EmailStr
    full_name: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None

class UserResponse(UserBase):
    id: int
    is_active: bool
    is_superuser: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Processing Job Schemas
class ProcessingJobBase(BaseModel):
    job_type: str
    input_file: str

class ProcessingJobCreate(ProcessingJobBase):
    user_id: Optional[int] = None

class ProcessingJobUpdate(BaseModel):
    status: Optional[str] = None
    progress: Optional[float] = None
    output_files: Optional[List[str]] = None
    result_data: Optional[dict] = None
    error_message: Optional[str] = None

class ProcessingJobResponse(ProcessingJobBase):
    id: int
    job_id: str
    user_id: Optional[int] = None
    output_files: Optional[List[str]] = None
    status: str
    progress: float
    result_data: Optional[dict] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Generic Response Schemas
class MessageResponse(BaseModel):
    message: str
    success: bool = True

class ListResponse(BaseModel):
    items: List[Any]
    total: int
    page: int = 1
    page_size: int = 10

