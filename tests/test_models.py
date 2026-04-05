"""Tests for contribution data models."""

from datetime import UTC, datetime

from contributions.models import (
    CommitContribution,
    ContributionType,
    MonthlyActivity,
    Provider,
    UserProfile,
)


def test_commit_contribution_defaults():
    c = CommitContribution(
        provider=Provider.GITHUB,
        timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        repo_name="user/repo",
        repo_url="https://github.com/user/repo",
        sha="abc123",
        message="initial commit",
    )
    assert c.type == ContributionType.COMMIT
    assert c.additions == 0
    assert c.deletions == 0


def test_user_profile_optional_fields():
    p = UserProfile(
        provider=Provider.GITHUB,
        username="minimal",
        profile_url="https://github.com/minimal",
    )
    assert p.display_name is None
    assert p.bio is None
    assert p.avatar_url is None
    assert p.public_repos == 0


def test_monthly_activity_total():
    m = MonthlyActivity(month="2026-01", commits=10, pull_requests=3, issues=2, reviews=1)
    assert m.total == 16


def test_monthly_activity_total_zero():
    m = MonthlyActivity(month="2026-01")
    assert m.total == 0
