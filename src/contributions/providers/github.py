"""GitHub REST API provider for contribution data."""

import asyncio
import logging
from datetime import UTC, datetime

import httpx

from contributions.models import (
    CommitContribution,
    Contribution,
    ContributionType,
    IssueContribution,
    Provider,
    PullRequestContribution,
    RepoSummary,
    ReviewContribution,
    UserProfile,
)

logger = logging.getLogger(__name__)

API_BASE = "https://api.github.com"
PER_PAGE = 100


class GitHubProvider:
    """Fetches contribution data from the GitHub REST API."""

    def __init__(self, token: str | None = None) -> None:
        headers = {"Accept": "application/vnd.github+json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self._client = httpx.AsyncClient(base_url=API_BASE, headers=headers, timeout=30.0)

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        await self.close()

    async def get_profile(self, username: str) -> UserProfile:
        data = await self._get(f"/users/{username}")
        return UserProfile(
            provider=Provider.GITHUB,
            username=data["login"],
            display_name=data.get("name"),
            bio=data.get("bio"),
            avatar_url=data.get("avatar_url"),
            profile_url=data["html_url"],
            public_repos=data.get("public_repos", 0),
            followers=data.get("followers", 0),
            following=data.get("following", 0),
            created_at=_parse_timestamp(data.get("created_at")),
        )

    async def get_repos(self, username: str) -> list[RepoSummary]:
        pages = await self._get_paginated(f"/users/{username}/repos", params={"sort": "pushed", "per_page": PER_PAGE})
        repos = []
        for data in pages:
            repos.append(
                RepoSummary(
                    name=data["full_name"],
                    url=data["html_url"],
                    language=data.get("language"),
                    stars=data.get("stargazers_count", 0),
                    is_fork=data.get("fork", False),
                )
            )
        return repos

    async def get_contributions(self, username: str) -> list[Contribution]:
        events = await self._get_paginated(
            f"/users/{username}/events/public", params={"per_page": PER_PAGE}, max_pages=3
        )
        contributions: list[Contribution] = []
        for event in events:
            parsed = _parse_event(event, username)
            if parsed:
                contributions.extend(parsed)
        return contributions

    async def get_repo_commits(self, owner: str, repo: str, author: str) -> list[CommitContribution]:
        """Fetch commits for a specific repo by author."""
        commits_data = await self._get_paginated(
            f"/repos/{owner}/{repo}/commits",
            params={"author": author, "per_page": PER_PAGE},
            max_pages=5,
        )
        commits = []
        for data in commits_data:
            commit_info = data.get("commit", {})
            author_date = commit_info.get("author", {}).get("date")
            commits.append(
                CommitContribution(
                    provider=Provider.GITHUB,
                    timestamp=_parse_timestamp(author_date) or datetime.now(tz=UTC),
                    repo_name=f"{owner}/{repo}",
                    repo_url=f"https://github.com/{owner}/{repo}",
                    sha=data.get("sha", ""),
                    message=commit_info.get("message", ""),
                    additions=data.get("stats", {}).get("additions", 0),
                    deletions=data.get("stats", {}).get("deletions", 0),
                )
            )
        return commits

    async def get_all_contributions(self, username: str) -> list[Contribution]:
        """Fetch contributions from events and top repo commits."""
        repos = await self.get_repos(username)
        event_contributions = await self.get_contributions(username)

        # Get commits from top repos (non-fork, sorted by stars)
        own_repos = sorted([r for r in repos if not r.is_fork], key=lambda r: r.stars, reverse=True)[:10]

        commit_tasks = []
        for repo in own_repos:
            parts = repo.name.split("/")
            if len(parts) == 2:
                commit_tasks.append(self.get_repo_commits(parts[0], parts[1], username))

        commit_results = await asyncio.gather(*commit_tasks, return_exceptions=True)

        all_contributions = list(event_contributions)
        seen_shas: set[str] = set()
        for c in all_contributions:
            if isinstance(c, CommitContribution):
                seen_shas.add(c.sha)

        for result in commit_results:
            if isinstance(result, BaseException):
                logger.warning("Failed to fetch commits for a repo: %s", result)
                continue
            for commit in result:
                if commit.sha not in seen_shas:
                    all_contributions.append(commit)
                    seen_shas.add(commit.sha)

        # Update repo summaries with contribution counts
        repo_map: dict[str, RepoSummary] = {r.name: r for r in repos}
        for c in all_contributions:
            if c.repo_name in repo_map:
                r = repo_map[c.repo_name]
                match c.type:
                    case ContributionType.COMMIT:
                        r.commits += 1
                    case ContributionType.PULL_REQUEST:
                        r.pull_requests += 1
                    case ContributionType.ISSUE:
                        r.issues += 1
                    case ContributionType.REVIEW:
                        r.reviews += 1

        return all_contributions

    async def _get(self, path: str, params: dict | None = None) -> dict:
        response = await self._client.get(path, params=params)
        _check_rate_limit(response)
        response.raise_for_status()
        return response.json()

    async def _get_paginated(self, path: str, params: dict | None = None, max_pages: int = 10) -> list[dict]:
        all_items: list[dict] = []
        params = dict(params) if params else {}
        url = path

        for _ in range(max_pages):
            response = await self._client.get(url, params=params)
            _check_rate_limit(response)
            response.raise_for_status()
            data = response.json()
            if not data:
                break
            all_items.extend(data)

            next_url = _parse_next_link(response.headers.get("link", ""))
            if not next_url:
                break
            url = next_url
            params = {}  # params are encoded in the next URL

        return all_items


def _check_rate_limit(response: httpx.Response) -> None:
    remaining = response.headers.get("x-ratelimit-remaining")
    if remaining is not None and int(remaining) < 10:
        logger.warning("GitHub API rate limit low: %s requests remaining", remaining)


def _parse_next_link(link_header: str) -> str | None:
    if not link_header:
        return None
    for part in link_header.split(","):
        if 'rel="next"' in part:
            url = part.split(";")[0].strip().strip("<>")
            return url
    return None


def _parse_timestamp(ts: str | None) -> datetime | None:
    if not ts:
        return None
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def _parse_event(event: dict, username: str) -> list[Contribution] | None:
    """Parse a GitHub event into normalized contribution(s)."""
    event_type = event.get("type")
    repo = event.get("repo", {})
    repo_name = repo.get("name", "unknown/unknown")
    repo_url = f"https://github.com/{repo_name}"
    created_at = _parse_timestamp(event.get("created_at"))
    if not created_at:
        return None

    payload = event.get("payload", {})

    match event_type:
        case "PushEvent":
            commits = payload.get("commits", [])
            return [
                CommitContribution(
                    provider=Provider.GITHUB,
                    timestamp=created_at,
                    repo_name=repo_name,
                    repo_url=repo_url,
                    sha=c.get("sha", ""),
                    message=c.get("message", ""),
                )
                for c in commits
                if c.get("author", {}).get("name", "").lower() == username.lower()
                or c.get("author", {}).get("email", "").startswith(username)
            ]

        case "PullRequestEvent":
            pr = payload.get("pull_request", {})
            return [
                PullRequestContribution(
                    provider=Provider.GITHUB,
                    timestamp=created_at,
                    repo_name=repo_name,
                    repo_url=repo_url,
                    title=pr.get("title", ""),
                    number=pr.get("number", 0),
                    state=pr.get("state", "open"),
                    merged=pr.get("merged", False),
                )
            ]

        case "IssuesEvent":
            issue = payload.get("issue", {})
            return [
                IssueContribution(
                    provider=Provider.GITHUB,
                    timestamp=created_at,
                    repo_name=repo_name,
                    repo_url=repo_url,
                    title=issue.get("title", ""),
                    number=issue.get("number", 0),
                    state=issue.get("state", "open"),
                    labels=[label.get("name", "") for label in issue.get("labels", [])],
                )
            ]

        case "PullRequestReviewEvent":
            review = payload.get("review", {})
            pr = payload.get("pull_request", {})
            return [
                ReviewContribution(
                    provider=Provider.GITHUB,
                    timestamp=created_at,
                    repo_name=repo_name,
                    repo_url=repo_url,
                    pr_number=pr.get("number", 0),
                    pr_title=pr.get("title", ""),
                    state=review.get("state", "commented"),
                )
            ]

        case _:
            return None
