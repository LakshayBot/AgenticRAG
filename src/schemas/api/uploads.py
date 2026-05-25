"""API schemas for PDF upload functionality."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    """Response model for PDF upload."""

    upload_id: UUID = Field(..., description="Unique upload identifier")
    filename: str = Field(..., description="Original filename")
    file_size: int = Field(..., description="File size in bytes")
    processing_status: str = Field(..., description="Processing status: pending, processing, completed, failed")
    created_at: datetime = Field(..., description="Upload timestamp")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "upload_id": "550e8400-e29b-41d4-a716-446655440000",
                "filename": "my_paper.pdf",
                "file_size": 1048576,
                "processing_status": "pending",
                "created_at": "2024-01-15T10:30:00Z",
            }
        }


class UploadStatusResponse(BaseModel):
    """Response model for upload status check."""

    upload_id: UUID = Field(..., description="Unique upload identifier")
    filename: str = Field(..., description="Original filename")
    processing_status: str = Field(..., description="Processing status")
    title: Optional[str] = Field(None, description="Extracted document title")
    authors: Optional[List[str]] = Field(None, description="Extracted authors")
    error_message: Optional[str] = Field(None, description="Error message if processing failed")
    processed_at: Optional[datetime] = Field(None, description="Processing completion timestamp")
    indexed_at: Optional[datetime] = Field(None, description="Indexing completion timestamp")
    created_at: datetime = Field(..., description="Upload timestamp")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "upload_id": "550e8400-e29b-41d4-a716-446655440000",
                "filename": "my_paper.pdf",
                "processing_status": "completed",
                "title": "Deep Learning for Computer Vision",
                "authors": ["John Doe", "Jane Smith"],
                "error_message": None,
                "processed_at": "2024-01-15T10:32:00Z",
                "indexed_at": "2024-01-15T10:32:30Z",
                "created_at": "2024-01-15T10:30:00Z",
            }
        }


class ProcessUploadRequest(BaseModel):
    """Request model to trigger processing of uploaded PDF."""

    upload_id: UUID = Field(..., description="Upload ID to process")

    class Config:
        json_schema_extra = {
            "example": {
                "upload_id": "550e8400-e29b-41d4-a716-446655440000",
            }
        }


class ProcessUploadResponse(BaseModel):
    """Response model for upload processing."""

    upload_id: UUID = Field(..., description="Upload ID")
    status: str = Field(..., description="Processing result status")
    chunks_created: int = Field(..., description="Number of chunks created")
    chunks_indexed: int = Field(..., description="Number of chunks indexed")
    metadata: dict = Field(..., description="Extracted metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "upload_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "completed",
                "chunks_created": 42,
                "chunks_indexed": 42,
                "metadata": {
                    "title": "Deep Learning for Computer Vision",
                    "authors": ["John Doe", "Jane Smith"],
                    "section_count": 8,
                },
            }
        }


class UploadListResponse(BaseModel):
    """Response model for listing uploads."""

    total: int = Field(..., description="Total number of uploads")
    uploads: List[UploadStatusResponse] = Field(..., description="List of uploads")
    limit: int = Field(..., description="Number of results returned")
    offset: int = Field(..., description="Offset used for pagination")

    class Config:
        json_schema_extra = {
            "example": {
                "total": 15,
                "uploads": [
                    {
                        "upload_id": "550e8400-e29b-41d4-a716-446655440000",
                        "filename": "paper1.pdf",
                        "processing_status": "completed",
                        "title": "Deep Learning Basics",
                        "authors": ["Alice"],
                        "error_message": None,
                        "processed_at": "2024-01-15T10:32:00Z",
                        "indexed_at": "2024-01-15T10:32:30Z",
                        "created_at": "2024-01-15T10:30:00Z",
                    }
                ],
                "limit": 10,
                "offset": 0,
            }
        }


class UploadStatsResponse(BaseModel):
    """Response model for upload statistics."""

    total_uploads: int = Field(..., description="Total number of uploads")
    pending: int = Field(..., description="Number of pending uploads")
    processing: int = Field(..., description="Number of processing uploads")
    completed: int = Field(..., description="Number of completed uploads")
    failed: int = Field(..., description="Number of failed uploads")

    class Config:
        json_schema_extra = {
            "example": {
                "total_uploads": 25,
                "pending": 3,
                "processing": 2,
                "completed": 18,
                "failed": 2,
            }
        }
