import json
import logging

from langchain_core.tools import tool

from src.services.embeddings.jina_client import JinaEmbeddingsClient
from src.services.opensearch.client import OpenSearchClient

logger = logging.getLogger(__name__)


def create_retriever_tool(
    opensearch_client: OpenSearchClient,
    embeddings_client: JinaEmbeddingsClient,
    top_k: int = 3,
    use_hybrid: bool = True,
):
    """Create a retriever tool that wraps OpenSearch service.

    :param opensearch_client: Existing OpenSearch service
    :param embeddings_client: Existing Jina embeddings service
    :param top_k: Number of chunks to retrieve
    :param use_hybrid: Use hybrid search (BM25 + vector)
    :returns: LangChain tool for retrieving papers
    """

    @tool
    async def retrieve_papers(query: str, file_ids: list = None, advisory_ids: list = None) -> str:
        """Search and return relevant documents from GitHub Security Advisories or uploaded PDFs.

        Use this tool when the user asks about:
        - Security vulnerabilities or advisories
        - CVEs, GHSA identifiers, or affected packages
        - Severity ratings or CVSS scores
        - Content from uploaded PDF documents

        :param query: The search query describing what to find
        :param file_ids: Optional list of file IDs to filter search (e.g., ["upload-abc123"])
        :param advisory_ids: Optional list of GHSA IDs to filter search (e.g., ["GHSA-xxxx-yyyy-zzzz"])
        :returns: JSON string containing a list of document objects with page_content and metadata
        """
        logger.info(f"Retrieving documents for query: {query[:100]}...")
        if file_ids:
            logger.info(f"Filtering by file IDs: {file_ids}")
        if advisory_ids:
            logger.info(f"Filtering by advisory IDs: {advisory_ids}")
        logger.debug(f"Search mode: {'hybrid' if use_hybrid else 'bm25'}, top_k: {top_k}")

        # For advisory queries, fetch all chunks for the advisory directly.
        if advisory_ids:
            logger.debug("Fetching all chunks for advisory/advisories — skipping relevance search")
            hits = []
            for ghsa_id in advisory_ids:
                chunks = opensearch_client.get_chunks_by_advisory(ghsa_id)
                hits.extend(chunks[:top_k])
            search_results = {"hits": hits[:top_k], "total": len(hits)}
        # For uploaded PDF queries, fetch all chunks for the file(s) directly.
        elif file_ids:
            logger.debug("Fetching all chunks for uploaded file(s) — skipping relevance search")
            hits = []
            for fid in file_ids:
                chunks = opensearch_client.get_chunks_by_upload(fid)
                hits.extend(chunks[:top_k])
            search_results = {"hits": hits[:top_k], "total": len(hits)}
        else:
            # Generate query embedding for hybrid search, fall back to BM25 if it fails
            query_embedding = None
            try:
                logger.debug("Generating query embedding")
                query_embedding = await embeddings_client.embed_query(query)
                logger.debug(f"Generated embedding with {len(query_embedding)} dimensions")
            except Exception as emb_err:
                logger.warning(f"Embedding failed ({emb_err}), falling back to BM25-only search")

            # Search using OpenSearch
            logger.debug("Searching OpenSearch")
            search_results = opensearch_client.search_unified(
                query=query,
                query_embedding=query_embedding,
                size=top_k,
                use_hybrid=use_hybrid and query_embedding is not None,
                source_ids=None,
            )

        # Convert hits to JSON-serializable dicts (LangChain ToolNode serialises
        # List[Document] as Python repr, breaking downstream JSON parsing).
        result_docs = []
        hits = search_results.get("hits", [])
        logger.info(f"Found {len(hits)} documents from OpenSearch")

        for hit in hits:
            # Field is 'content' for uploaded docs, 'chunk_text' for advisory docs
            page_content = hit.get("content") or hit.get("chunk_text", "")
            # Advisory chunks use ghsa_id, upload chunks use source_id
            source_id = hit.get("source_id") or hit.get("ghsa_id", "")
            result_docs.append(
                {
                    "page_content": page_content,
                    "metadata": {
                        "source_id": source_id,
                        "title": hit.get("title", ""),
                        "authors": hit.get("authors", ""),
                        "score": float(hit.get("score", 0.0)),
                        "section": hit.get("section_name", ""),
                        "search_mode": "hybrid" if use_hybrid else "bm25",
                        "top_k": top_k,
                    },
                }
            )

        logger.debug(f"Converted {len(result_docs)} hits to serialisable dicts")
        logger.info(f"✓ Retrieved {len(result_docs)} documents successfully")

        return json.dumps(result_docs)

    return retrieve_papers
