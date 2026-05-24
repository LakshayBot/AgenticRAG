"""
Embeddings Generation Microservice
Port: 8002
Purpose: Generate vector embeddings for text using Jina AI
"""
import os
import logging
from typing import List, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Import from shared src directory
import sys
sys.path.append('/app/src')
sys.path.append('/app')

from src.services.embeddings.jina_client import JinaEmbeddingsClient
from src.config import get_settings

# Initialize settings
settings = get_settings()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Request/Response Models
class HealthResponse(BaseModel):
    status: str
    service: str
    version: str

class EmbedRequest(BaseModel):
    texts: List[str]
    model: str = "jina-embeddings-v3"

class EmbedResponse(BaseModel):
    embeddings: List[List[float]]
    dimensions: int
    model: str
    count: int

class EmbedSingleRequest(BaseModel):
    text: str
    model: str = "jina-embeddings-v3"

class EmbedSingleResponse(BaseModel):
    embedding: List[float]
    dimensions: int
    model: str

# Service instance
jina_client: JinaEmbeddingsClient = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup service resources"""
    global jina_client
    
    logger.info("Initializing Embeddings Service...")
    try:
        # Get Jina API key from environment
        api_key = os.getenv("JINA_API_KEY", "")
        if not api_key:
            logger.warning("JINA_API_KEY not set! Service will fail on actual requests.")
        
        jina_client = JinaEmbeddingsClient(api_key=api_key)
        logger.info("Embeddings Service initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize service: {e}")
        raise
    
    yield
    
    logger.info("Shutting down Embeddings Service...")
    if jina_client and hasattr(jina_client, 'client'):
        await jina_client.client.aclose()

# FastAPI application
app = FastAPI(
    title="Embeddings Generation Service",
    description="Microservice for generating vector embeddings using Jina AI",
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        service="embeddings-generation",
        version="1.0.0"
    )

@app.post("/api/v1/embed", response_model=EmbedResponse)
async def embed_texts(request: EmbedRequest):
    """
    Generate embeddings for multiple texts (batch)
    
    Args:
        request: List of texts to embed
        
    Returns:
        List of embedding vectors
    """
    try:
        logger.info(f"Generating embeddings for {len(request.texts)} texts")
        
        # Use passage embedding for indexing
        embeddings = await jina_client.embed_passages(
            texts=request.texts,
            batch_size=100
        )
        
        return EmbedResponse(
            embeddings=embeddings,
            dimensions=len(embeddings[0]) if len(embeddings) > 0 else 0,
            model=request.model,
            count=len(embeddings)
        )
        
    except Exception as e:
        logger.error(f"Error generating embeddings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate embeddings: {str(e)}")

@app.post("/api/v1/embed-single", response_model=EmbedSingleResponse)
async def embed_single_text(request: EmbedSingleRequest):
    """
    Generate embedding for a single text
    
    Args:
        request: Single text to embed
        
    Returns:
        Embedding vector
    """
    try:
        logger.info(f"Generating embedding for single text")
        
        # Use passage embedding for single text
        embeddings = await jina_client.embed_passages(
            texts=[request.text],
            batch_size=1
        )
        
        return EmbedSingleResponse(
            embedding=embeddings[0] if len(embeddings) > 0 else [],
            dimensions=len(embeddings[0]) if len(embeddings) > 0 else 0,
            model=request.model
        )
        
    except Exception as e:
        logger.error(f"Error generating embedding: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate embedding: {str(e)}")

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Embeddings Generation Service",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "embed_batch": "/api/v1/embed",
            "embed_single": "/api/v1/embed-single"
        }
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("SERVICE_PORT", 8002))
    uvicorn.run(app, host="0.0.0.0", port=port)
