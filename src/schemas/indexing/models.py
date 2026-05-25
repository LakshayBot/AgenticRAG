from typing import Optional

from pydantic import BaseModel


class ChunkMetadata(BaseModel):
    """Metadata for a text chunk."""

    chunk_index: int
    start_char: int
    end_char: int
    word_count: int
    overlap_with_previous: int
    overlap_with_next: int
    section_title: Optional[str] = None


class TextChunk(BaseModel):
    """A chunk of text with metadata.

    Supports both GitHub Security Advisories and uploaded PDFs.
    For uploaded PDFs: use source_id (the upload_id)
    For advisories: use ghsa_id and advisory_id
    """

    text: str
    metadata: ChunkMetadata
    # Generic source ID for uploaded PDFs
    source_id: Optional[str] = None
    # Advisory fields (optional for uploaded PDFs)
    ghsa_id: Optional[str] = None
    advisory_id: Optional[str] = None
