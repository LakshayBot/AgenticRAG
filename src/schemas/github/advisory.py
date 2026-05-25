"""GitHub Security Advisory Pydantic models"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class VulnerabilityPackage(BaseModel):
    """Affected package information"""

    ecosystem: str  # npm, pip, maven, nuget, etc.
    name: str


class VulnerabilityInfo(BaseModel):
    """Vulnerability details for a specific package"""

    package: VulnerabilityPackage
    vulnerable_version_range: str  # e.g., "<=4.17.20"
    first_patched_version: Optional[str] = None  # e.g., "4.17.21"
    vulnerable_functions: List[str] = Field(default_factory=list)


class CWEInfo(BaseModel):
    """Common Weakness Enumeration"""

    cwe_id: str  # e.g., "CWE-400"
    name: str  # e.g., "Uncontrolled Resource Consumption"


class CVSSScore(BaseModel):
    """CVSS scoring information"""

    vector_string: str  # e.g., "CVSS:3.1/AV:N/AC:H/PR:H/..."
    score: float  # e.g., 7.6


class GitHubAdvisory(BaseModel):
    """GitHub Security Advisory complete data model"""

    # Primary Identifiers
    ghsa_id: str  # GHSA-abcd-1234-efgh (GitHub's identifier)
    cve_id: Optional[str] = None  # CVE-2024-1234 (optional)

    # Content
    summary: str  # Short title
    description: str  # Full description (THIS IS WHAT WE EMBED)

    # Severity & Scoring
    severity: str  # low, medium, high, critical, unknown
    cvss: Optional[CVSSScore] = None

    # Classification
    type: str  # reviewed, malware, unreviewed

    # Timestamps
    published_at: datetime
    updated_at: datetime
    github_reviewed_at: Optional[datetime] = None
    nvd_published_at: Optional[datetime] = None
    withdrawn_at: Optional[datetime] = None

    # Vulnerability Details
    vulnerabilities: List[VulnerabilityInfo] = Field(default_factory=list)
    cwes: List[CWEInfo] = Field(default_factory=list)
    references: List[str] = Field(default_factory=list)

    # URLs
    url: str  # API URL
    html_url: str  # Human-readable URL
    source_code_location: Optional[str] = None

    @property
    def affected_ecosystems(self) -> List[str]:
        """Get list of unique affected ecosystems"""
        return list(set(v.package.ecosystem for v in self.vulnerabilities))

    @property
    def affected_packages(self) -> List[str]:
        """Get list of affected package names"""
        return [f"{v.package.ecosystem}:{v.package.name}" for v in self.vulnerabilities]

    @property
    def cvss_score(self) -> Optional[float]:
        """Get CVSS score if available"""
        return self.cvss.score if self.cvss else None

    @property
    def is_critical(self) -> bool:
        """Check if severity is critical"""
        return self.severity.lower() == "critical"

    @property
    def is_high_or_critical(self) -> bool:
        """Check if severity is high or critical"""
        return self.severity.lower() in ("high", "critical")
