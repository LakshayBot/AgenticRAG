"""Factory functions for GitHub service"""

from src.config import Settings, get_settings

from .client import GitHubAdvisoriesClient


def make_github_client(settings: Settings = None) -> GitHubAdvisoriesClient:
    """Factory function to create GitHubAdvisoriesClient"""
    if settings is None:
        settings = get_settings()

    return GitHubAdvisoriesClient(settings.github)
