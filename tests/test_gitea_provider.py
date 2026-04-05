"""Tests for Gitea API provider with mocked responses."""

import pytest
import respx
from httpx import Response

from contributions.models import ContributionType, Provider
from contributions.providers.gitea import GiteaProvider

BASE_URL = "https://gitea.example.com"
API_URL = f"{BASE_URL}/api/v1"


@pytest.fixture
def gitea_user_response() -> dict:
    return {
        "login": "testuser",
        "full_name": "Test User",
        "description": "A Gitea developer",
        "avatar_url": "https://gitea.example.com/avatars/123",
        "public_repos": 5,
        "followers_count": 10,
        "following_count": 3,
        "created": "2021-06-01T00:00:00Z",
    }


@pytest.fixture
def gitea_repos_response() -> list[dict]:
    return [
        {
            "full_name": "testuser/project-a",
            "html_url": "https://gitea.example.com/testuser/project-a",
            "language": "Go",
            "stars_count": 8,
            "fork": False,
        },
    ]


@respx.mock
@pytest.mark.asyncio
async def test_get_profile(gitea_user_response):
    respx.get(f"{API_URL}/users/testuser").mock(return_value=Response(200, json=gitea_user_response))

    async with GiteaProvider(base_url=BASE_URL) as provider:
        profile = await provider.get_profile("testuser")

    assert profile.username == "testuser"
    assert profile.display_name == "Test User"
    assert profile.provider == Provider.GITEA
    assert profile.public_repos == 5
    assert profile.profile_url == f"{BASE_URL}/testuser"


@respx.mock
@pytest.mark.asyncio
async def test_get_repos(gitea_repos_response):
    respx.get(f"{API_URL}/users/testuser/repos").mock(
        return_value=Response(200, json=gitea_repos_response, headers={"x-total-count": "1"})
    )

    async with GiteaProvider(base_url=BASE_URL) as provider:
        repos = await provider.get_repos("testuser")

    assert len(repos) == 1
    assert repos[0].name == "testuser/project-a"
    assert repos[0].language == "Go"
    assert repos[0].stars == 8


@respx.mock
@pytest.mark.asyncio
async def test_get_profile_with_token(gitea_user_response):
    route = respx.get(f"{API_URL}/users/testuser").mock(return_value=Response(200, json=gitea_user_response))

    async with GiteaProvider(base_url=BASE_URL, token="tok_test123") as provider:
        await provider.get_profile("testuser")

    assert route.calls[0].request.headers["authorization"] == "token tok_test123"


@respx.mock
@pytest.mark.asyncio
async def test_get_contributions_fetches_commits(gitea_repos_response):
    respx.get(f"{API_URL}/users/testuser/repos").mock(
        return_value=Response(200, json=gitea_repos_response, headers={"x-total-count": "1"})
    )

    commits_response = [
        {
            "sha": "aaa111",
            "commit": {"message": "feat: init", "author": {"date": "2026-03-01T12:00:00Z"}},
            "author": {"login": "testuser"},
        }
    ]
    respx.get(f"{API_URL}/repos/testuser/project-a/commits").mock(
        return_value=Response(200, json=commits_response, headers={"x-total-count": "1"})
    )
    respx.get(f"{API_URL}/repos/testuser/project-a/issues").mock(
        return_value=Response(200, json=[], headers={"x-total-count": "0"})
    )
    respx.get(f"{API_URL}/repos/testuser/project-a/pulls").mock(
        return_value=Response(200, json=[], headers={"x-total-count": "0"})
    )

    async with GiteaProvider(base_url=BASE_URL) as provider:
        contributions = await provider.get_contributions("testuser")

    assert len(contributions) == 1
    assert contributions[0].type == ContributionType.COMMIT
