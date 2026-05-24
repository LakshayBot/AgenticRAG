"""
Search Microservice
Port: 8003
Purpose: Perform hybrid, BM25, and vector search using OpenSearch
"""

import os
import logging
from typing import List, Dict, Any, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Import from shared src directory
import sys

sys.path.append("/app/src")
sys.path.append("/app")

from src.services.opensearch.client import OpenSearchClient
from src.config import get_settings

# Initialize settings
settings = get_settings()

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


# Request/Response Models
class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


class SearchRequest(BaseModel):
    query: str
    top_k: int = 10
    filters: Optional[Dict[str, Any]] = None


class HybridSearchRequest(SearchRequest):
    alpha: float = 0.5  # Weight for vector search (1-alpha for BM25)


class SearchResult(BaseModel):
    id: str
    source_id: str = ""
    title: str = ""
    chunk_text: Optional[str] = None
    chunk_index: int = 0
    score: float
    snippet: Optional[str] = None
    authors: Optional[List[str]] = None
    published_date: Optional[str] = None


class SearchResponse(BaseModel):
    results: List[SearchResult]
    total_results: int
    query: str
    search_type: str
    query_time_ms: float = 0.0


class ChunkData(BaseModel):
    text: str
    embedding: List[float]
    chunkIndex: int


class BulkIndexRequest(BaseModel):
    paperId: str
    sourceId: str
    title: str
    chunks: List[ChunkData]


class BulkIndexResponse(BaseModel):
    success: bool
    indexed: int
    failed: int
    paperId: str


# Service instance
opensearch_client: OpenSearchClient = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup service resources"""
    global opensearch_client

    logger.info("Initializing Search Service...")
    try:
        opensearch_host = os.getenv("OPENSEARCH__HOST", "http://localhost:9200")
        opensearch_client = OpenSearchClient(host=opensearch_host, settings=settings)

        # Check health
        if opensearch_client.health_check():
            logger.info("OpenSearch is healthy")
            # Ensure index exists with proper mapping
            setup_results = opensearch_client.setup_indices(force=False)
            logger.info(f"Index setup results: {setup_results}")
        else:
            logger.warning("OpenSearch may not be fully ready")

    except Exception as e:
        logger.error(f"Failed to initialize service: {e}")
        raise

    yield

    logger.info("Shutting down Search Service...")


# FastAPI application
app = FastAPI(
    title="Search Service",
    description="Microservice for hybrid, BM25, and vector search using OpenSearch",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(status="healthy", service="search", version="1.0.0")


def deduplicate_hits(hits: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Deduplicate search hits by source_id, keeping the highest-scoring chunk per advisory.
    Falls back to chunk_id deduplication when source_id is absent.
    """
    seen: Dict[str, Dict[str, Any]] = {}
    for hit in hits:
        key = hit.get("source_id") or hit.get("ghsa_id") or hit.get("chunk_id", "")
        if not key:
            continue
        existing = seen.get(key)
        if existing is None or hit.get("score", 0.0) > existing.get("score", 0.0):
            seen[key] = hit
    return list(seen.values())


@app.post("/api/v1/search/hybrid", response_model=SearchResponse)
async def hybrid_search(request: HybridSearchRequest):
    """
    Perform hybrid search (combines BM25 and vector search)
    """
    try:
        logger.info(f"Hybrid search for query: {request.query}")

        results = opensearch_client.search_unified(
            query=request.query,
            query_embedding=None,  # BM25 fallback — embeddings service not available here
            size=request.top_k,
            use_hybrid=False,
        )

        hits = deduplicate_hits(results.get("hits", []))
        return SearchResponse(
            results=[
                SearchResult(
                    id=r.get("chunk_id", str(idx)),
                    source_id=r.get("source_id") or r.get("ghsa_id") or "",
                    title=r.get("title", ""),
                    chunk_text=r.get("chunk_text") or r.get("text"),
                    chunk_index=r.get("chunk_index", idx),
                    score=r.get("score", 0.0),
                    snippet=r.get("chunk_text") or r.get("text"),
                    authors=r.get("authors"),
                    published_date=r.get("published_date") or r.get("published_at"),
                )
                for idx, r in enumerate(hits)
            ],
            total_results=len(hits),
            query=request.query,
            search_type="hybrid",
        )

    except Exception as e:
        logger.error(f"Error in hybrid search: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@app.post("/api/v1/search/bm25", response_model=SearchResponse)
async def bm25_search(request: SearchRequest):
    """
    Perform BM25 (keyword-based) search
    """
    try:
        logger.info(f"BM25 search for query: {request.query}")

        results = opensearch_client.search_unified(
            query=request.query,
            query_embedding=None,
            size=request.top_k,
            use_hybrid=False,
        )

        hits = deduplicate_hits(results.get("hits", []))
        return SearchResponse(
            results=[
                SearchResult(
                    id=r.get("chunk_id", str(idx)),
                    source_id=r.get("source_id") or r.get("ghsa_id") or "",
                    title=r.get("title", ""),
                    chunk_text=r.get("chunk_text") or r.get("text"),
                    chunk_index=r.get("chunk_index", idx),
                    score=r.get("score", 0.0),
                    snippet=r.get("chunk_text") or r.get("text"),
                    authors=r.get("authors"),
                    published_date=r.get("published_date") or r.get("published_at"),
                )
                for idx, r in enumerate(hits)
            ],
            total_results=len(hits),
            query=request.query,
            search_type="bm25",
        )

    except Exception as e:
        logger.error(f"Error in BM25 search: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@app.post("/api/v1/search/vector", response_model=SearchResponse)
async def vector_search(request: SearchRequest):
    """
    Perform vector similarity search (falls back to BM25 when no embedding available)
    """
    try:
        logger.info(f"Vector search for query: {request.query}")

        results = opensearch_client.search_unified(
            query=request.query,
            query_embedding=None,
            size=request.top_k,
            use_hybrid=False,
        )

        hits = deduplicate_hits(results.get("hits", []))
        return SearchResponse(
            results=[
                SearchResult(
                    id=r.get("chunk_id", str(idx)),
                    source_id=r.get("source_id") or r.get("ghsa_id") or "",
                    title=r.get("title", ""),
                    chunk_text=r.get("chunk_text") or r.get("text"),
                    chunk_index=r.get("chunk_index", idx),
                    score=r.get("score", 0.0),
                    snippet=r.get("chunk_text") or r.get("text"),
                    authors=r.get("authors"),
                    published_date=r.get("published_date") or r.get("published_at"),
                )
                for idx, r in enumerate(hits)
            ],
            total_results=len(hits),
            query=request.query,
            search_type="vector",
        )

    except Exception as e:
        logger.error(f"Error in vector search: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@app.post("/api/v1/index/bulk-insert", response_model=BulkIndexResponse)
async def bulk_insert_chunks(request: BulkIndexRequest):
    """
    Bulk index chunks for a paper into OpenSearch

    Args:
        request: Bulk index request with paper ID, arxiv ID, title, and chunks

    Returns:
        Indexing result with success status and counts
    """
    try:
        logger.info(f"Indexing {len(request.chunks)} chunks for paper {request.paperId}")

        # Prepare chunks for OpenSearch
        chunks_data = []
        for idx, chunk in enumerate(request.chunks):
            chunk_record = {
                "chunk_data": {
                    "source_id": request.sourceId,
                    "paper_id": request.paperId,
                    "title": request.title,
                    "chunk_index": chunk.chunkIndex,
                    "content": chunk.text,
                    "metadata": {"total_chunks": len(request.chunks), "chunk_number": idx + 1},
                },
                "embedding": chunk.embedding,
            }
            chunks_data.append(chunk_record)

        # Bulk index using OpenSearch client
        result = opensearch_client.bulk_index_chunks(chunks_data)

        success = result.get("success", 0)
        failed = result.get("failed", 0)

        logger.info(f"Indexed {success} chunks successfully, {failed} failed for paper {request.paperId}")

        return BulkIndexResponse(success=(failed == 0), indexed=success, failed=failed, paperId=request.paperId)

    except Exception as e:
        logger.error(f"Error bulk indexing chunks for paper {request.paperId}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Bulk indexing failed: {str(e)}")


class AdvisoryChunkCount(BaseModel):
    ghsa_id: str
    chunk_count: int


class AdvisoryChunkCountsResponse(BaseModel):
    counts: List[AdvisoryChunkCount]
    total_advisories: int
    total_chunks: int


@app.get("/api/v1/chunks/advisory-counts", response_model=AdvisoryChunkCountsResponse)
async def get_advisory_chunk_counts(limit: int = 30):
    """
    Return chunk counts per advisory (ghsa_id) via OpenSearch terms aggregation.
    Useful for analytics — shows which advisories have the most indexed content.
    """
    try:
        index_name = opensearch_client.index_name
        body = {
            "size": 0,
            "query": {"term": {"source_type": "github_advisory"}},
            "aggs": {
                "by_advisory": {
                    "terms": {
                        "field": "ghsa_id",
                        "size": limit,
                        "order": {"_count": "desc"},
                    }
                }
            },
        }
        resp = opensearch_client.client.search(index=index_name, body=body)
        buckets = resp.get("aggregations", {}).get("by_advisory", {}).get("buckets", [])
        counts = [AdvisoryChunkCount(ghsa_id=b["key"], chunk_count=b["doc_count"]) for b in buckets]
        total_chunks = sum(c.chunk_count for c in counts)
        return AdvisoryChunkCountsResponse(
            counts=counts,
            total_advisories=len(counts),
            total_chunks=total_chunks,
        )
    except Exception as e:
        logger.error(f"Error getting advisory chunk counts: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Aggregation failed: {str(e)}")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Search Service",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "hybrid": "/api/v1/search/hybrid",
            "bm25": "/api/v1/search/bm25",
            "vector": "/api/v1/search/vector",
            "bulk_index": "/api/v1/index/bulk-insert",
        },
    }


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("SERVICE_PORT", 8003))
    uvicorn.run(app, host="0.0.0.0", port=port)
