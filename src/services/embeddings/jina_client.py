import asyncio
import logging
from typing import List

import httpx
from src.schemas.embeddings.jina import JinaEmbeddingRequest, JinaEmbeddingResponse

logger = logging.getLogger(__name__)

_MAX_RETRIES = 2
_RETRY_BASE_DELAY = 1.0  # seconds; doubles on each attempt, capped at 5s
_MAX_RETRY_DELAY = 5.0


async def _with_retry(coro_fn, max_retries: int = _MAX_RETRIES, base_delay: float = _RETRY_BASE_DELAY):
    """Call an async function with exponential backoff on 429 Too Many Requests."""
    for attempt in range(max_retries + 1):
        try:
            return await coro_fn()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429 and attempt < max_retries:
                retry_after = e.response.headers.get("Retry-After")
                delay = min(float(retry_after) if retry_after else base_delay * (2 ** attempt), _MAX_RETRY_DELAY)
                logger.warning(f"Jina rate limit hit (429). Attempt {attempt + 1}/{max_retries}. Retrying in {delay:.1f}s...")
                await asyncio.sleep(delay)
            else:
                raise
    raise RuntimeError("Retry loop exhausted without raising")


class JinaEmbeddingsClient:
    """Client for Jina AI embeddings API.

    Uses Jina embeddings v3 model with 1024 dimensions optimized for retrieval.
    Documentation: https://jina.ai/embeddings
    """

    def __init__(self, api_key: str, base_url: str = "https://api.jina.ai/v1"):
        """Initialize Jina embeddings client.

        :param api_key: Jina API key
        :param base_url: API base URL
        """
        self.api_key = api_key
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        self.client = httpx.AsyncClient(timeout=10.0)
        logger.info("Jina embeddings client initialized")

    async def embed_passages(self, texts: List[str], batch_size: int = 100) -> List[List[float]]:
        """Embed text passages for indexing.

        :param texts: List of text passages to embed
        :param batch_size: Number of texts to process in each API call
        :returns: List of embedding vectors
        """
        embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]

            request_data = JinaEmbeddingRequest(
                model="jina-embeddings-v3", task="retrieval.passage", dimensions=1024, input=batch
            )

            async def _call_batch():
                response = await self.client.post(
                    f"{self.base_url}/embeddings", headers=self.headers, json=request_data.model_dump()
                )
                response.raise_for_status()
                result = JinaEmbeddingResponse(**response.json())
                return [item["embedding"] for item in result.data]

            try:
                batch_embeddings = await _with_retry(_call_batch)
                embeddings.extend(batch_embeddings)
                logger.debug(f"Embedded batch of {len(batch)} passages")
            except httpx.HTTPError as e:
                logger.error(f"Error embedding passages: {e}")
                raise
            except Exception as e:
                logger.error(f"Unexpected error in embed_passages: {e}")
                raise

        logger.info(f"Successfully embedded {len(texts)} passages")
        return embeddings

    async def embed_query(self, query: str) -> List[float]:
        """Embed a search query.

        :param query: Query text to embed
        :returns: Embedding vector for the query
        """
        request_data = JinaEmbeddingRequest(model="jina-embeddings-v3", task="retrieval.query", dimensions=1024, input=[query])

        async def _call_query():
            response = await self.client.post(f"{self.base_url}/embeddings", headers=self.headers, json=request_data.model_dump())
            response.raise_for_status()
            result = JinaEmbeddingResponse(**response.json())
            return result.data[0]["embedding"]

        try:
            embedding = await _with_retry(_call_query)
            logger.debug(f"Embedded query: '{query[:50]}...'")
            return embedding
        except httpx.HTTPError as e:
            logger.error(f"Error embedding query: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in embed_query: {e}")
            raise

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
