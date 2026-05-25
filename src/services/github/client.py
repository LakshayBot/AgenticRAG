"""GitHub Security Advisories API Client

Documentation: https://docs.github.com/en/rest/security-advisories/global-advisories
"""

import asyncio
import logging
from datetime import datetime
from typing import List, Optional

import httpx

from src.config import GitHubSettings
from src.exceptions import GitHubAPIException, GitHubAPITimeoutError, GitHubRateLimitError
from src.schemas.github.advisory import GitHubAdvisory

logger = logging.getLogger(__name__)


class GitHubAdvisoriesClient:
    """Client for GitHub Security Advisories API"""

    def __init__(self, settings: GitHubSettings):
        self._settings = settings
        self._last_request_time: Optional[float] = None

    @property
    def headers(self) -> dict:
        """Build request headers"""
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        if self._settings.api_token:
            headers["Authorization"] = f"Bearer {self._settings.api_token}"

        return headers

    async def _rate_limit_delay(self):
        """Enforce rate limiting between requests"""
        if self._last_request_time:
            elapsed = datetime.now().timestamp() - self._last_request_time
            delay_needed = self._settings.rate_limit_delay - elapsed

            if delay_needed > 0:
                logger.debug(f"Rate limiting: waiting {delay_needed:.2f}s")
                await asyncio.sleep(delay_needed)

        self._last_request_time = datetime.now().timestamp()

    async def fetch_advisories(
        self,
        max_results: Optional[int] = None,
        from_date: Optional[str] = None,  # YYYY-MM-DD
        to_date: Optional[str] = None,
        severity: Optional[str] = None,  # Comma-separated: "high,critical"
        ecosystem: Optional[str] = None,  # Comma-separated: "npm,pip"
        type: str = "reviewed",
    ) -> List[GitHubAdvisory]:
        """
        Fetch advisories from GitHub API with pagination

        Args:
            max_results: Maximum number of advisories to fetch (None = all)
            from_date: Filter published date >= this (YYYY-MM-DD)
            to_date: Filter published date <= this (YYYY-MM-DD)
            severity: Filter by severity (comma-separated)
            ecosystem: Filter by ecosystem (comma-separated)
            type: Advisory type (reviewed, malware, unreviewed)

        Returns:
            List of GitHubAdvisory objects

        Raises:
            GitHubAPIException: On API errors
            GitHubRateLimitError: On rate limit (429)
        """
        advisories = []
        url = f"{self._settings.base_url}/advisories"

        # Build query parameters
        params = {
            "per_page": self._settings.per_page,
            "sort": "published",
            "direction": "desc",
            "type": type,
        }

        # Add filters
        if severity:
            params["severity"] = severity
        if ecosystem:
            params["ecosystem"] = ecosystem
        if from_date and to_date:
            params["published"] = f"{from_date}..{to_date}"
        elif from_date:
            params["published"] = f">={from_date}"
        elif to_date:
            params["published"] = f"<={to_date}"

        page_count = 0

        async with httpx.AsyncClient(timeout=self._settings.timeout_seconds) as client:
            while True:
                await self._rate_limit_delay()

                try:
                    logger.info(f"Fetching advisories page {page_count + 1}")
                    response = await client.get(url, headers=self.headers, params=params)

                    # Handle rate limiting
                    if response.status_code == 429:
                        retry_after = int(response.headers.get("Retry-After", 60))
                        logger.warning(f"Rate limited! Waiting {retry_after}s")
                        await asyncio.sleep(retry_after)
                        continue

                    response.raise_for_status()
                    data = response.json()

                    if not data:
                        logger.info("No more advisories to fetch")
                        break

                    # Parse advisories
                    for item in data:
                        try:
                            advisory = self._parse_advisory(item)
                            advisories.append(advisory)

                            # Check max_results limit
                            if max_results and len(advisories) >= max_results:
                                logger.info(f"Reached max_results limit: {max_results}")
                                return advisories[:max_results]

                        except Exception as e:
                            logger.error(f"Failed to parse advisory: {e}")
                            continue

                    logger.info(f"Fetched {len(data)} advisories (total: {len(advisories)})")

                    # Check pagination
                    link_header = response.headers.get("Link", "")
                    if 'rel="next"' not in link_header:
                        logger.info("No more pages")
                        break

                    next_url = self._extract_next_url(link_header)
                    if not next_url:
                        break

                    url = next_url
                    params = {}  # Clear params for next page
                    page_count += 1

                    # Safety check: max pages
                    if page_count >= self._settings.max_pages:
                        logger.warning(f"Reached max_pages limit: {self._settings.max_pages}")
                        break

                except httpx.TimeoutException as e:
                    logger.error(f"Timeout fetching advisories: {e}")
                    raise GitHubAPITimeoutError(f"GitHub API timeout: {e}")

                except httpx.HTTPStatusError as e:
                    logger.error(f"HTTP error fetching advisories: {e.response.status_code}")
                    raise GitHubAPIException(f"GitHub API error: {e}")

                except Exception as e:
                    logger.error(f"Unexpected error fetching advisories: {e}")
                    raise GitHubAPIException(f"Failed to fetch advisories: {e}")

        logger.info(f"✓ Fetched {len(advisories)} advisories total")
        return advisories

    def _parse_advisory(self, data: dict) -> GitHubAdvisory:
        """Parse raw API response into GitHubAdvisory model"""
        try:
            # Extract CVSS if available
            cvss_data = None
            if data.get("cvss") and isinstance(data.get("cvss"), dict):
                # Only create CVSS object if we have both required fields
                vector_str = data["cvss"].get("vector_string")
                score = data["cvss"].get("score")
                if vector_str and score is not None:
                    cvss_data = {
                        "vector_string": vector_str,
                        "score": score,
                    }

            # Parse vulnerabilities
            vulnerabilities = []
            for vuln in data.get("vulnerabilities", []):
                pkg = vuln.get("package", {})
                vulnerabilities.append(
                    {
                        "package": {
                            "ecosystem": pkg.get("ecosystem", "unknown"),
                            "name": pkg.get("name", "unknown"),
                        },
                        "vulnerable_version_range": vuln.get("vulnerable_version_range", ""),
                        "first_patched_version": vuln.get("first_patched_version"),
                        "vulnerable_functions": vuln.get("vulnerable_functions", []),
                    }
                )

            # Parse CWEs
            cwes = [
                {"cwe_id": cwe.get("cwe_id", ""), "name": cwe.get("name", "")}
                for cwe in data.get("cwes", [])
            ]

            return GitHubAdvisory(
                ghsa_id=data["ghsa_id"],
                cve_id=data.get("cve_id"),
                summary=data["summary"],
                description=data["description"],
                severity=data.get("severity", "unknown"),
                cvss=cvss_data,
                type=data["type"],
                published_at=datetime.fromisoformat(data["published_at"].replace("Z", "+00:00")),
                updated_at=datetime.fromisoformat(data["updated_at"].replace("Z", "+00:00")),
                github_reviewed_at=(
                    datetime.fromisoformat(data["github_reviewed_at"].replace("Z", "+00:00"))
                    if data.get("github_reviewed_at")
                    else None
                ),
                nvd_published_at=(
                    datetime.fromisoformat(data["nvd_published_at"].replace("Z", "+00:00"))
                    if data.get("nvd_published_at")
                    else None
                ),
                withdrawn_at=(
                    datetime.fromisoformat(data["withdrawn_at"].replace("Z", "+00:00"))
                    if data.get("withdrawn_at")
                    else None
                ),
                vulnerabilities=vulnerabilities,
                cwes=cwes,
                references=data.get("references", []),
                url=data["url"],
                html_url=data["html_url"],
                source_code_location=data.get("source_code_location"),
            )

        except KeyError as e:
            raise GitHubAPIException(f"Missing required field in API response: {e}")
        except Exception as e:
            raise GitHubAPIException(f"Failed to parse advisory: {e}")

    def _extract_next_url(self, link_header: str) -> Optional[str]:
        """Extract next page URL from Link header

        Example header:
        <https://api.github.com/advisories?after=cursor>; rel="next", <...>; rel="last"
        """
        parts = link_header.split(",")
        for part in parts:
            if 'rel="next"' in part:
                url = part.split(";")[0].strip()
                return url.strip("<>")
        return None

    async def fetch_advisory_by_id(self, ghsa_id: str) -> Optional[GitHubAdvisory]:
        """Fetch a single advisory by GHSA ID"""
        url = f"{self._settings.base_url}/advisories/{ghsa_id}"

        await self._rate_limit_delay()

        async with httpx.AsyncClient(timeout=self._settings.timeout_seconds) as client:
            try:
                response = await client.get(url, headers=self.headers)

                if response.status_code == 404:
                    logger.warning(f"Advisory not found: {ghsa_id}")
                    return None

                response.raise_for_status()
                data = response.json()

                return self._parse_advisory(data)

            except httpx.HTTPStatusError as e:
                logger.error(f"Error fetching advisory {ghsa_id}: {e}")
                return None
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                return None
