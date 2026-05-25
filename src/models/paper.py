import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, Column, DateTime, Enum, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from src.db.interfaces.postgresql import Base


class ProcessingStatus(str, enum.Enum):
    """Status of PDF processing for uploaded papers."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class UploadedPaper(Base):
    """Model for user-uploaded PDF papers."""

    __tablename__ = "uploaded_papers"

    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False, unique=True)
    file_size_bytes = Column(Integer, nullable=False)
    mime_type = Column(String, default="application/pdf", nullable=False)

    # Processing status
    processing_status = Column(Enum(ProcessingStatus), default=ProcessingStatus.PENDING, nullable=False, index=True)
    error_message = Column(Text, nullable=True)

    # Extracted metadata (populated during processing)
    title = Column(String, nullable=True)
    authors = Column(JSON, nullable=True)  # List of author names
    abstract = Column(Text, nullable=True)

    # Parsed PDF content
    raw_text = Column(Text, nullable=True)
    sections = Column(JSON, nullable=True)
    references = Column(JSON, nullable=True)

    # PDF processing metadata
    parser_used = Column(String, nullable=True)
    parser_metadata = Column(JSON, nullable=True)
    pdf_processed = Column(Boolean, default=False, nullable=False)
    pdf_processing_date = Column(DateTime, nullable=True)

    # Indexing metadata
    indexed_at = Column(DateTime, nullable=True)
    indexed_chunks = Column(Integer, default=0, nullable=False)

    # Timestamps
    upload_date = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
