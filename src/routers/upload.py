"""Router for PDF upload functionality."""

import logging
import shutil
from pathlib import Path
from typing import Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile

from src.config import get_settings
from src.dependencies import SessionDep, UploadProcessorDep
from src.models.paper import ProcessingStatus
from src.repositories.uploaded_paper import UploadedPaperRepository
from src.schemas.api.uploads import (
    ProcessUploadRequest,
    ProcessUploadResponse,
    UploadListResponse,
    UploadResponse,
    UploadStatsResponse,
    UploadStatusResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/upload", tags=["uploads"])


@router.post("/", response_model=UploadResponse, status_code=201)
async def upload_pdf(
    file: UploadFile = File(..., description="PDF file to upload"),
    session: SessionDep = None,
) -> UploadResponse:
    """
    Upload a PDF file for processing.
    
    The file will be saved to disk and a database record will be created.
    Processing must be triggered separately via the /process endpoint.
    """
    settings = get_settings()
    repository = UploadedPaperRepository(session)
    
    # Validate file type
    if file.content_type not in settings.upload.allowed_mime_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed types: {settings.upload.allowed_mime_types}",
        )
    
    # Validate filename extension
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="File must have .pdf extension")
    
    try:
        # Generate unique upload ID - not needed, DB will generate it
        
        # Read file content and check size
        content = await file.read()
        file_size = len(content)
        
        max_size_bytes = settings.upload.max_upload_size_mb * 1024 * 1024
        if file_size > max_size_bytes:
            raise HTTPException(
                status_code=400,
                detail=f"File size ({file_size / 1024 / 1024:.2f} MB) exceeds maximum allowed size ({settings.upload.max_upload_size_mb} MB)",
            )
        
        # Create database record first to get the ID
        upload_record = repository.create(
            filename=file.filename,
            file_path="",  # Will be updated after saving file
            file_size_bytes=file_size,
        )
        
        # Create safe filename using the generated ID
        safe_filename = f"{upload_record.id}_{file.filename}"
        upload_path = settings.upload.upload_directory / safe_filename
        
        # Save file to disk
        upload_path.parent.mkdir(parents=True, exist_ok=True)
        with open(upload_path, "wb") as f:
            f.write(content)
        
        logger.info(f"Saved uploaded file: {upload_path}")
        
        # Update file path in database
        upload_record.file_path = str(upload_path)
        session.commit()
        session.refresh(upload_record)
        
        logger.info(f"Created upload record: {upload_record.id}")
        
        return UploadResponse(
            upload_id=upload_record.id,
            filename=upload_record.filename,
            file_size=upload_record.file_size_bytes,
            processing_status=upload_record.processing_status.value,
            created_at=upload_record.upload_date,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        # Clean up file if it was created
        if 'upload_path' in locals() and upload_path.exists():
            upload_path.unlink()
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.get("/{upload_id}", response_model=UploadStatusResponse)
async def get_upload_status(
    upload_id: UUID,
    session: SessionDep,
) -> UploadStatusResponse:
    """
    Get the status of an uploaded PDF.
    
    Returns processing status, extracted metadata, and any error messages.
    """
    repository = UploadedPaperRepository(session)
    
    upload = repository.get_by_id(upload_id)
    if not upload:
        raise HTTPException(status_code=404, detail=f"Upload {upload_id} not found")
    
    return UploadStatusResponse(
        upload_id=upload.id,
        filename=upload.filename,
        processing_status=upload.processing_status.value,
        title=upload.title,
        authors=upload.authors,
        error_message=upload.error_message,
        processed_at=upload.pdf_processing_date,
        indexed_at=upload.indexed_at,
        created_at=upload.upload_date,
    )


@router.get("s/", response_model=UploadListResponse)
async def list_uploads(
    session: SessionDep,
    limit: int = 10,
    offset: int = 0,
    status: Optional[str] = None,
) -> UploadListResponse:
    """
    List all uploaded PDFs with optional status filtering.
    
    - **limit**: Number of results to return (default: 10, max: 100)
    - **offset**: Number of results to skip for pagination (default: 0)
    - **status**: Filter by processing status (pending, processing, completed, failed)
    """
    repository = UploadedPaperRepository(session)
    
    # Validate limit
    if limit > 100:
        raise HTTPException(status_code=400, detail="Limit cannot exceed 100")
    
    # Validate status if provided
    status_filter = None
    if status:
        try:
            status_filter = ProcessingStatus(status)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status. Must be one of: {[s.value for s in ProcessingStatus]}",
            )
    
    uploads = repository.get_all(limit=limit, offset=offset, status=status_filter)
    total = repository.get_count(status=status_filter)
    
    return UploadListResponse(
        total=total,
        uploads=[
            UploadStatusResponse(
                upload_id=upload.id,
                filename=upload.filename,
                processing_status=upload.processing_status.value,
                title=upload.title,
                authors=upload.authors,
                error_message=upload.error_message,
                processed_at=upload.pdf_processing_date,
                indexed_at=upload.indexed_at,
                created_at=upload.upload_date,
            )
            for upload in uploads
        ],
        limit=limit,
        offset=offset,
    )


@router.post("/{upload_id}/process", response_model=ProcessUploadResponse)
async def process_upload(
    upload_id: UUID,
    session: SessionDep,
    processor: UploadProcessorDep,
) -> ProcessUploadResponse:
    """
    Trigger processing of an uploaded PDF.
    
    This will:
    1. Parse the PDF with Docling
    2. Extract metadata (title, authors)
    3. Chunk the content
    4. Generate embeddings
    5. Index to OpenSearch
    """
    repository = UploadedPaperRepository(session)
    
    # Check if upload exists
    upload = repository.get_by_id(upload_id)
    if not upload:
        raise HTTPException(status_code=404, detail=f"Upload {upload_id} not found")
    
    # Check if already processed
    if upload.processing_status == ProcessingStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Upload already processed")
    
    # Check if currently processing
    if upload.processing_status == ProcessingStatus.PROCESSING:
        raise HTTPException(status_code=400, detail="Upload is currently being processed")
    
    try:
        # Process synchronously (we'll add background processing later)
        result = await processor.process_uploaded_pdf(upload_id, session)
        
        return ProcessUploadResponse(**result)
        
    except Exception as e:
        logger.error(f"Processing failed for upload {upload_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


@router.get("s/stats", response_model=UploadStatsResponse)
async def get_upload_stats(session: SessionDep) -> UploadStatsResponse:
    """
    Get statistics about uploaded PDFs.
    
    Returns counts by processing status.
    """
    repository = UploadedPaperRepository(session)
    
    stats = repository.get_processing_stats()
    
    return UploadStatsResponse(**stats)


@router.delete("/{upload_id}", status_code=204)
async def delete_upload(
    upload_id: UUID,
    session: SessionDep,
    hard_delete: bool = False,
) -> None:
    """
    Delete an uploaded PDF.
    
    - **hard_delete**: If True, permanently deletes the record and file.
                      If False (default), marks as deleted (soft delete).
    """
    repository = UploadedPaperRepository(session)
    
    upload = repository.get_by_id(upload_id)
    if not upload:
        raise HTTPException(status_code=404, detail=f"Upload {upload_id} not found")
    
    try:
        if hard_delete:
            # Delete file from disk
            file_path = Path(upload.file_path)
            if file_path.exists():
                file_path.unlink()
                logger.info(f"Deleted file: {file_path}")
            
            # Delete database record
            repository.hard_delete(upload_id)
            logger.info(f"Hard deleted upload: {upload_id}")
        else:
            # Soft delete
            repository.delete(upload_id)
            logger.info(f"Soft deleted upload: {upload_id}")
        
    except Exception as e:
        logger.error(f"Delete failed for upload {upload_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")
