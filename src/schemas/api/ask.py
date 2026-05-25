from typing import List, Optional

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    """Request model for RAG question answering."""

    query: str = Field(..., description="User's question", min_length=1, max_length=1000)
    top_k: int = Field(3, description="Number of top chunks to retrieve", ge=1, le=10)
    use_hybrid: bool = Field(True, description="Use hybrid search (BM25 + vector)")
    model: str = Field("llama3.2:1b", description="Ollama model to use for generation")
    source_ids: Optional[List[str]] = Field(None, description="Filter by specific source IDs (upload_id or ghsa_id)")

    class Config:
        json_schema_extra = {
            "example": {
                "query": "What vulnerabilities affect the npm package?",
                "top_k": 3,
                "use_hybrid": True,
                "model": "llama3.2:1b",
                "source_ids": ["550e8400-e29b-41d4-a716-446655440000"],
            }
        }


class AskResponse(BaseModel):
    """Response model for RAG question answering."""

    query: str = Field(..., description="Original user question")
    answer: str = Field(..., description="Generated answer from LLM")
    sources: List[str] = Field(..., description="Source URLs")
    chunks_used: int = Field(..., description="Number of chunks used for generation")
    search_mode: str = Field(..., description="Search mode used: bm25 or hybrid")

    class Config:
        json_schema_extra = {
            "example": {
                "query": "What vulnerabilities affect the npm package?",
                "answer": "The npm package has a critical vulnerability...",
                "sources": ["https://github.com/advisories/GHSA-xxxx-yyyy-zzzz"],
                "chunks_used": 3,
                "search_mode": "hybrid",
            }
        }


class AgenticAskResponse(AskResponse):
    """Response model for agentic RAG question answering."""

    reasoning_steps: List[str] = Field(..., description="Agent's decision-making steps")
    retrieval_attempts: int = Field(..., description="Number of document retrieval attempts")
    trace_id: Optional[str] = Field(None, description="Langfuse trace ID for feedback and debugging")

    class Config:
        json_schema_extra = {
            "example": {
                "query": "What vulnerabilities affect the npm package?",
                "answer": "The npm package has a critical vulnerability...",
                "sources": ["https://github.com/advisories/GHSA-xxxx-yyyy-zzzz"],
                "chunks_used": 3,
                "search_mode": "hybrid",
                "reasoning_steps": [
                    "Validated query scope",
                    "Retrieved relevant advisories",
                    "Generated answer from advisory data",
                ],
                "retrieval_attempts": 1,
                "trace_id": "abc123-def456-ghi789",
            }
        }


class FeedbackRequest(BaseModel):
    """Request model for user feedback on RAG answers."""

    trace_id: str = Field(..., description="Langfuse trace ID from the response")
    score: float = Field(..., description="Feedback score (0-1 or -1 to 1)", ge=-1, le=1)
    comment: Optional[str] = Field(None, description="Optional feedback comment", max_length=1000)

    class Config:
        json_schema_extra = {
            "example": {
                "trace_id": "abc123-def456-ghi789",
                "score": 1.0,
                "comment": "This answer was very helpful and accurate!",
            }
        }


class FeedbackResponse(BaseModel):
    """Response model for feedback submission."""

    success: bool = Field(..., description="Whether feedback was recorded successfully")
    message: str = Field(..., description="Status message")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Feedback recorded successfully",
            }
        }
