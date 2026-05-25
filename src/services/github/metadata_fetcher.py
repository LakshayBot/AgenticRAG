"""GitHub Advisory metadata fetcher service."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from src.config import Settings
from src.exceptions import PipelineException
from src.schemas.github.advisory import GitHubAdvisory
from src.services.github.client import GitHubAdvisoriesClient

logger = logging.getLogger(__name__)


class GitHubAdvisoryFetcher:
    """Service for fetching GitHub Security Advisories and storing to database."""

    def __init__(
        self,
        github_client: GitHubAdvisoriesClient,
        settings: Optional[Settings] = None,
    ):
        """Initialize GitHub advisory fetcher.

        Args:
            github_client: Client for GitHub Security Advisories API
            settings: Application settings instance
        """
        from src.config import get_settings

        self.github_client = github_client
        self.settings = settings or get_settings()

    async def fetch_and_store_advisories(
        self,
        max_results: Optional[int] = None,
        severity: Optional[str] = None,
        ecosystem: Optional[str] = None,
        modified_since: Optional[str] = None,
        store_to_db: bool = True,
        db_session: Optional[Session] = None,
    ) -> Dict[str, Any]:
        """Fetch advisories from GitHub and store to database.

        Args:
            max_results: Maximum advisories to fetch (None for all available)
            severity: Filter by severity (critical, high, medium, low)
            ecosystem: Filter by ecosystem (npm, pip, go, etc.)
            modified_since: Filter advisories modified since date (ISO 8601)
            store_to_db: Whether to store results in database
            db_session: Database session (required if store_to_db=True)

        Returns:
            Dictionary with processing results and statistics:
            {
                "advisories_fetched": int,
                "advisories_stored": int,
                "advisories_updated": int,
                "advisories_new": int,
                "errors": List[str],
                "processing_time": float,
                "severity_breakdown": Dict[str, int],
                "ecosystem_breakdown": Dict[str, int]
            }

        Raises:
            PipelineException: If pipeline execution fails
        """
        results = {
            "advisories_fetched": 0,
            "advisories_stored": 0,
            "advisories_updated": 0,
            "advisories_new": 0,
            "errors": [],
            "processing_time": 0,
            "severity_breakdown": {},
            "ecosystem_breakdown": {},
        }

        start_time = datetime.now()

        try:
            # Step 1: Fetch advisories from GitHub API
            logger.info(
                f"Fetching advisories from GitHub API (max_results={max_results}, "
                f"severity={severity}, ecosystem={ecosystem})"
            )

            advisories = await self.github_client.fetch_advisories(
                max_results=max_results,
                severity=severity,
                ecosystem=ecosystem,
                modified_since=modified_since,
            )

            results["advisories_fetched"] = len(advisories)

            if not advisories:
                logger.warning("No advisories found")
                return results

            # Calculate severity and ecosystem breakdowns
            results["severity_breakdown"] = self._calculate_severity_breakdown(advisories)
            results["ecosystem_breakdown"] = self._calculate_ecosystem_breakdown(advisories)

            # Step 2: Store to database if requested
            if store_to_db and db_session:
                logger.info(f"Storing {len(advisories)} advisories to database...")
                storage_results = self._store_advisories_to_db(advisories, db_session)
                results["advisories_stored"] = storage_results["stored"]
                results["advisories_updated"] = storage_results["updated"]
                results["advisories_new"] = storage_results["new"]
                results["errors"].extend(storage_results["errors"])
            elif store_to_db:
                logger.warning("Database storage requested but no session provided")
                results["errors"].append("Database session not provided for storage")

            # Calculate total processing time
            processing_time = (datetime.now() - start_time).total_seconds()
            results["processing_time"] = processing_time

            # Log summary
            logger.info(
                f"GitHub advisory fetch completed in {processing_time:.1f}s: "
                f"{results['advisories_fetched']} fetched, "
                f"{results['advisories_new']} new, "
                f"{results['advisories_updated']} updated, "
                f"{len(results['errors'])} errors"
            )

            if results["errors"]:
                logger.warning("Errors encountered during processing:")
                for i, error in enumerate(results["errors"][:5], 1):
                    logger.warning(f"  {i}. {error}")
                if len(results["errors"]) > 5:
                    logger.warning(f"  ... and {len(results['errors']) - 5} more errors")

            return results

        except Exception as e:
            logger.error(f"GitHub advisory pipeline error: {e}", exc_info=True)
            results["errors"].append(f"Pipeline error: {str(e)}")
            raise PipelineException(f"GitHub advisory pipeline failed: {e}") from e

    def _store_advisories_to_db(
        self, advisories: List[GitHubAdvisory], session: Session
    ) -> Dict[str, Any]:
        """Store advisories to PostgreSQL database.

        Args:
            advisories: List of GitHub advisories to store
            session: Database session

        Returns:
            Dictionary with storage statistics:
            {
                "stored": int,
                "new": int,
                "updated": int,
                "errors": List[str]
            }
        """
        try:
            repository = AdvisoryRepository(session)
            stored = 0
            new_count = 0
            updated_count = 0
            errors = []

            for advisory in advisories:
                try:
                    # Check if advisory already exists
                    existing = repository.get_by_ghsa_id(advisory.ghsa_id)
                    is_new = existing is None

                    # Upsert advisory
                    repository.upsert(advisory)
                    stored += 1

                    if is_new:
                        new_count += 1
                    else:
                        updated_count += 1

                except Exception as e:
                    error_msg = f"Failed to store advisory {advisory.ghsa_id}: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
                    continue

            # Commit all changes
            session.commit()
            logger.info(
                f"Successfully stored {stored} advisories "
                f"({new_count} new, {updated_count} updated)"
            )

            return {
                "stored": stored,
                "new": new_count,
                "updated": updated_count,
                "errors": errors,
            }

        except Exception as e:
            session.rollback()
            logger.error(f"Database storage failed: {e}", exc_info=True)
            raise

    async def fetch_advisories(
        self,
        max_results: Optional[int] = None,
        severity: Optional[str] = None,
        ecosystem: Optional[str] = None,
        modified_since: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Fetch advisories from GitHub API and return as plain data (no DB operations).

        Returns:
            Dictionary with 'advisories' list and breakdown stats.
        """
        advisories = await self.github_client.fetch_advisories(
            max_results=max_results,
            severity=severity,
            ecosystem=ecosystem,
            from_date=modified_since,  # client uses from_date, not modified_since
        )

        advisory_dicts = []
        for advisory in advisories:
            # Pydantic models: use model_dump(); also expose computed properties
            base = advisory.model_dump()
            base["affected_ecosystems"] = advisory.affected_ecosystems
            base["affected_packages"] = advisory.affected_packages
            base["cvss_score"] = advisory.cvss_score
            base["github_url"] = advisory.html_url
            base["reference_urls"] = advisory.references
            # Flatten CWE ids list for .NET compatibility
            base["cwe_ids"] = [c.cwe_id for c in advisory.cwes]
            # Serialise datetimes to ISO strings
            for dt_field in ("published_at", "updated_at", "withdrawn_at"):
                if base.get(dt_field) is not None:
                    base[dt_field] = base[dt_field].isoformat()
            advisory_dicts.append(base)

        return {
            "advisories": advisory_dicts,
            "advisories_fetched": len(advisory_dicts),
            "severity_breakdown": self._calculate_severity_breakdown(advisories),
            "ecosystem_breakdown": self._calculate_ecosystem_breakdown(advisories),
        }

    def _calculate_severity_breakdown(self, advisories: List[GitHubAdvisory]) -> Dict[str, int]:
        """Calculate advisory count by severity level.

        Args:
            advisories: List of GitHub advisories

        Returns:
            Dictionary mapping severity to count
        """
        breakdown = {}
        for advisory in advisories:
            severity = advisory.severity.lower() if advisory.severity else "unknown"
            breakdown[severity] = breakdown.get(severity, 0) + 1
        return breakdown

    def _calculate_ecosystem_breakdown(self, advisories: List[GitHubAdvisory]) -> Dict[str, int]:
        """Calculate advisory count by ecosystem.

        Args:
            advisories: List of GitHub advisories

        Returns:
            Dictionary mapping ecosystem to count
        """
        breakdown = {}
        for advisory in advisories:
            ecosystems = advisory.affected_ecosystems
            for ecosystem in ecosystems:
                breakdown[ecosystem] = breakdown.get(ecosystem, 0) + 1
        return breakdown
