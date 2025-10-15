"""
Database-related API routes
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from api import crud, schemas

router = APIRouter(prefix="/api", tags=["database"])

# Document endpoints
@router.post("/documents", response_model=schemas.DocumentResponse, status_code=201)
async def create_document(
    document: schemas.DocumentCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new document record"""
    return await crud.create_document(db, document)

@router.get("/documents", response_model=List[schemas.DocumentResponse])
async def get_documents(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get list of documents"""
    documents = await crud.get_documents(db, skip=skip, limit=limit, status=status)
    return documents

@router.get("/documents/{document_id}", response_model=schemas.DocumentResponse)
async def get_document(
    document_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific document"""
    document = await crud.get_document(db, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return document

@router.patch("/documents/{document_id}", response_model=schemas.DocumentResponse)
async def update_document(
    document_id: int,
    document_update: schemas.DocumentUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update a document"""
    document = await crud.update_document(db, document_id, document_update)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return document

@router.delete("/documents/{document_id}", response_model=schemas.MessageResponse)
async def delete_document(
    document_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Delete a document"""
    deleted = await crud.delete_document(db, document_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found")
    return schemas.MessageResponse(message="Document deleted successfully")

# Processing Job endpoints
@router.post("/jobs", response_model=schemas.ProcessingJobResponse, status_code=201)
async def create_job(
    job: schemas.ProcessingJobCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new processing job"""
    return await crud.create_processing_job(db, job)

@router.get("/jobs", response_model=List[schemas.ProcessingJobResponse])
async def get_jobs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[str] = Query(None),
    user_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get list of processing jobs"""
    jobs = await crud.get_processing_jobs(
        db, skip=skip, limit=limit, status=status, user_id=user_id
    )
    return jobs

@router.get("/jobs/{job_id}", response_model=schemas.ProcessingJobResponse)
async def get_job(
    job_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific processing job"""
    job = await crud.get_processing_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@router.patch("/jobs/{job_id}", response_model=schemas.ProcessingJobResponse)
async def update_job(
    job_id: str,
    job_update: schemas.ProcessingJobUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update a processing job"""
    job = await crud.update_processing_job(db, job_id, job_update)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@router.delete("/jobs/{job_id}", response_model=schemas.MessageResponse)
async def delete_job(
    job_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Delete a processing job"""
    deleted = await crud.delete_processing_job(db, job_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Job not found")
    return schemas.MessageResponse(message="Job deleted successfully")

# Health check endpoint
@router.get("/health", response_model=schemas.MessageResponse)
async def health_check(db: AsyncSession = Depends(get_db)):
    """Check database connection health"""
    try:
        # Simple query to check connection
        await db.execute("SELECT 1")
        return schemas.MessageResponse(
            message="Database connection healthy",
            success=True
        )
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Database connection failed: {str(e)}"
        )

