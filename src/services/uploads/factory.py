"""Factory function for creating upload processor service."""

from typing import Optional

from sqlalchemy.orm import Session

from src.config import Settings, get_settings
from src.repositories.uploaded_paper import UploadedPaperRepository
from src.services.indexing.factory import make_hybrid_indexing_service
from src.services.pdf_parser.parser import PDFParserService

from .processor import UploadProcessor


def make_upload_processor(
    session: Session,
    settings: Optional[Settings] = None,
    pdf_parser: Optional[PDFParserService] = None,
) -> UploadProcessor:
    """Factory function to create upload processor service.

    :param session: Database session
    :param settings: Optional settings instance
    :param pdf_parser: Optional PDF parser service
    :returns: UploadProcessor instance
    """
    if settings is None:
        settings = get_settings()

    # Use provided PDF parser or get from app state (will be injected via dependencies)
    # The pdf_parser will be passed in from the dependency injection
    if pdf_parser is None:
        raise ValueError("PDF parser service must be provided")
    
    # Create indexing service
    indexing_service = make_hybrid_indexing_service(settings)

    # Create upload processor
    return UploadProcessor(
        pdf_parser=pdf_parser,
        indexing_service=indexing_service,
    )
