"""Upload processor service for parsing, extracting metadata, and indexing uploaded PDFs."""

import logging
from pathlib import Path
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from src.exceptions import PDFParsingException, PDFValidationError
from src.models.paper import ProcessingStatus
from src.repositories.uploaded_paper import UploadedPaperRepository
from src.schemas.pdf_parser.models import PdfContent
from src.services.indexing.hybrid_indexer import HybridIndexingService
from src.services.pdf_parser.parser import PDFParserService

logger = logging.getLogger(__name__)


class UploadProcessor:
    """Service for processing uploaded PDF files.
    
    Orchestrates:
    1. PDF parsing with DoclingParser
    2. Metadata extraction (title, authors)
    3. Chunking and indexing to OpenSearch
    """

    def __init__(
        self,
        pdf_parser: PDFParserService,
        indexing_service: HybridIndexingService,
    ):
        """Initialize upload processor.
        
        :param pdf_parser: PDF parsing service
        :param indexing_service: Hybrid indexing service
        """
        self.pdf_parser = pdf_parser
        self.indexing_service = indexing_service

    async def process_uploaded_pdf(self, upload_id: UUID, session: Session) -> Dict[str, any]:
        """Process an uploaded PDF through the full pipeline.
        
        :param upload_id: ID of the uploaded paper
        :param session: Database session
        :returns: Processing statistics
        :raises: PDFParsingException, PDFValidationError
        """
        logger.info(f"Starting processing for upload {upload_id}")
        
        repository = UploadedPaperRepository(session)
        
        try:
            # Get upload record
            upload = repository.get_by_id(upload_id)
            if not upload:
                raise ValueError(f"Upload {upload_id} not found")
            
            # Update status to processing
            repository.update_status(upload_id, ProcessingStatus.PROCESSING)
            
            # Step 1: Parse PDF
            logger.info(f"Parsing PDF: {upload.filename}")
            parsed_content = await self._parse_pdf(Path(upload.file_path))
            
            # Step 2: Extract and save metadata
            logger.info(f"Extracting metadata for upload {upload_id}")
            metadata = self._extract_metadata(parsed_content)
            self._save_metadata(session, upload_id, metadata, parsed_content, repository)
            
            # Step 3: Chunk and index
            logger.info(f"Indexing upload {upload_id}")
            indexing_stats = await self._chunk_and_index(upload_id, parsed_content, metadata)
            
            # Mark as completed and indexed
            repository.mark_as_processed(upload_id)
            repository.mark_as_indexed(upload_id)
            
            logger.info(
                f"Successfully processed upload {upload_id}: "
                f"{indexing_stats['chunks_indexed']} chunks indexed"
            )
            
            return {
                "upload_id": str(upload_id),
                "status": "completed",
                "chunks_created": indexing_stats["chunks_created"],
                "chunks_indexed": indexing_stats["chunks_indexed"],
                "metadata": metadata,
            }
            
        except (PDFParsingException, PDFValidationError) as e:
            logger.error(f"PDF processing error for upload {upload_id}: {e}")
            repository.update_status(
                upload_id, 
                ProcessingStatus.FAILED,
                error_message=str(e)
            )
            raise
            
        except Exception as e:
            logger.error(f"Unexpected error processing upload {upload_id}: {e}")
            repository.update_status(
                upload_id,
                ProcessingStatus.FAILED,
                error_message=f"Unexpected error: {str(e)}"
            )
            raise

    async def _parse_pdf(self, file_path: Path) -> PdfContent:
        """Parse PDF file using PDF parser service.
        
        :param file_path: Path to PDF file
        :returns: Parsed PDF content
        :raises: PDFParsingException, PDFValidationError
        """
        result = await self.pdf_parser.parse_pdf(file_path)
        if not result:
            raise PDFParsingException(f"Failed to parse PDF: {file_path}")
        return result

    def _extract_metadata(self, parsed_content: PdfContent) -> Dict[str, any]:
        """Extract metadata from parsed PDF content.
        
        Extracts:
        - Title (from first heading or first line)
        - Authors (attempts to extract from content)
        - Section count
        
        :param parsed_content: Parsed PDF content
        :returns: Metadata dictionary
        """
        metadata = {
            "title": None,
            "authors": None,
            "section_count": 0,
        }
        
        # Extract title - use first heading if available, else first line of text
        if parsed_content.sections:
            first_section = parsed_content.sections[0]
            if first_section.title:
                metadata["title"] = first_section.title
            elif first_section.content:
                # Use first line as title
                first_line = first_section.content.split('\n')[0].strip()
                metadata["title"] = first_line[:200]  # Limit length
        
        # If still no title, use raw text
        if not metadata["title"] and parsed_content.raw_text:
            first_line = parsed_content.raw_text.split('\n')[0].strip()
            metadata["title"] = first_line[:200]
        
        # Count sections
        metadata["section_count"] = len(parsed_content.sections)
        
        # Author extraction - basic heuristic (look for "Author:", "By:", etc.)
        authors = self._extract_authors(parsed_content)
        if authors:
            metadata["authors"] = authors
        
        return metadata

    def _extract_authors(self, parsed_content: PdfContent) -> Optional[List[str]]:
        """Attempt to extract author names from PDF content.
        
        Uses simple heuristics - looks for patterns like:
        - "Author:", "Authors:", "By:"
        - Text near the top of the document
        
        :param parsed_content: Parsed PDF content
        :returns: List of author names or None
        """
        # Look in first few sections
        for section in parsed_content.sections[:3]:
            content = section.content.lower()
            
            # Look for author indicators
            for indicator in ["author:", "authors:", "by:"]:
                if indicator in content:
                    # Extract text after indicator
                    idx = content.index(indicator)
                    author_text = section.content[idx + len(indicator):].split('\n')[0].strip()
                    
                    # Simple split by comma or "and"
                    if ',' in author_text:
                        authors = [a.strip() for a in author_text.split(',')]
                    elif ' and ' in author_text.lower():
                        authors = [a.strip() for a in author_text.lower().split(' and ')]
                    else:
                        authors = [author_text]
                    
                    # Filter out empty strings
                    authors = [a for a in authors if a and len(a) > 2]
                    if authors:
                        return authors
        
        return None

    def _save_metadata(
        self, 
        session: Session, 
        upload_id: UUID, 
        metadata: Dict[str, any],
        parsed_content: PdfContent,
        repository: UploadedPaperRepository
    ) -> None:
        """Save extracted metadata to database.
        
        :param session: Database session
        :param upload_id: Upload ID
        :param metadata: Extracted metadata
        :param parsed_content: Parsed PDF content
        :param repository: Uploaded paper repository
        """
        # Get the upload record
        upload = repository.get_by_id(upload_id)
        if not upload:
            return
        
        # Update fields
        upload.title = metadata.get("title")
        upload.authors = metadata.get("authors")
        upload.raw_text = parsed_content.raw_text
        
        # Save sections as JSON-serializable format
        if parsed_content.sections:
            upload.sections = [
                {
                    "title": section.title,
                    "content": section.content,
                    "page_number": section.page_number,
                }
                for section in parsed_content.sections
            ]
        
        session.commit()

    async def _chunk_and_index(
        self,
        upload_id: UUID,
        parsed_content: PdfContent,
        metadata: Dict[str, any]
    ) -> Dict[str, int]:
        """Chunk content and index to OpenSearch.
        
        :param upload_id: Upload ID
        :param parsed_content: Parsed PDF content
        :param metadata: Extracted metadata
        :returns: Indexing statistics
        """
        # Prepare paper data in the format expected by indexing service
        paper_data = {
            "upload_id": str(upload_id),
            "source_type": "uploaded",
            "title": metadata.get("title", "Untitled"),
            "authors": metadata.get("authors", []),
            "sections": [
                {
                    "title": section.title,
                    "content": section.content,
                    "page_number": section.page_number,
                }
                for section in parsed_content.sections
            ],
            "raw_text": parsed_content.raw_text,
        }
        
        # Use the hybrid indexing service's index_uploaded_paper method
        # (We'll add this method in the next step)
        stats = await self.indexing_service.index_uploaded_paper(paper_data)
        
        return stats
