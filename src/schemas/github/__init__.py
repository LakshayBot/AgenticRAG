"""GitHub Security Advisories schemas"""

from .advisory import (
    CWEInfo,
    CVSSScore,
    GitHubAdvisory,
    VulnerabilityInfo,
    VulnerabilityPackage,
)

__all__ = [
    "VulnerabilityPackage",
    "VulnerabilityInfo",
    "CWEInfo",
    "CVSSScore",
    "GitHubAdvisory",
]
