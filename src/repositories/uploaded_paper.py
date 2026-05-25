"""Repository for managing uploaded PDF papers."""
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session
from src.models.paper import ProcessingStatus, UploadedPaper


class UploadedPaperRepository:
    """Repository for CRUD operations on uploaded papers."""

    def __init__(self, session: Session):
        self.session = session

    def create(
        self,
        filename: str,
        file_path: str,
        file_size_bytes: int,
        mime_type: str = "application/pdf",
    ) -> UploadedPaper:
        """Create a new uploaded paper record.

        :param filename: Original filename
        :param file_path: Path where the file is stored
        :param file_size_bytes: File size in bytes
        :param mime_type: MIME type of the file
        :return: Created UploadedPaper instance
        """
        uploaded_paper = UploadedPaper(
            filename=filename,
            file_path=file_path,
            file_size_bytes=file_size_bytes,
            mime_type=mime_type,
            processing_status=ProcessingStatus.PENDING,
        )
        self.session.add(uploaded_paper)
        self.session.commit()
        self.session.refresh(uploaded_paper)
        return uploaded_paper

    def get_by_id(self, upload_id: UUID) -> Optional[UploadedPaper]:
        """Get uploaded paper by ID.

        :param upload_id: UUID of the uploaded paper
        :return: UploadedPaper instance or None
        """
        stmt = select(UploadedPaper).where(UploadedPaper.id == upload_id)
        return self.session.scalar(stmt)

    def get_by_file_path(self, file_path: str) -> Optional[UploadedPaper]:
        """Get uploaded paper by file path.

        :param file_path: Path to the file
        :return: UploadedPaper instance or None
        """
        stmt = select(UploadedPaper).where(UploadedPaper.file_path == file_path)
        return self.session.scalar(stmt)

    def get_all(
        self,
        limit: int = 100,
        offset: int = 0,
        status: Optional[ProcessingStatus] = None,
    ) -> List[UploadedPaper]:
        """Get all uploaded papers with optional status filter.

        :param limit: Maximum number of results
        :param offset: Number of results to skip
        :param status: Filter by processing status
        :return: List of UploadedPaper instances
        """
        stmt = select(UploadedPaper).order_by(UploadedPaper.upload_date.desc())

        if status:
            stmt = stmt.where(UploadedPaper.processing_status == status)

        stmt = stmt.limit(limit).offset(offset)
        return list(self.session.scalars(stmt))

    def get_count(self, status: Optional[ProcessingStatus] = None) -> int:
        """Get count of uploaded papers with optional status filter.

        :param status: Filter by processing status
        :return: Count of papers
        """
        stmt = select(func.count(UploadedPaper.id))

        if status:
            stmt = stmt.where(UploadedPaper.processing_status == status)

        return self.session.scalar(stmt) or 0

    def get_pending_uploads(self, limit: int = 100) -> List[UploadedPaper]:
        """Get papers with pending processing status.

        :param limit: Maximum number of results
        :return: List of UploadedPaper instances
        """
        return self.get_all(limit=limit, status=ProcessingStatus.PENDING)

    def update_status(
        self,
        upload_id: UUID,
        status: ProcessingStatus,
        error_message: Optional[str] = None,
    ) -> Optional[UploadedPaper]:
        """Update processing status of an uploaded paper.

        :param upload_id: UUID of the uploaded paper
        :param status: New processing status
        :param error_message: Error message if status is FAILED
        :return: Updated UploadedPaper instance or None
        """
        paper = self.get_by_id(upload_id)
        if not paper:
            return None

        paper.processing_status = status
        if error_message:
            paper.error_message = error_message

        if status == ProcessingStatus.PROCESSING:
            paper.pdf_processing_date = datetime.now(timezone.utc)
        elif status == ProcessingStatus.COMPLETED:
            paper.pdf_processed = True
            if not paper.pdf_processing_date:
                paper.pdf_processing_date = datetime.now(timezone.utc)

        self.session.commit()
        self.session.refresh(paper)
        return paper

    def mark_as_processed(
        self,
        upload_id: UUID,
        title: Optional[str] = None,
        authors: Optional[List[str]] = None,
        abstract: Optional[str] = None,
        raw_text: Optional[str] = None,
        sections: Optional[dict] = None,
        references: Optional[List[dict]] = None,
        parser_used: Optional[str] = None,
        parser_metadata: Optional[dict] = None,
    ) -> Optional[UploadedPaper]:
        """Mark paper as processed and store extracted content.

        :param upload_id: UUID of the uploaded paper
        :param title: Extracted title
        :param authors: List of author names
        :param abstract: Extracted abstract
        :param raw_text: Full text content
        :param sections: Document sections
        :param references: Extracted references
        :param parser_used: Name of parser used
        :param parser_metadata: Parser metadata
        :return: Updated UploadedPaper instance or None
        """
        paper = self.get_by_id(upload_id)
        if not paper:
            return None

        paper.processing_status = ProcessingStatus.COMPLETED
        paper.pdf_processed = True
        paper.pdf_processing_date = datetime.now(timezone.utc)

        if title:
            paper.title = title
        if authors:
            paper.authors = authors
        if abstract:
            paper.abstract = abstract
        if raw_text:
            paper.raw_text = raw_text
        if sections:
            paper.sections = sections
        if references:
            paper.references = references
        if parser_used:
            paper.parser_used = parser_used
        if parser_metadata:
            paper.parser_metadata = parser_metadata

        self.session.commit()
        self.session.refresh(paper)
        return paper

    def mark_as_indexed(self, upload_id: UUID, chunks_count: int = 0) -> Optional[UploadedPaper]:
        """Mark paper as indexed in OpenSearch.

        :param upload_id: UUID of the uploaded paper
        :param chunks_count: Number of chunks indexed
        :return: Updated UploadedPaper instance or None
        """
        paper = self.get_by_id(upload_id)
        if not paper:
            return None

        paper.indexed_at = datetime.now(timezone.utc)
        paper.indexed_chunks = chunks_count

        self.session.commit()
        self.session.refresh(paper)
        return paper

    def get_processing_stats(self) -> dict:
        """Get statistics about upload processing status.

        :return: Dictionary with processing statistics
        """
        total = self.get_count()
        pending = self.get_count(status=ProcessingStatus.PENDING)
        processing = self.get_count(status=ProcessingStatus.PROCESSING)
        completed = self.get_count(status=ProcessingStatus.COMPLETED)
        failed = self.get_count(status=ProcessingStatus.FAILED)

        # Get total file size
        total_size_stmt = select(func.sum(UploadedPaper.file_size_bytes))
        total_size_bytes = self.session.scalar(total_size_stmt) or 0

        return {
            "total_uploads": total,
            "pending": pending,
            "processing": processing,
            "completed": completed,
            "failed": failed,
            "completion_rate": (completed / total * 100) if total > 0 else 0,
            "total_size_bytes": total_size_bytes,
            "total_size_mb": round(total_size_bytes / (1024 * 1024), 2),
        }

    def update(self, paper: UploadedPaper) -> UploadedPaper:
        """Update an existing uploaded paper.

        :param paper: UploadedPaper instance to update
        :return: Updated UploadedPaper instance
        """
        self.session.add(paper)
        self.session.commit()
        self.session.refresh(paper)
        return paper

    def delete(self, upload_id: UUID) -> bool:
        """Delete an uploaded paper (soft delete by marking as deleted).

        :param upload_id: UUID of the uploaded paper
        :return: True if deleted, False if not found
        """
        paper = self.get_by_id(upload_id)
        if not paper:
            return False

        # Soft delete: mark as failed with delete message
        paper.processing_status = ProcessingStatus.FAILED
        paper.error_message = "Deleted by user"
        self.session.commit()
        return True

    def hard_delete(self, upload_id: UUID) -> bool:
        """Permanently delete an uploaded paper from database.

        :param upload_id: UUID of the uploaded paper
        :return: True if deleted, False if not found
        """
        paper = self.get_by_id(upload_id)
        if not paper:
            return False

        self.session.delete(paper)
        self.session.commit()
        return True
