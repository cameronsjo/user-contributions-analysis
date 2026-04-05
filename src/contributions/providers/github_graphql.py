"""GitHub GraphQL API for richer contribution data.

The GraphQL contributionsCollection provides a full year of data including:
- Contribution calendar (daily activity heatmap)
- Commit, issue, PR, and review counts
- Repositories contributed to
- Private contribution counts (with token)

Requires a GitHub token — GraphQL API does not support unauthenticated requests.
"""

import logging
from datetime import UTC, datetime

import httpx

logger = logging.getLogger(__name__)

GRAPHQL_URL = "https://api.github.com/graphql"

CONTRIBUTIONS_QUERY = """
query($username: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $username) {
    contributionsCollection(from: $from, to: $to) {
      totalCommitContributions
      totalIssueContributions
      totalPullRequestContributions
      totalPullRequestReviewContributions
      restrictedContributionsCount
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            date
            contributionCount
          }
        }
      }
      commitContributionsByRepository(maxRepositories: 25) {
        repository {
          nameWithOwner
          url
          primaryLanguage {
            name
          }
          stargazerCount
          isFork
        }
        contributions {
          totalCount
        }
      }
      issueContributionsByRepository(maxRepositories: 25) {
        repository {
          nameWithOwner
          url
        }
        contributions {
          totalCount
        }
      }
      pullRequestContributionsByRepository(maxRepositories: 25) {
        repository {
          nameWithOwner
          url
        }
        contributions {
          totalCount
        }
      }
      pullRequestReviewContributionsByRepository(maxRepositories: 25) {
        repository {
          nameWithOwner
          url
        }
        contributions {
          totalCount
        }
      }
    }
  }
}
"""


class ContributionCalendarDay:
    """A single day in the contribution calendar."""

    def __init__(self, date: str, count: int) -> None:
        self.date = date
        self.count = count


class GraphQLContributions:
    """Rich contribution data from GitHub's GraphQL API."""

    def __init__(self, data: dict) -> None:
        collection = data["user"]["contributionsCollection"]
        self.total_commits = collection["totalCommitContributions"]
        self.total_issues = collection["totalIssueContributions"]
        self.total_pull_requests = collection["totalPullRequestContributions"]
        self.total_reviews = collection["totalPullRequestReviewContributions"]
        self.private_contributions = collection["restrictedContributionsCount"]

        # Calendar
        calendar = collection["contributionCalendar"]
        self.calendar_total = calendar["totalContributions"]
        self.calendar_days: list[ContributionCalendarDay] = []
        for week in calendar["weeks"]:
            for day in week["contributionDays"]:
                self.calendar_days.append(ContributionCalendarDay(day["date"], day["contributionCount"]))

        # Per-repo breakdowns
        self.commit_repos = _parse_repo_contributions(collection["commitContributionsByRepository"])
        self.issue_repos = _parse_repo_contributions(collection["issueContributionsByRepository"])
        self.pr_repos = _parse_repo_contributions(collection["pullRequestContributionsByRepository"])
        self.review_repos = _parse_repo_contributions(collection["pullRequestReviewContributionsByRepository"])

    @property
    def total_contributions(self) -> int:
        return self.total_commits + self.total_issues + self.total_pull_requests + self.total_reviews


async def fetch_graphql_contributions(
    token: str,
    username: str,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
) -> GraphQLContributions | None:
    """Fetch rich contribution data from GitHub's GraphQL API.

    Returns None if the request fails (e.g., bad token, rate limited).
    """
    if not from_date:
        from_date = datetime(
            datetime.now(tz=UTC).year - 1, datetime.now(tz=UTC).month, datetime.now(tz=UTC).day, tzinfo=UTC
        )
    if not to_date:
        to_date = datetime.now(tz=UTC)

    variables = {
        "username": username,
        "from": from_date.isoformat(),
        "to": to_date.isoformat(),
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            GRAPHQL_URL,
            json={"query": CONTRIBUTIONS_QUERY, "variables": variables},
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
        )

    if response.status_code != 200:
        logger.warning("GitHub GraphQL request failed with status %d", response.status_code)
        return None

    data = response.json()
    if "errors" in data:
        logger.warning("GitHub GraphQL errors: %s", data["errors"])
        return None

    if not data.get("data", {}).get("user"):
        logger.warning("GitHub GraphQL returned no user data for %s", username)
        return None

    return GraphQLContributions(data["data"])


def _parse_repo_contributions(repos_data: list[dict]) -> dict[str, dict]:
    """Parse per-repository contribution data from GraphQL response."""
    result = {}
    for entry in repos_data:
        repo = entry["repository"]
        name = repo["nameWithOwner"]
        result[name] = {
            "name": name,
            "url": repo["url"],
            "language": repo.get("primaryLanguage", {}).get("name") if repo.get("primaryLanguage") else None,
            "stars": repo.get("stargazerCount", 0),
            "is_fork": repo.get("isFork", False),
            "count": entry["contributions"]["totalCount"],
        }
    return result
