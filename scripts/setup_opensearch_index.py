#!/usr/bin/env python3
"""Setup OpenSearch index for hybrid RAG system.

This creates a unified index that supports:
- GitHub Security Advisories (source_type=github_advisory)
- User Uploaded PDFs (source_type=uploaded)
"""

import logging
import os
import sys
from typing import Optional

from opensearchpy import OpenSearch

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# OpenSearch connection from environment
OPENSEARCH_HOST = os.getenv("OPENSEARCH_HOST", "localhost")
OPENSEARCH_PORT = int(os.getenv("OPENSEARCH_PORT", "9200"))
OPENSEARCH_USER = os.getenv("OPENSEARCH_USER", "admin")
OPENSEARCH_PASSWORD = os.getenv("OPENSEARCH_PASSWORD", "admin")
DEFAULT_INDEX_NAME = "security-rag-chunks"

# Unified index mapping for papers and advisories
HYBRID_INDEX_MAPPING = {
    "settings": {
        "index": {
            "knn": True,
            "knn.algo_param.ef_search": 100,
            "number_of_shards": 1,
            "number_of_replicas": 1,
        },
        "analysis": {
            "analyzer": {
                "standard": {"type": "standard"},
            }
        },
    },
    "mappings": {
        "properties": {
            # ===== Source Type Discriminator =====
            "source_type": {
                "type": "keyword"  # Values: github_advisory, uploaded
            },
            # ===== Advisory-specific Fields =====
            "ghsa_id": {"type": "keyword"},
            "cve_id": {"type": "keyword"}, 
            "advisory_id": {"type": "keyword"},
            "severity": {"type": "keyword"},
            "cvss_score": {"type": "float"},
            "affected_ecosystems": {"type": "keyword"},
            "affected_packages": {"type": "keyword"},
            "cwe_ids": {"type": "keyword"},
            "withdrawn_at": {"type": "date"},
            # ===== Upload-specific Fields =====
            "source_id": {"type": "keyword"},
            "upload_id": {"type": "keyword"},
            "authors": {"type": "text"},
            "abstract": {"type": "text"},
            # ===== Common Chunk Fields =====
            "chunk_index": {"type": "integer"},
            "chunk_text": {
                "type": "text",
                "analyzer": "standard",
            },
            "chunk_word_count": {"type": "integer"},
            "start_char": {"type": "integer"},
            "end_char": {"type": "integer"},
            "section_title": {"type": "keyword"},
            # ===== Vector Embedding =====
            "embedding": {
                "type": "knn_vector",
                "dimension": 1024,  # Jina Embeddings v3 dimension
                "method": {
                    "name": "hnsw",
                    "engine": "nmslib",
                    "space_type": "cosinesimil",
                    "parameters": {
                        "ef_construction": 128,
                        "m": 24,
                    },
                },
            },
            "embedding_model": {"type": "keyword"},
            # ===== Common Metadata =====
            "title": {"type": "text"},
            "published_date": {"type": "date"},
            "updated_date": {"type": "date"},
            "timestamp": {"type": "date"},
        }
    },
}


def create_opensearch_client() -> OpenSearch:
    """Create OpenSearch client with connection settings."""
    return OpenSearch(
        hosts=[{"host": OPENSEARCH_HOST, "port": OPENSEARCH_PORT}],
        http_compress=True,
        http_auth=(OPENSEARCH_USER, OPENSEARCH_PASSWORD),
        use_ssl=False,
        verify_certs=False,
    )


def create_index(index_name: str = DEFAULT_INDEX_NAME, force: bool = False) -> bool:
    """Create OpenSearch index for hybrid RAG system.

    Args:
        index_name: Name of the index to create
        force: If True, delete existing index without prompting

    Returns:
        True if index was created successfully
    """
    try:
        client = create_opensearch_client()
        logger.info(f"Connected to OpenSearch at {OPENSEARCH_HOST}:{OPENSEARCH_PORT}")

        # Check if index exists
        if client.indices.exists(index=index_name):
            logger.warning(f"Index '{index_name}' already exists")

            if not force:
                response = input("Delete and recreate? (yes/no): ")
                if response.lower() != "yes":
                    logger.info("Aborted - index not modified")
                    return False

            # Delete existing index
            client.indices.delete(index=index_name)
            logger.info(f"✓ Deleted existing index '{index_name}'")

        # Create index with mapping
        client.indices.create(index=index_name, body=HYBRID_INDEX_MAPPING)
        logger.info(f"✓ Created index '{index_name}' with hybrid mapping")

        # Verify mapping
        mapping = client.indices.get_mapping(index=index_name)
        properties_count = len(mapping[index_name]["mappings"]["properties"])
        logger.info(f"✓ Index mapping verified ({properties_count} properties)")

        # Display summary
        logger.info("")
        logger.info("=" * 60)
        logger.info(f"Index '{index_name}' is ready for:")
        logger.info("  📊 GitHub Security Advisories (source_type=github_advisory)")
        logger.info("  📤 User Uploaded PDFs (source_type=uploaded)")
        logger.info("")
        logger.info("Vector Configuration:")
        logger.info("  - Dimension: 1024 (Jina Embeddings v3)")
        logger.info("  - Algorithm: HNSW (cosine similarity)")
        logger.info("  - ef_construction: 128, m: 24")
        logger.info("=" * 60)

        return True

    except Exception as e:
        logger.error(f"Failed to create index: {e}", exc_info=True)
        return False


def delete_index(index_name: str = DEFAULT_INDEX_NAME) -> bool:
    """Delete OpenSearch index.

    Args:
        index_name: Name of the index to delete

    Returns:
        True if index was deleted successfully
    """
    try:
        client = create_opensearch_client()

        if not client.indices.exists(index=index_name):
            logger.warning(f"Index '{index_name}' does not exist")
            return False

        client.indices.delete(index=index_name)
        logger.info(f"✓ Deleted index '{index_name}'")
        return True

    except Exception as e:
        logger.error(f"Failed to delete index: {e}", exc_info=True)
        return False


def verify_index(index_name: str = DEFAULT_INDEX_NAME) -> bool:
    """Verify OpenSearch index exists and has correct mapping.

    Args:
        index_name: Name of the index to verify

    Returns:
        True if index exists and is correctly configured
    """
    try:
        client = create_opensearch_client()

        if not client.indices.exists(index=index_name):
            logger.error(f"Index '{index_name}' does not exist")
            return False

        # Get mapping
        mapping = client.indices.get_mapping(index=index_name)
        properties = mapping[index_name]["mappings"]["properties"]

        # Check critical fields
        critical_fields = [
            "source_type",
            "chunk_text",
            "embedding",
            "ghsa_id",  # Advisory
            "source_id",  # Upload
        ]

        missing_fields = []
        for field in critical_fields:
            if field not in properties:
                missing_fields.append(field)

        if missing_fields:
            logger.error(f"Index missing critical fields: {missing_fields}")
            return False

        # Check embedding dimension
        embedding_config = properties.get("embedding", {})
        dimension = embedding_config.get("dimension")
        if dimension != 1024:
            logger.warning(f"Embedding dimension is {dimension}, expected 1024")

        # Get document count
        count = client.count(index=index_name)
        doc_count = count.get("count", 0)

        logger.info(f"✓ Index '{index_name}' verified")
        logger.info(f"  - Properties: {len(properties)}")
        logger.info(f"  - Documents: {doc_count}")
        logger.info(f"  - Embedding dimension: {dimension}")

        return True

    except Exception as e:
        logger.error(f"Failed to verify index: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Manage OpenSearch index for hybrid RAG system")
    parser.add_argument(
        "command",
        choices=["create", "delete", "verify"],
        help="Command to execute",
    )
    parser.add_argument(
        "--index",
        default=DEFAULT_INDEX_NAME,
        help=f"Index name (default: {DEFAULT_INDEX_NAME})",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force operation without confirmation",
    )

    args = parser.parse_args()

    if args.command == "create":
        success = create_index(args.index, args.force)
        sys.exit(0 if success else 1)
    elif args.command == "delete":
        if not args.force:
            response = input(f"Delete index '{args.index}'? (yes/no): ")
            if response.lower() != "yes":
                logger.info("Aborted")
                sys.exit(0)
        success = delete_index(args.index)
        sys.exit(0 if success else 1)
    elif args.command == "verify":
        success = verify_index(args.index)
        sys.exit(0 if success else 1)
