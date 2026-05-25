import logging
from typing import Dict, List, Optional

from src.services.embeddings.jina_client import JinaEmbeddingsClient
from src.services.opensearch.client import OpenSearchClient

from .text_chunker import TextChunker

logger = logging.getLogger(__name__)


class HybridIndexingService:
    """Service for indexing documents with chunking and embeddings for hybrid search.

    Orchestrates the process of:
    1. Chunking documents into overlapping segments
    2. Generating embeddings for each chunk
    3. Indexing chunks with embeddings into OpenSearch
    """

    def __init__(self, chunker: TextChunker, embeddings_client: JinaEmbeddingsClient, opensearch_client: OpenSearchClient):
        """Initialize hybrid indexing service.

        :param chunker: Text chunking service
        :param embeddings_client: Embeddings generation client
        :param opensearch_client: OpenSearch client
        """
        self.chunker = chunker
        self.embeddings_client = embeddings_client
        self.opensearch_client = opensearch_client

        logger.info("Hybrid indexing service initialized")

    async def index_uploaded_paper(self, paper_data: Dict) -> Dict[str, int]:
        """Index an uploaded paper with chunking and embeddings.

        Similar to index_paper but for user-uploaded PDFs.
        Uses upload_id instead of arxiv_id.

        :param paper_data: Paper data from uploaded PDF
        :returns: Dictionary with indexing statistics
        """
        upload_id = paper_data.get("upload_id")

        if not upload_id:
            logger.error("Uploaded paper missing upload_id")
            return {"chunks_created": 0, "chunks_indexed": 0, "embeddings_generated": 0, "errors": 1}

        try:
            # Step 1: Chunk the paper using hybrid section-based approach
            chunks = self.chunker.chunk_paper(
                title=paper_data.get("title", "Untitled"),
                abstract="",  # Uploaded PDFs don't have abstracts
                full_text=paper_data.get("raw_text", ""),
                source_id=upload_id,
                sections=paper_data.get("sections"),
            )

            if not chunks:
                logger.warning(f"No chunks created for uploaded paper {upload_id}")
                return {"chunks_created": 0, "chunks_indexed": 0, "embeddings_generated": 0, "errors": 0}

            logger.info(f"Created {len(chunks)} chunks for uploaded paper {upload_id}")

            # Step 2: Generate embeddings for chunks
            chunk_texts = [chunk.text for chunk in chunks]
            embeddings = await self.embeddings_client.embed_passages(
                texts=chunk_texts,
                batch_size=50,  # Process in batches
            )

            if len(embeddings) != len(chunks):
                logger.error(f"Embedding count mismatch: {len(embeddings)} != {len(chunks)}")
                return {"chunks_created": len(chunks), "chunks_indexed": 0, "embeddings_generated": len(embeddings), "errors": 1}

            # Step 3: Prepare chunks with embeddings for indexing
            chunks_with_embeddings = []

            for chunk, embedding in zip(chunks, embeddings):
                # Prepare chunk data for OpenSearch
                chunk_data = {
                    "upload_id": upload_id,
                    "source_id": upload_id,
                    "source_type": "uploaded",  # Mark as uploaded paper
                    "chunk_index": chunk.metadata.chunk_index,
                    "chunk_text": chunk.text,
                    "chunk_word_count": chunk.metadata.word_count,
                    "start_char": chunk.metadata.start_char,
                    "end_char": chunk.metadata.end_char,
                    "section_title": chunk.metadata.section_title,
                    "embedding_model": "jina-embeddings-v3",
                    # Denormalized paper metadata for efficient search
                    "title": paper_data.get("title", "Untitled"),
                    "authors": ", ".join(paper_data.get("authors", []))
                    if isinstance(paper_data.get("authors"), list)
                    else paper_data.get("authors", ""),
                    "abstract": "",  # No abstract for uploaded papers
                    "categories": [],  # No categories for uploaded papers
                    "published_date": None,  # No published date for uploaded papers
                }

                chunks_with_embeddings.append({"chunk_data": chunk_data, "embedding": embedding})

            # Step 4: Index chunks into OpenSearch
            results = self.opensearch_client.bulk_index_chunks(chunks_with_embeddings)

            logger.info(f"Indexed uploaded paper {upload_id}: {results['success']} chunks successful, {results['failed']} failed")

            return {
                "chunks_created": len(chunks),
                "chunks_indexed": results["success"],
                "embeddings_generated": len(embeddings),
                "errors": results["failed"],
            }

        except Exception as e:
            logger.error(f"Error indexing uploaded paper {upload_id}: {e}")
            return {"chunks_created": 0, "chunks_indexed": 0, "embeddings_generated": 0, "errors": 1}

    async def index_advisory(self, advisory_data: Dict) -> Dict[str, int]:
        """Index a GitHub Security Advisory with chunking and embeddings.

        Args:
            advisory_data: Advisory data from database

        Returns:
            Dictionary with indexing statistics
        """
        ghsa_id = advisory_data.get("ghsa_id")
        advisory_id = str(advisory_data.get("id", ""))

        if not ghsa_id:
            logger.error("Advisory missing ghsa_id")
            return {"chunks_created": 0, "chunks_indexed": 0, "embeddings_generated": 0, "errors": 1}

        try:
            # Step 1: Chunk the advisory
            chunks = self.chunker.chunk_advisory(
                ghsa_id=ghsa_id,
                advisory_id=advisory_id,
                summary=advisory_data.get("summary", ""),
                description=advisory_data.get("description"),
                severity=advisory_data.get("severity"),
                cve_id=advisory_data.get("cve_id"),
                cvss_score=advisory_data.get("cvss_score"),
                affected_packages=advisory_data.get("affected_packages", []),
                affected_ecosystems=advisory_data.get("affected_ecosystems", []),
                cwe_ids=advisory_data.get("cwe_ids", []),
            )

            if not chunks:
                logger.warning(f"No chunks created for advisory {ghsa_id}")
                return {"chunks_created": 0, "chunks_indexed": 0, "embeddings_generated": 0, "errors": 0}

            logger.info(f"Created {len(chunks)} chunks for advisory {ghsa_id}")

            # Step 2: Generate embeddings for chunks
            chunk_texts = [chunk.text for chunk in chunks]
            embeddings = await self.embeddings_client.embed_passages(
                texts=chunk_texts,
                batch_size=50,
            )

            if len(embeddings) != len(chunks):
                logger.error(f"Embedding count mismatch: {len(embeddings)} != {len(chunks)}")
                return {"chunks_created": len(chunks), "chunks_indexed": 0, "embeddings_generated": len(embeddings), "errors": 1}

            # Step 3: Prepare chunks with embeddings for indexing
            chunks_with_embeddings = []

            for chunk, embedding in zip(chunks, embeddings):
                # Prepare chunk data for OpenSearch
                chunk_data = {
                    "source_type": "github_advisory",  # Mark as GitHub advisory
                    "ghsa_id": chunk.ghsa_id,
                    "advisory_id": chunk.advisory_id,
                    "chunk_index": chunk.metadata.chunk_index,
                    "chunk_text": chunk.text,
                    "chunk_word_count": chunk.metadata.word_count,
                    "start_char": chunk.metadata.start_char,
                    "end_char": chunk.metadata.end_char,
                    "section_title": chunk.metadata.section_title,
                    "embedding_model": "jina-embeddings-v3",
                    # Denormalized advisory metadata for efficient search
                    "title": advisory_data.get("summary", ""),  # Use summary as title
                    "severity": advisory_data.get("severity"),
                    "cve_id": advisory_data.get("cve_id"),
                    "cvss_score": advisory_data.get("cvss_score"),
                    "affected_ecosystems": advisory_data.get("affected_ecosystems", []),
                    "affected_packages": advisory_data.get("affected_packages", []),
                    "cwe_ids": advisory_data.get("cwe_ids", []),
                    "published_date": advisory_data.get("published_at"),
                    "updated_date": advisory_data.get("updated_at"),
                    "withdrawn_at": advisory_data.get("withdrawn_at"),
                }

                chunks_with_embeddings.append({"chunk_data": chunk_data, "embedding": embedding})

            # Step 4: Index chunks into OpenSearch
            results = self.opensearch_client.bulk_index_chunks(chunks_with_embeddings)

            logger.info(f"Indexed advisory {ghsa_id}: {results['success']} chunks successful, {results['failed']} failed")

            return {
                "chunks_created": len(chunks),
                "chunks_indexed": results["success"],
                "embeddings_generated": len(embeddings),
                "errors": results["failed"],
            }

        except Exception as e:
            logger.error(f"Error indexing advisory {ghsa_id}: {e}")
            return {"chunks_created": 0, "chunks_indexed": 0, "embeddings_generated": 0, "errors": 1}

    async def index_advisories_batch(self, advisories: List[Dict], replace_existing: bool = False) -> Dict[str, int]:
        """Index multiple GitHub Security Advisories in batch.

        Args:
            advisories: List of advisory data
            replace_existing: If True, delete existing chunks before indexing

        Returns:
            Aggregated statistics
        """
        total_stats = {
            "advisories_processed": 0,
            "total_chunks_created": 0,
            "total_chunks_indexed": 0,
            "total_embeddings_generated": 0,
            "total_errors": 0,
        }

        for advisory in advisories:
            ghsa_id = advisory.get("ghsa_id")

            # Optionally delete existing chunks
            if replace_existing and ghsa_id:
                self.opensearch_client.delete_advisory_chunks(ghsa_id)

            # Index the advisory
            stats = await self.index_advisory(advisory)

            # Update totals
            total_stats["advisories_processed"] += 1
            total_stats["total_chunks_created"] += stats["chunks_created"]
            total_stats["total_chunks_indexed"] += stats["chunks_indexed"]
            total_stats["total_embeddings_generated"] += stats["embeddings_generated"]
            total_stats["total_errors"] += stats["errors"]

        logger.info(
            f"Batch advisory indexing complete: {total_stats['advisories_processed']} advisories, "
            f"{total_stats['total_chunks_indexed']} chunks indexed"
        )

        return total_stats

    async def reindex_advisory(self, ghsa_id: str, advisory_data: Dict) -> Dict[str, int]:
        """Reindex an advisory by deleting old chunks and creating new ones.

        Args:
            ghsa_id: GHSA ID of the advisory
            advisory_data: Updated advisory data

        Returns:
            Indexing statistics
        """
        # Delete existing chunks
        deleted = self.opensearch_client.delete_advisory_chunks(ghsa_id)
        if deleted:
            logger.info(f"Deleted existing chunks for advisory {ghsa_id}")

        # Index with new data
        return await self.index_advisory(advisory_data)
