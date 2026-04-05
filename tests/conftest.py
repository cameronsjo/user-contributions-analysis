"""Shared test fixtures."""

from datetime import UTC, datetime

import pytest

from contributions.models import (
    CommitContribution,
    ContributionSummary,
    IssueContribution,
    Provider,
    PullRequestContribution,
    RepoSummary,
    ReviewContribution,
    UserProfile,
)


@pytest.fixture
def sample_profile() -> UserProfile:
    return UserProfile(
        provider=Provider.GITHUB,
        username="testuser",
        display_name="Test User",
        bio="A developer",
        avatar_url="https://avatars.githubusercontent.com/u/12345",
        profile_url="https://github.com/testuser",
        public_repos=10,
        followers=50,
        following=20,
        created_at=datetime(2020, 1, 15, tzinfo=UTC),
    )


@pytest.fixture
def sample_contributions() -> list:
    base = {
        "provider": Provider.GITHUB,
        "repo_name": "testuser/myrepo",
        "repo_url": "https://github.com/testuser/myrepo",
    }
    return [
        CommitContribution(
            **base,
            timestamp=datetime(2026, 1, 10, tzinfo=UTC),
            sha="abc123",
            message="feat: add login",
        ),
        CommitContribution(
            **base,
            timestamp=datetime(2026, 1, 15, tzinfo=UTC),
            sha="def456",
            message="fix: login redirect",
        ),
        CommitContribution(
            **base,
            timestamp=datetime(2026, 2, 5, tzinfo=UTC),
            sha="ghi789",
            message="refactor: auth module",
        ),
        PullRequestContribution(
            **base,
            timestamp=datetime(2026, 1, 12, tzinfo=UTC),
            title="Add login flow",
            number=1,
            state="closed",
            merged=True,
        ),
        IssueContribution(
            **base,
            timestamp=datetime(2026, 1, 20, tzinfo=UTC),
            title="Bug in auth",
            number=5,
            state="closed",
            labels=["bug"],
        ),
        ReviewContribution(
            **base,
            timestamp=datetime(2026, 2, 1, tzinfo=UTC),
            pr_number=3,
            pr_title="Update docs",
            state="approved",
        ),
    ]


@pytest.fixture
def sample_repos() -> list[RepoSummary]:
    return [
        RepoSummary(name="testuser/myrepo", url="https://github.com/testuser/myrepo", language="Python", stars=5),
        RepoSummary(name="testuser/other", url="https://github.com/testuser/other", language="TypeScript", stars=2),
    ]


@pytest.fixture
def sample_summary(sample_profile, sample_contributions, sample_repos) -> ContributionSummary:
    from contributions.summarizer import summarize

    return summarize(sample_profile, sample_contributions, sample_repos)
