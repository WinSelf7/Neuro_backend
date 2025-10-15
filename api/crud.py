"""
CRUD operations for database models
"""
from typing import List, Optional
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from api import models, schemas
import uuid
from datetime import datetime

# Document CRUD
async def create_document(db: AsyncSession, document: schemas.DocumentCreate) -> models.Document:
    """Create a new document record"""
    doc_data = document.model_dump()
    # Map 'metadata' to 'doc_metadata' for database column
    if 'metadata' in doc_data:
        doc_data['doc_metadata'] = doc_data.pop('metadata')
    
    db_document = models.Document(**doc_data)
    db.add(db_document)
    await db.commit()
    await db.refresh(db_document)
    return db_document

async def get_document(db: AsyncSession, document_id: int) -> Optional[models.Document]:
    """Get a document by ID"""
    result = await db.execute(select(models.Document).filter(models.Document.id == document_id))
    return result.scalar_one_or_none()

async def get_documents(
    db: AsyncSession, 
    skip: int = 0, 
    limit: int = 100,
    status: Optional[str] = None
) -> List[models.Document]:
    """Get list of documents with optional filtering"""
    query = select(models.Document)
    
    if status:
        query = query.filter(models.Document.status == status)
    
    query = query.offset(skip).limit(limit).order_by(models.Document.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()

async def update_document(
    db: AsyncSession, 
    document_id: int, 
    document_update: schemas.DocumentUpdate
) -> Optional[models.Document]:
    """Update a document"""
    update_data = document_update.model_dump(exclude_unset=True)
    # Map 'metadata' to 'doc_metadata' for database column
    if 'metadata' in update_data:
        update_data['doc_metadata'] = update_data.pop('metadata')
    
    if update_data:
        await db.execute(
            update(models.Document)
            .where(models.Document.id == document_id)
            .values(**update_data)
        )
        await db.commit()
    
    return await get_document(db, document_id)

async def delete_document(db: AsyncSession, document_id: int) -> bool:
    """Delete a document"""
    result = await db.execute(
        delete(models.Document).where(models.Document.id == document_id)
    )
    await db.commit()
    return result.rowcount > 0

# Processing Job CRUD
async def create_processing_job(
    db: AsyncSession, 
    job: schemas.ProcessingJobCreate
) -> models.ProcessingJob:
    """Create a new processing job"""
    job_data = job.model_dump()
    job_data['job_id'] = str(uuid.uuid4())
    job_data['status'] = 'pending'
    job_data['progress'] = 0.0
    
    db_job = models.ProcessingJob(**job_data)
    db.add(db_job)
    await db.commit()
    await db.refresh(db_job)
    return db_job

async def get_processing_job(db: AsyncSession, job_id: str) -> Optional[models.ProcessingJob]:
    """Get a processing job by job_id"""
    result = await db.execute(
        select(models.ProcessingJob).filter(models.ProcessingJob.job_id == job_id)
    )
    return result.scalar_one_or_none()

async def get_processing_jobs(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    user_id: Optional[int] = None
) -> List[models.ProcessingJob]:
    """Get list of processing jobs with optional filtering"""
    query = select(models.ProcessingJob)
    
    if status:
        query = query.filter(models.ProcessingJob.status == status)
    if user_id:
        query = query.filter(models.ProcessingJob.user_id == user_id)
    
    query = query.offset(skip).limit(limit).order_by(models.ProcessingJob.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()

async def update_processing_job(
    db: AsyncSession,
    job_id: str,
    job_update: schemas.ProcessingJobUpdate
) -> Optional[models.ProcessingJob]:
    """Update a processing job"""
    update_data = job_update.model_dump(exclude_unset=True)
    
    # Set timestamps based on status changes
    if 'status' in update_data:
        if update_data['status'] == 'processing' and 'started_at' not in update_data:
            update_data['started_at'] = datetime.utcnow()
        elif update_data['status'] in ['completed', 'failed'] and 'completed_at' not in update_data:
            update_data['completed_at'] = datetime.utcnow()
    
    if update_data:
        await db.execute(
            update(models.ProcessingJob)
            .where(models.ProcessingJob.job_id == job_id)
            .values(**update_data)
        )
        await db.commit()
    
    return await get_processing_job(db, job_id)

async def delete_processing_job(db: AsyncSession, job_id: str) -> bool:
    """Delete a processing job"""
    result = await db.execute(
        delete(models.ProcessingJob).where(models.ProcessingJob.job_id == job_id)
    )
    await db.commit()
    return result.rowcount > 0

# User CRUD (basic implementation)
async def create_user(db: AsyncSession, user: schemas.UserCreate) -> models.User:
    """Create a new user"""
    from api.auth import get_password_hash
    
    user_data = user.model_dump()
    password = user_data.pop('password')
    
    # Use the centralized password hashing helper (handles 72-byte truncation)
    hashed_password = get_password_hash(password)
    
    db_user = models.User(**user_data, hashed_password=hashed_password)
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user

async def get_user_by_username(db: AsyncSession, username: str) -> Optional[models.User]:
    """Get a user by username"""
    result = await db.execute(
        select(models.User).filter(models.User.username == username)
    )
    return result.scalar_one_or_none()

async def get_user_by_email(db: AsyncSession, email: str) -> Optional[models.User]:
    """Get a user by email"""
    result = await db.execute(
        select(models.User).filter(models.User.email == email)
    )
    return result.scalar_one_or_none()

async def get_user(db: AsyncSession, user_id: int) -> Optional[models.User]:
    """Get a user by ID"""
    result = await db.execute(select(models.User).filter(models.User.id == user_id))
    return result.scalar_one_or_none()

