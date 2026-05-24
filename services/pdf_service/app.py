"""
PDF Processing Microservice
Port: 8001
Purpose: Extract text and metadata from PDF files using Docling
"""
import os
import logging
from pathlib import Path
from typing import Dict, Any, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Import from shared src directory
import sys
sys.path.append('/app/src')
sys.path.append('/app')

from src.services.pdf_parser.docling import DoclingParser
from src.config import get_settings

# Initialize settings
settings = get_settings()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Response Models
class HealthResponse(BaseModel):
    status: str
    service: str
    version: str

class ParsedPDFResponse(BaseModel):
    text: str
    metadata: Dict[str, Any]
    chunks: List[str]  # List of text chunks
    page_count: int
    success: bool

# Service instance
pdf_parser: DoclingParser = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup service resources"""
    global pdf_parser
    
    logger.info("Initializing PDF Processing Service...")
    try:
        # Get settings from environment or defaults
        max_pages = int(os.getenv("PDF_PARSER__MAX_PAGES", "30"))
        max_file_size_mb = int(os.getenv("PDF_PARSER__MAX_FILE_SIZE_MB", "20"))
        do_ocr = os.getenv("PDF_PARSER__DO_OCR", "false").lower() == "true"
        do_table_structure = os.getenv("PDF_PARSER__DO_TABLE_STRUCTURE", "true").lower() == "true"
        
        pdf_parser = DoclingParser(
            max_pages=max_pages,
            max_file_size_mb=max_file_size_mb,
            do_ocr=do_ocr,
            do_table_structure=do_table_structure
        )
        logger.info("PDF Processing Service initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize service: {e}")
        raise
    
    yield
    
    logger.info("Shutting down PDF Processing Service...")

# FastAPI application
app = FastAPI(
    title="PDF Processing Service",
    description="Microservice for parsing PDF documents using Docling",
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        service="pdf-processing",
        version="1.0.0"
    )

@app.post("/api/v1/parse-pdf", response_model=ParsedPDFResponse)
async def parse_pdf_endpoint(file: UploadFile = File(...)):
    """
    Parse a PDF file and extract text, metadata, and chunks
    
    Args:
        file: PDF file upload
        
    Returns:
        Parsed PDF data with text, metadata, and chunks
    """
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    try:
        # Read file content
        content = await file.read()
        
        # Save temporarily
        temp_path = Path(f"/tmp/{file.filename}")
        temp_path.write_bytes(content)
        
        # Parse PDF
        logger.info(f"Parsing PDF: {file.filename}")
        pdf_content = await pdf_parser.parse_pdf(temp_path)
        
        if pdf_content is None:
            raise HTTPException(status_code=400, detail="PDF validation failed or file is too large")
        
        # Extract sections as chunks - return just the content text
        chunks = []
        for section in pdf_content.sections:
            # Combine title and content for better context
            chunk_text = f"{section.title}\n{section.content}" if section.title else section.content
            chunks.append(chunk_text)
        
        # Clean up temp file
        temp_path.unlink(missing_ok=True)
        
        return ParsedPDFResponse(
            text=pdf_content.raw_text,
            metadata=pdf_content.metadata or {},
            chunks=chunks,
            page_count=len(pdf_content.sections),
            success=True
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error parsing PDF {file.filename}: {e}", exc_info=True)
        # Clean up temp file on error
        try:
            temp_path.unlink(missing_ok=True)
        except:
            pass
        raise HTTPException(status_code=500, detail=f"Failed to parse PDF: {str(e)}")

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "PDF Processing Service",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "parse": "/api/v1/parse-pdf"
        }
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("SERVICE_PORT", 8001))
    uvicorn.run(app, host="0.0.0.0", port=port)
