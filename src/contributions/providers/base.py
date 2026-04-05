"""Base provider protocol for contribution data sources."""

from typing import Protocol, runtime_checkable

from contributions.models import Contribution, RepoSummary, UserProfile


@runtime_checkable
class ContributionProvider(Protocol):
    """Protocol that all contribution data sources must implement."""

    async def get_profile(self, username: str) -> UserProfile: ...

    async def get_repos(self, username: str) -> list[RepoSummary]: ...

    async def get_contributions(self, username: str) -> list[Contribution]: ...
