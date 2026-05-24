#!/usr/bin/env python3
"""Standalone script for scheduled GitHub Security Advisory ingestion.

This script can be run as a cron job to periodically fetch and index
GitHub Security Advisories. It provides the same functionality as the
FastAPI endpoint but can be executed independently.

Usage:
    # Fetch and index all critical advisories
    python scripts/ingest_advisories.py --severity critical

    # Fetch only npm ecosystem advisories
    python scripts/ingest_advisories.py --ecosystem npm

    # Fetch advisories modified in the last 24 hours
    python scripts/ingest_advisories.py --since "2024-01-15T00:00:00Z"

    # Dry run (fetch and store but don't index)
    python scripts/ingest_advisories.py --no-index

Cron Example:
    # Run daily at 6 AM to fetch critical advisories
    0 6 * * * /path/to/venv/bin/python /path/to/scripts/ingest_advisories.py --severity critical
"""

import argparse
import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import get_settings
from src.database import get_db_session
from src.repositories.advisory import AdvisoryRepository
from src.services.embeddings.jina_client import JinaEmbeddingsClient
from src.services.github import make_github_client, GitHubAdvisoryFetcher
from src.services.indexing.hybrid_indexer import HybridIndexingService
from src.services.indexing.text_chunker import TextChunker
from src.services.opensearch.client import OpenSearchClient

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def run_ingestion(
    max_results: int = None,
    severity: str = None,
    ecosystem: str = None,
    modified_since: str = None,
    index_to_opensearch: bool = True,
) -> dict:
    """Run the advisory ingestion pipeline.

    Args:
        max_results: Maximum advisories to fetch
        severity: Filter by severity
        ecosystem: Filter by ecosystem
        modified_since: Filter by modification date
        index_to_opensearch: Whether to index to OpenSearch

    Returns:
        Results dictionary with statistics
    """
    start_time = datetime.now()
    logger.info("=" * 80)
    logger.info("GitHub Security Advisories Ingestion - Starting")
    logger.info("=" * 80)

    settings = get_settings()

    try:
        # Step 1: Fetch and store advisories
        with get_db_session() as db_session:
            github_client = make_github_client(settings)
            fetcher = GitHubAdvisoryFetcher(github_client, settings)

            logger.info(
                f"Fetching advisories (max_results={max_results}, severity={severity}, "
                f"ecosystem={ecosystem}, modified_since={modified_since})"
            )

            fetch_results = await fetcher.fetch_and_store_advisories(
                max_results=max_results,
                severity=severity,
                ecosystem=ecosystem,
                modified_since=modified_since,
                store_to_db=True,
                db_session=db_session,
            )

            logger.info(
                f"✓ Fetched {fetch_results['advisories_fetched']} advisories, "
                f"stored {fetch_results['advisories_stored']} "
                f"({fetch_results['advisories_new']} new, {fetch_results['advisories_updated']} updated)"
            )

            total_indexed = 0
            total_chunks = 0
            indexing_errors = []

            # Step 2: Index to OpenSearch if requested
            if index_to_opensearch and fetch_results["advisories_stored"] > 0:
                logger.info(
                    f"Indexing {fetch_results['advisories_stored']} advisories to OpenSearch..."
                )

                try:
                    # Get advisories that were just stored
                    repository = AdvisoryRepository(db_session)
                    recent_advisories = repository.get_recent(
                        limit=fetch_results["advisories_stored"]
                    )

                    if recent_advisories:
                        # Initialize indexing services
                        chunker = TextChunker(
                            chunk_size=settings.chunking.chunk_size,
                            overlap_size=settings.chunking.overlap_size,
                            min_chunk_size=settings.chunking.min_chunk_size,
                        )
                        embeddings_client = JinaEmbeddingsClient(settings)
                        opensearch_client = OpenSearchClient(settings)
                        indexer = HybridIndexingService(
                            chunker, embeddings_client, opensearch_client
                        )

                        # Convert to dict format for indexer
                        advisories_data = [
                            {
                                "id": adv.id,
                                "ghsa_id": adv.ghsa_id,
                                "cve_id": adv.cve_id,
                                "summary": adv.summary,
                                "description": adv.description,
                                "severity": adv.severity,
                                "cvss_score": adv.cvss_score,
                                "affected_ecosystems": adv.affected_ecosystems,
                                "affected_packages": adv.affected_packages,
                                "cwe_ids": adv.cwe_ids,
                                "published_at": adv.published_at,
                                "updated_at": adv.updated_at,
                                "withdrawn_at": adv.withdrawn_at,
                            }
                            for adv in recent_advisories
                        ]

                        # Index advisories in batch
                        index_results = await indexer.index_advisories_batch(
                            advisories=advisories_data, replace_existing=True
                        )

                        total_indexed = index_results["total_chunks_indexed"]
                        total_chunks = index_results["total_chunks_created"]
                        
                        if index_results["total_errors"] > 0:
                            indexing_errors.append(
                                f"Indexing errors: {index_results['total_errors']} chunks failed"
                            )

                        logger.info(
                            f"✓ Indexed {index_results['advisories_processed']} advisories "
                            f"({total_chunks} chunks, {total_indexed} successful)"
                        )

                except Exception as e:
                    error_msg = f"OpenSearch indexing failed: {str(e)}"
                    logger.error(error_msg, exc_info=True)
                    indexing_errors.append(error_msg)

            # Calculate results
            processing_time = (datetime.now() - start_time).total_seconds()

            results = {
                "advisories_fetched": fetch_results["advisories_fetched"],
                "advisories_stored": fetch_results["advisories_stored"],
                "advisories_new": fetch_results["advisories_new"],
                "advisories_updated": fetch_results["advisories_updated"],
                "advisories_indexed": total_indexed,
                "chunks_created": total_chunks,
                "processing_time": processing_time,
                "severity_breakdown": fetch_results["severity_breakdown"],
                "ecosystem_breakdown": fetch_results["ecosystem_breakdown"],
                "errors": fetch_results["errors"] + indexing_errors,
            }

            # Print summary
            logger.info("=" * 80)
            logger.info(f"Ingestion completed in {processing_time:.1f}s:")
            logger.info(f"  Fetched: {results['advisories_fetched']} advisories")
            logger.info(
                f"  Stored: {results['advisories_stored']} "
                f"({results['advisories_new']} new, {results['advisories_updated']} updated)"
            )
            logger.info(f"  Indexed: {results['advisories_indexed']} chunks")
            logger.info(f"  Errors: {len(results['errors'])}")

            if results["severity_breakdown"]:
                logger.info("  Severity breakdown:")
                for severity, count in sorted(results["severity_breakdown"].items()):
                    logger.info(f"    {severity}: {count}")

            if results["ecosystem_breakdown"]:
                logger.info("  Ecosystem breakdown:")
                for ecosystem, count in sorted(
                    results["ecosystem_breakdown"].items(), key=lambda x: -x[1]
                )[:5]:
                    logger.info(f"    {ecosystem}: {count}")

            logger.info("=" * 80)

            return results

    except Exception as e:
        logger.error(f"Ingestion pipeline failed: {e}", exc_info=True)
        raise


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Fetch and index GitHub Security Advisories",
        epilog="Example: python scripts/ingest_advisories.py --severity critical --ecosystem npm",
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=None,
        help="Maximum number of advisories to fetch (default: no limit)",
    )
    parser.add_argument(
        "--severity",
        choices=["critical", "high", "medium", "low"],
        help="Filter by severity level",
    )
    parser.add_argument(
        "--ecosystem", help="Filter by ecosystem (e.g., npm, pip, go, maven, rubygems)"
    )
    parser.add_argument(
        "--since",
        help="Fetch advisories modified since this date (ISO 8601 format: YYYY-MM-DDTHH:MM:SSZ)",
    )
    parser.add_argument(
        "--no-index",
        action="store_true",
        help="Skip OpenSearch indexing (only fetch and store to database)",
    )

    args = parser.parse_args()

    try:
        # Run ingestion
        results = asyncio.run(
            run_ingestion(
                max_results=args.max_results,
                severity=args.severity,
                ecosystem=args.ecosystem,
                modified_since=args.since,
                index_to_opensearch=not args.no_index,
            )
        )

        # Exit with success if no errors
        if results.get("errors"):
            logger.warning(f"Completed with {len(results['errors'])} errors")
            sys.exit(1)
        else:
            logger.info("✓ Ingestion completed successfully")
            sys.exit(0)

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
