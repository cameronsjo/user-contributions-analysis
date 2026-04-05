"""Tests for GitHub API provider with mocked responses."""

import pytest
import respx
from httpx import Response

from contributions.models import ContributionType, Provider
from contributions.providers.github import GitHubProvider


@pytest.fixture
def github_user_response() -> dict:
    return {
        "login": "testuser",
        "name": "Test User",
        "bio": "A developer",
        "avatar_url": "https://avatars.githubusercontent.com/u/12345",
        "html_url": "https://github.com/testuser",
        "public_repos": 10,
        "followers": 50,
        "following": 20,
        "created_at": "2020-01-15T00:00:00Z",
    }


@pytest.fixture
def github_repos_response() -> list[dict]:
    return [
        {
            "full_name": "testuser/repo-a",
            "html_url": "https://github.com/testuser/repo-a",
            "language": "Python",
            "stargazers_count": 42,
            "fork": False,
        },
        {
            "full_name": "testuser/repo-b",
            "html_url": "https://github.com/testuser/repo-b",
            "language": "TypeScript",
            "stargazers_count": 10,
            "fork": True,
        },
    ]


@pytest.fixture
def github_events_response() -> list[dict]:
    return [
        {
            "type": "PushEvent",
            "repo": {"name": "testuser/repo-a"},
            "created_at": "2026-03-01T12:00:00Z",
            "payload": {
                "commits": [
                    {
                        "sha": "aaa111",
                        "message": "feat: something",
                        "author": {"name": "testuser", "email": "test@example.com"},
                    }
                ]
            },
        },
        {
            "type": "PullRequestEvent",
            "repo": {"name": "testuser/repo-a"},
            "created_at": "2026-03-02T12:00:00Z",
            "payload": {"pull_request": {"title": "Add feature", "number": 1, "state": "closed", "merged": True}},
        },
        {
            "type": "IssuesEvent",
            "repo": {"name": "testuser/repo-a"},
            "created_at": "2026-03-03T12:00:00Z",
            "payload": {"issue": {"title": "Bug report", "number": 5, "state": "open", "labels": [{"name": "bug"}]}},
        },
    ]


@respx.mock
@pytest.mark.asyncio
async def test_get_profile(github_user_response):
    respx.get("https://api.github.com/users/testuser").mock(return_value=Response(200, json=github_user_response))

    async with GitHubProvider() as provider:
        profile = await provider.get_profile("testuser")

    assert profile.username == "testuser"
    assert profile.display_name == "Test User"
    assert profile.provider == Provider.GITHUB
    assert profile.public_repos == 10


@respx.mock
@pytest.mark.asyncio
async def test_get_repos(github_repos_response):
    respx.get("https://api.github.com/users/testuser/repos").mock(
        return_value=Response(200, json=github_repos_response)
    )

    async with GitHubProvider() as provider:
        repos = await provider.get_repos("testuser")

    assert len(repos) == 2
    assert repos[0].name == "testuser/repo-a"
    assert repos[0].language == "Python"
    assert repos[0].stars == 42
    assert repos[0].is_fork is False
    assert repos[1].is_fork is True


@respx.mock
@pytest.mark.asyncio
async def test_get_contributions_parses_events(github_events_response):
    respx.get("https://api.github.com/users/testuser/events/public").mock(
        return_value=Response(200, json=github_events_response)
    )

    async with GitHubProvider() as provider:
        contributions = await provider.get_contributions("testuser")

    types = [c.type for c in contributions]
    assert ContributionType.COMMIT in types
    assert ContributionType.PULL_REQUEST in types
    assert ContributionType.ISSUE in types


@respx.mock
@pytest.mark.asyncio
async def test_get_profile_with_token(github_user_response):
    route = respx.get("https://api.github.com/users/testuser").mock(
        return_value=Response(200, json=github_user_response)
    )

    async with GitHubProvider(token="ghp_test123") as provider:
        await provider.get_profile("testuser")

    assert route.calls[0].request.headers["authorization"] == "Bearer ghp_test123"


@respx.mock
@pytest.mark.asyncio
async def test_rate_limit_warning(github_user_response, caplog):
    respx.get("https://api.github.com/users/testuser").mock(
        return_value=Response(200, json=github_user_response, headers={"x-ratelimit-remaining": "5"})
    )

    async with GitHubProvider() as provider:
        await provider.get_profile("testuser")

    assert any("rate limit low" in r.message.lower() for r in caplog.records)
