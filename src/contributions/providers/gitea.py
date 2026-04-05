"""Gitea REST API provider for contribution data."""

import asyncio
import logging
from datetime import datetime

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

PER_PAGE = 50


class GiteaProvider:
    """Fetches contribution data from a Gitea instance's REST API."""

    def __init__(self, base_url: str, token: str | None = None) -> None:
        api_url = base_url.rstrip("/") + "/api/v1"
        headers = {"Accept": "application/json"}
        if token:
            headers["Authorization"] = f"token {token}"
        self._client = httpx.AsyncClient(base_url=api_url, headers=headers, timeout=30.0)
        self._base_url = base_url.rstrip("/")

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        await self.close()

    async def get_profile(self, username: str) -> UserProfile:
        data = await self._get(f"/users/{username}")
        return UserProfile(
            provider=Provider.GITEA,
            username=data["login"],
            display_name=data.get("full_name") or None,
            bio=data.get("description") or data.get("biography") or None,
            avatar_url=data.get("avatar_url"),
            profile_url=f"{self._base_url}/{data['login']}",
            public_repos=data.get("public_repos", 0),
            followers=data.get("followers_count", 0),
            following=data.get("following_count", 0),
            created_at=_parse_timestamp(data.get("created")),
        )

    async def get_repos(self, username: str) -> list[RepoSummary]:
        pages = await self._get_paginated(f"/users/{username}/repos", params={"limit": PER_PAGE})
        repos = []
        for data in pages:
            repos.append(
                RepoSummary(
                    name=data["full_name"],
                    url=data.get("html_url", f"{self._base_url}/{data['full_name']}"),
                    language=data.get("language") or None,
                    stars=data.get("stars_count", 0),
                    is_fork=data.get("fork", False),
                )
            )
        return repos

    async def get_contributions(self, username: str) -> list[Contribution]:
        """Fetch contributions by pulling commits, issues, and PRs from user's repos."""
        repos = await self.get_repos(username)
        own_repos = [r for r in repos if not r.is_fork]

        tasks = [self._get_repo_contributions(r.name, username) for r in own_repos[:15]]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_contributions: list[Contribution] = []
        for result in results:
            if isinstance(result, BaseException):
                logger.warning("Failed to fetch contributions for a Gitea repo: %s", result)
                continue
            all_contributions.extend(result)

        return all_contributions

    async def get_all_contributions(self, username: str) -> list[Contribution]:
        """Fetch all contributions and update repo summaries."""
        repos = await self.get_repos(username)
        contributions = await self.get_contributions(username)

        repo_map: dict[str, RepoSummary] = {r.name: r for r in repos}
        for c in contributions:
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

        return contributions

    async def _get_repo_contributions(self, repo_full_name: str, username: str) -> list[Contribution]:
        """Fetch commits, issues, and PRs for a single repo."""
        owner, repo = repo_full_name.split("/", 1)
        repo_url = f"{self._base_url}/{repo_full_name}"
        contributions: list[Contribution] = []

        # Commits
        commits = await self._get_paginated(f"/repos/{owner}/{repo}/commits", params={"limit": PER_PAGE}, max_pages=3)
        for data in commits:
            commit_info = data.get("commit", {})
            author_info = commit_info.get("author", {})
            # Match by commit author name or the API-level author login
            api_author = data.get("author")
            if api_author and api_author.get("login", "").lower() == username.lower():
                contributions.append(
                    CommitContribution(
                        provider=Provider.GITEA,
                        timestamp=_parse_timestamp(author_info.get("date")) or datetime.now(),
                        repo_name=repo_full_name,
                        repo_url=repo_url,
                        sha=data.get("sha", ""),
                        message=commit_info.get("message", ""),
                    )
                )

        # Issues (created by user)
        issues = await self._get_paginated(
            f"/repos/{owner}/{repo}/issues",
            params={"type": "issues", "created_by": username, "state": "all", "limit": PER_PAGE},
            max_pages=2,
        )
        for data in issues:
            contributions.append(
                IssueContribution(
                    provider=Provider.GITEA,
                    timestamp=_parse_timestamp(data.get("created_at")) or datetime.now(),
                    repo_name=repo_full_name,
                    repo_url=repo_url,
                    title=data.get("title", ""),
                    number=data.get("number", 0),
                    state="closed" if data.get("state") == "closed" else "open",
                    labels=[label.get("name", "") for label in data.get("labels", []) or []],
                )
            )

        # Pull requests (created by user)
        prs = await self._get_paginated(
            f"/repos/{owner}/{repo}/pulls",
            params={"state": "all", "limit": PER_PAGE},
            max_pages=2,
        )
        for data in prs:
            poster = data.get("user", {})
            if poster.get("login", "").lower() != username.lower():
                continue
            contributions.append(
                PullRequestContribution(
                    provider=Provider.GITEA,
                    timestamp=_parse_timestamp(data.get("created_at")) or datetime.now(),
                    repo_name=repo_full_name,
                    repo_url=repo_url,
                    title=data.get("title", ""),
                    number=data.get("number", 0),
                    state="merged" if data.get("merged") else data.get("state", "open"),
                    merged=data.get("merged", False),
                )
            )

        # PR reviews by user
        for pr_data in prs:
            pr_number = pr_data.get("number", 0)
            reviews = await self._get_safe(f"/repos/{owner}/{repo}/pulls/{pr_number}/reviews")
            if not reviews:
                continue
            for review in reviews:
                reviewer = review.get("user", {})
                if reviewer.get("login", "").lower() == username.lower():
                    contributions.append(
                        ReviewContribution(
                            provider=Provider.GITEA,
                            timestamp=_parse_timestamp(review.get("submitted_at")) or datetime.now(),
                            repo_name=repo_full_name,
                            repo_url=repo_url,
                            pr_number=pr_number,
                            pr_title=pr_data.get("title", ""),
                            state=_map_review_state(review.get("state", "")),
                        )
                    )

        return contributions

    async def _get(self, path: str, params: dict | None = None) -> dict:
        response = await self._client.get(path, params=params)
        response.raise_for_status()
        return response.json()

    async def _get_safe(self, path: str, params: dict | None = None) -> list | None:
        """GET that returns None on error instead of raising."""
        try:
            response = await self._client.get(path, params=params)
            if response.status_code != 200:
                return None
            return response.json()
        except httpx.HTTPError:
            return None

    async def _get_paginated(self, path: str, params: dict | None = None, max_pages: int = 10) -> list[dict]:
        all_items: list[dict] = []
        params = dict(params) if params else {}
        page = 1

        for _ in range(max_pages):
            params["page"] = page
            response = await self._client.get(path, params=params)
            response.raise_for_status()
            data = response.json()
            if not data:
                break
            all_items.extend(data)

            # Gitea uses x-total-count and page-based pagination
            total = response.headers.get("x-total-count")
            if total and len(all_items) >= int(total):
                break
            page += 1

        return all_items


def _parse_timestamp(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


def _map_review_state(state: str) -> str:
    """Map Gitea review states to our normalized states."""
    mapping = {
        "APPROVED": "approved",
        "REQUEST_CHANGES": "changes_requested",
        "COMMENT": "commented",
        "REJECTED": "changes_requested",
    }
    return mapping.get(state.upper(), "commented")
