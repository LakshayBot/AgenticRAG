"""Advisory Service — FastAPI entrypoint.

Thin wrapper that mounts the advisory router from the shared src/ library.
Handles GitHub Security Advisory fetching, chunking, embedding and OpenSearch indexing.
Called by the .NET backend (AdvisoryServiceClient).
"""

import logging

from fastapi import FastAPI

from src.routers.advisories import router as advisories_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="CyberGuard Advisory Service",
    description="GitHub Security Advisory fetch, chunk, embed and index service",
    version="1.0.0",
)

app.include_router(advisories_router)


@app.on_event("startup")
async def startup():
    logger.info("Advisory service started on port 8005")


@app.on_event("shutdown")
async def shutdown():
    logger.info("Advisory service shutting down")
