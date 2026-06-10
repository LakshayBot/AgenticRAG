"""
Agentic RAG Microservice
Port: 8004
Purpose: Answer questions using agentic RAG workflows with LangGraph and Ollama
"""

import os
import logging
from typing import List, Dict, Any, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# Import from shared src directory
import sys

sys.path.append("/app/src")
sys.path.append("/app")

from src.services.agents.agentic_rag import AgenticRAGService
from src.services.opensearch.client import OpenSearchClient
from src.services.ollama.client import OllamaClient
from src.services.embeddings.jina_client import JinaEmbeddingsClient
from src.services.langfuse.client import LangfuseTracer
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


class RAGRequest(BaseModel):
    question: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    top_k: int = 5
    model: str = "llama3.2:1b"
    file_ids: Optional[List[str]] = None  # Filter by specific file/paper IDs
    advisory_ids: Optional[List[str]] = None  # Filter by specific advisory GHSA IDs
    use_hybrid: bool = True
    conversation_history: Optional[List[Dict[str, Any]]] = None  # Prior turns [{"role": "user"|"assistant", "content": "..."}]


class AgenticRAGRequest(RAGRequest):
    max_iterations: int = 3
    enable_reasoning: bool = True


class SourceDocument(BaseModel):
    sourceId: str = ""
    title: str = ""
    authors: Optional[List[str]] = None
    chunkText: Optional[str] = None
    chunkIndex: int = 0
    score: float = 0.0


class RAGResponse(BaseModel):
    answer: str
    sources: List[SourceDocument]
    question: str
    model: str
    reasoning_steps: Optional[List[str]] = None


# Service instance
rag_service: AgenticRAGService = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup service resources"""
    global rag_service

    logger.info("Initializing Agentic RAG Service...")
    try:
        # Initialize OpenSearch client
        opensearch_host = os.getenv("OPENSEARCH__HOST", "http://localhost:9200")
        opensearch_client = OpenSearchClient(host=opensearch_host, settings=settings)

        # Initialize Ollama client
        ollama_client = OllamaClient(settings=settings)

        # Initialize embeddings client
        jina_api_key = os.getenv("JINA_API_KEY", "")
        embeddings_client = JinaEmbeddingsClient(api_key=jina_api_key)

        # Initialize Langfuse tracer (optional)
        langfuse_tracer = None
        if settings.langfuse.enabled:
            try:
                langfuse_tracer = LangfuseTracer(settings=settings)
                logger.info("Langfuse tracer initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Langfuse tracer: {e}")

        # Initialize Agentic RAG service
        rag_service = AgenticRAGService(
            opensearch_client=opensearch_client,
            ollama_client=ollama_client,
            embeddings_client=embeddings_client,
            langfuse_tracer=langfuse_tracer,
        )

        logger.info("Agentic RAG Service initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize service: {e}", exc_info=True)
        raise

    yield

    logger.info("Shutting down Agentic RAG Service...")


# FastAPI application
app = FastAPI(
    title="Agentic RAG Service",
    description="Microservice for agentic RAG with LangGraph and Ollama",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(status="healthy", service="agentic-rag", version="1.0.0")


@app.post("/api/v1/ask", response_model=RAGResponse)
async def ask_question(request: RAGRequest):
    """
    Answer a question using standard RAG (retrieve + generate)

    Args:
        request: Question and parameters

    Returns:
        Answer with source documents
    """
    try:
        logger.info(f"RAG request for question: {request.question}")

        result = await rag_service.ask(
            query=request.question,
            user_id=request.user_id or request.session_id or "default",
            session_id=request.session_id,
            model=request.model,
            file_ids=request.file_ids,
            advisory_ids=request.advisory_ids,
            conversation_history=request.conversation_history,
        )

        sources = []
        for src in result.get("sources", []):
            if isinstance(src, dict):
                sources.append(
                    SourceDocument(
                        sourceId=src.get("sourceId", ""),
                        title=src.get("title", ""),
                        authors=src.get("authors") if isinstance(src.get("authors"), list) else None,
                        chunkText=src.get("chunk_text") or src.get("page_content"),
                        chunkIndex=src.get("chunk_index", 0),
                        score=float(src.get("score", 0.0)),
                    )
                )

        return RAGResponse(
            answer=result.get("answer", "No answer generated"),
            sources=sources,
            question=request.question,
            model=request.model,
        )

    except Exception as e:
        logger.error(f"Error in RAG: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"RAG failed: {str(e)}")


@app.post("/api/v1/ask-agentic", response_model=RAGResponse)
async def ask_agentic(request: AgenticRAGRequest):
    """
    Answer a question using agentic RAG (planning + reasoning + retrieval)

    Args:
        request: Question with agentic parameters

    Returns:
        Answer with reasoning steps and sources
    """
    try:
        logger.info(f"Agentic RAG request for question: {request.question}")
        if request.file_ids:
            logger.info(f"File IDs filter: {request.file_ids}")
        if request.advisory_ids:
            logger.info(f"Advisory IDs filter: {request.advisory_ids}")

        # Use the full agentic workflow
        result = await rag_service.ask(
            query=request.question,
            user_id=request.user_id or request.session_id or "default",
            session_id=request.session_id,
            model=request.model,
            file_ids=request.file_ids,
            advisory_ids=request.advisory_ids,
            conversation_history=request.conversation_history,
        )

        # Extract sources — result["sources"] is a list of dicts with OpenSearch hit fields
        sources = []
        for src in result.get("sources", []):
            if isinstance(src, dict):
                sources.append(
                    SourceDocument(
                        sourceId=src.get("sourceId", ""),
                        title=src.get("title", ""),
                        authors=src.get("authors") if isinstance(src.get("authors"), list) else None,
                        chunkText=src.get("chunk_text") or src.get("page_content"),
                        chunkIndex=src.get("chunk_index", 0),
                        score=float(src.get("score", 0.0)),
                    )
                )

        # Extract reasoning steps if available
        reasoning_steps = result.get("reasoning_steps", [])

        return RAGResponse(
            answer=result.get("answer", "No answer generated"),
            sources=sources,
            question=request.question,
            model=request.model,
            reasoning_steps=reasoning_steps if reasoning_steps else None,
        )

    except Exception as e:
        logger.error(f"Error in agentic RAG: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Agentic RAG failed: {str(e)}")


@app.post("/api/v1/ask-stream")
async def ask_stream(request: RAGRequest):
    """
    Stream answer generation for a question

    Args:
        request: Question and parameters

    Returns:
        Streaming response
    """
    try:
        logger.info(f"Streaming RAG request for question: {request.question}")

        async def generate():
            answer = await rag_service.ask(
                query=request.question,
                user_id=request.user_id or request.session_id or "default",
                session_id=request.session_id,
                model=request.model,
                file_ids=request.file_ids,
                advisory_ids=request.advisory_ids,
                conversation_history=request.conversation_history,
            )
            yield f"data: {answer.get('answer', 'No answer')}\n\n"

        return StreamingResponse(generate(), media_type="text/event-stream")

    except Exception as e:
        logger.error(f"Error in streaming RAG: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Streaming RAG failed: {str(e)}")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Agentic RAG Service",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "ask": "/api/v1/ask",
            "ask_agentic": "/api/v1/ask-agentic",
            "ask_stream": "/api/v1/ask-stream",
        },
    }


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("SERVICE_PORT", 8004))
    uvicorn.run(app, host="0.0.0.0", port=port)
