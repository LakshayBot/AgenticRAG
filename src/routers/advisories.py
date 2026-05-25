"""FastAPI router for GitHub Security Advisory AI/ML processing.

This service is called by the .NET backend for AI/ML tasks only:
- Fetching data from GitHub API
- Text chunking
- Embedding generation
- OpenSearch indexing

Database operations are handled by .NET backend.
"""

import logging
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..dependencies import SettingsDep
from ..services.embeddings.jina_client import JinaEmbeddingsClient
from ..services.embeddings.factory import make_embeddings_client
from ..services.github import make_github_client, GitHubAdvisoryFetcher
from ..services.indexing.hybrid_indexer import HybridIndexingService
from ..services.indexing.text_chunker import TextChunker
from ..services.opensearch.factory import make_opensearch_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/advisories", tags=["Advisories"])


# ============================================================================
# DTOs (Data Transfer Objects) - Match .NET DTOs
# ============================================================================


class AdvisoryFetchRequest(BaseModel):
    """Request to fetch advisories from GitHub API."""

    max_results: Optional[int] = Field(None, description="Maximum advisories to fetch")
    severity: Optional[str] = Field(None, description="Filter by severity (critical, high, medium, low)")
    ecosystem: Optional[str] = Field(None, description="Filter by ecosystem (npm, pip, go, etc.)")
    modified_since: Optional[str] = Field(None, description="Filter advisories modified since date (ISO 8601)")


class GitHubAdvisoryDto(BaseModel):
    """Advisory data fetched from GitHub."""

    ghsa_id: str
    cve_id: Optional[str] = None
    summary: str
    description: str
    severity: str
    cvss_score: Optional[float] = None
    type: str
    affected_ecosystems: List[str]
    affected_packages: List[str]
    vulnerabilities: List[dict]
    cwe_ids: List[str]
    cwes: List[dict]
    reference_urls: List[str]
    github_url: str
    published_at: Optional[str] = None
    updated_at: Optional[str] = None
    withdrawn_at: Optional[str] = None


class AdvisoryFetchResult(BaseModel):
    """Result of fetching advisories from GitHub."""

    total_fetched: int
    advisories: List[GitHubAdvisoryDto]
    severity_breakdown: Dict[str, int]
    ecosystem_breakdown: Dict[str, int]


class AdvisoryData(BaseModel):
    """Advisory data for processing (passed from .NET)."""

    ghsa_id: str
    summary: str
    description: str
    severity: str
    affected_ecosystems: List[str]
    cve_id: Optional[str] = None
    cvss_score: Optional[float] = None
    affected_packages: List[str] = []
    cwe_ids: List[str] = []
    published_at: Optional[str] = None
    updated_at: Optional[str] = None
    withdrawn_at: Optional[str] = None
    metadata: Optional[Dict] = None


class AdvisoryProcessRequest(BaseModel):
    """Request to process advisories (chunk, embed, index)."""

    advisories: List[AdvisoryData]
    replace_existing: bool = Field(True, description="Replace existing chunks in OpenSearch")


class AdvisoryProcessResult(BaseModel):
    """Result of processing advisories."""

    advisories_processed: int
    chunks_indexed: int
    status: str
    errors: List[str] = []


# ============================================================================
# Endpoints - Called by .NET Backend
# ============================================================================


@router.post("/fetch", response_model=AdvisoryFetchResult)
async def fetch_advisories(request: AdvisoryFetchRequest, settings: SettingsDep):
    """
    Fetch advisories from GitHub API and return JSON.

    This endpoint is called by .NET backend.
    .NET will store the returned advisories in PostgreSQL.

    Args:
        request: Fetch parameters (severity, ecosystem, etc.)
        settings: Application settings

    Returns:
        AdvisoryFetchResult with list of advisories
    """
    try:
        logger.info(f"Fetching advisories from GitHub: {request.dict()}")

        # Use existing GitHub client to fetch from API
        github_client = make_github_client(settings)
        fetcher = GitHubAdvisoryFetcher(github_client, settings)

        # Fetch from GitHub (returns raw data, no database operations)
        fetch_results = await fetcher.fetch_advisories(
            max_results=request.max_results,
            severity=request.severity,
            ecosystem=request.ecosystem,
            modified_since=request.modified_since,
        )

        # Transform to DTOs
        advisories = []
        for adv_data in fetch_results["advisories"]:
            advisories.append(
                GitHubAdvisoryDto(
                    ghsa_id=adv_data["ghsa_id"],
                    cve_id=adv_data.get("cve_id"),
                    summary=adv_data["summary"],
                    description=adv_data["description"],
                    severity=adv_data["severity"],
                    cvss_score=adv_data.get("cvss_score"),
                    type=adv_data["type"],
                    affected_ecosystems=adv_data["affected_ecosystems"],
                    affected_packages=adv_data["affected_packages"],
                    vulnerabilities=adv_data["vulnerabilities"],
                    cwe_ids=adv_data["cwe_ids"],
                    cwes=adv_data["cwes"],
                    reference_urls=adv_data["reference_urls"],
                    github_url=adv_data["github_url"],
                    published_at=adv_data.get("published_at"),
                    updated_at=adv_data.get("updated_at"),
                    withdrawn_at=adv_data.get("withdrawn_at"),
                )
            )

        # Calculate breakdowns
        severity_breakdown = fetch_results.get("severity_breakdown", {})
        ecosystem_breakdown = fetch_results.get("ecosystem_breakdown", {})

        logger.info(f"Fetched {len(advisories)} advisories from GitHub")

        return AdvisoryFetchResult(
            total_fetched=len(advisories),
            advisories=advisories,
            severity_breakdown=severity_breakdown,
            ecosystem_breakdown=ecosystem_breakdown,
        )

    except Exception as e:
        logger.error(f"Error fetching advisories: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/process", response_model=AdvisoryProcessResult)
async def process_advisories(request: AdvisoryProcessRequest, settings: SettingsDep):
    """
    Process advisories: chunk, generate embeddings, index to OpenSearch.

    This endpoint is called by .NET backend after advisories are stored in PostgreSQL.
    .NET passes advisory data to process.

    Args:
        request: Advisory data to process
        settings: Application settings

    Returns:
        AdvisoryProcessResult with processing statistics
    """
    try:
        logger.info(f"Processing {len(request.advisories)} advisories for indexing")

        # Initialize AI/ML services
        chunker = TextChunker(
            chunk_size=settings.chunking.chunk_size,
            overlap_size=settings.chunking.overlap_size,
            min_chunk_size=settings.chunking.min_chunk_size,
        )
        embeddings_client = make_embeddings_client()
        opensearch_client = make_opensearch_client()
        indexer = HybridIndexingService(chunker, embeddings_client, opensearch_client)

        chunks_indexed = 0
        errors = []

        for advisory in request.advisories:
            try:
                # Prepare advisory data for indexing
                advisory_data = {
                    "ghsa_id": advisory.ghsa_id,
                    "summary": advisory.summary,
                    "description": advisory.description,
                    "severity": advisory.severity,
                    "affected_ecosystems": advisory.affected_ecosystems,
                    "cve_id": advisory.cve_id,
                    "cvss_score": advisory.cvss_score,
                    "affected_packages": advisory.affected_packages,
                    "cwe_ids": advisory.cwe_ids,
                    "published_at": advisory.published_at,
                    "updated_at": advisory.updated_at,
                    "withdrawn_at": advisory.withdrawn_at,
                    "metadata": advisory.metadata or {},
                }

                # Index advisory (chunking, embedding, indexing happen inside)
                index_result = await indexer.index_advisory(advisory_data)

                chunks_indexed += index_result.get("chunks_indexed", 0)

            except Exception as e:
                error_msg = f"Error processing {advisory.ghsa_id}: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)

        logger.info(f"Indexed {chunks_indexed} chunks for {len(request.advisories)} advisories")

        return AdvisoryProcessResult(
            advisories_processed=len(request.advisories),
            chunks_indexed=chunks_indexed,
            status="success" if not errors else "partial_success",
            errors=errors,
        )

    except Exception as e:
        logger.error(f"Error processing advisories: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """Health check endpoint for .NET to verify Python service is running."""
    return {"status": "healthy", "service": "advisory-processing", "endpoints": ["/fetch", "/process"]}
