"""Pure Python contribution summarization — no LLM needed for v0.1.0."""

from collections import Counter, defaultdict
from datetime import datetime

from contributions.models import (
    CommitContribution,
    Contribution,
    ContributionSummary,
    ContributionType,
    IssueContribution,
    MonthlyActivity,
    PullRequestContribution,
    RepoContributions,
    RepoSummary,
    ReviewContribution,
    UserProfile,
)


def filter_by_date_range(
    contributions: list[Contribution],
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> list[Contribution]:
    """Filter contributions to a date range."""
    filtered = contributions
    if date_from:
        filtered = [c for c in filtered if c.timestamp >= date_from]
    if date_to:
        filtered = [c for c in filtered if c.timestamp <= date_to]
    return filtered


def build_details(contributions: list[Contribution]) -> list[RepoContributions]:
    """Group contributions by repo for the detail view."""
    by_repo: dict[str, RepoContributions] = {}

    for c in sorted(contributions, key=lambda x: x.timestamp, reverse=True):
        if c.repo_name not in by_repo:
            by_repo[c.repo_name] = RepoContributions(repo_name=c.repo_name, repo_url=c.repo_url)

        detail = by_repo[c.repo_name]
        match c:
            case CommitContribution():
                detail.commits.append(c)
            case PullRequestContribution():
                detail.pull_requests.append(c)
            case IssueContribution():
                detail.issues.append(c)
            case ReviewContribution():
                detail.reviews.append(c)

    return sorted(by_repo.values(), key=lambda r: r.total, reverse=True)


def summarize(
    profile: UserProfile,
    contributions: list[Contribution],
    repos: list[RepoSummary],
) -> ContributionSummary:
    """Aggregate raw contributions into a renderable summary."""
    type_counts = Counter(c.type for c in contributions)

    # Monthly activity
    monthly: dict[str, dict[str, int]] = defaultdict(
        lambda: {"commits": 0, "pull_requests": 0, "issues": 0, "reviews": 0}
    )
    for c in contributions:
        month_key = c.timestamp.strftime("%Y-%m")
        match c.type:
            case ContributionType.COMMIT:
                monthly[month_key]["commits"] += 1
            case ContributionType.PULL_REQUEST:
                monthly[month_key]["pull_requests"] += 1
            case ContributionType.ISSUE:
                monthly[month_key]["issues"] += 1
            case ContributionType.REVIEW:
                monthly[month_key]["reviews"] += 1

    monthly_activity = sorted(
        [MonthlyActivity(month=k, **v) for k, v in monthly.items()],
        key=lambda m: m.month,
    )

    # Count contributions per repo
    repo_map: dict[str, RepoSummary] = {r.name: r.model_copy() for r in repos}
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

    # Language breakdown from repos
    languages: dict[str, int] = Counter(r.language for r in repos if r.language)

    # Top repos by total activity
    enriched_repos = list(repo_map.values())
    top_repos = sorted(
        [r for r in enriched_repos if (r.commits + r.pull_requests + r.issues + r.reviews) > 0],
        key=lambda r: r.commits + r.pull_requests + r.issues + r.reviews + r.stars,
        reverse=True,
    )[:15]

    # Build detail view
    details = build_details(contributions)

    return ContributionSummary(
        profile=profile,
        total_commits=type_counts.get(ContributionType.COMMIT, 0),
        total_pull_requests=type_counts.get(ContributionType.PULL_REQUEST, 0),
        total_issues=type_counts.get(ContributionType.ISSUE, 0),
        total_reviews=type_counts.get(ContributionType.REVIEW, 0),
        top_repos=top_repos,
        monthly_activity=monthly_activity,
        languages=dict(languages),
        contribution_types={
            "Commits": type_counts.get(ContributionType.COMMIT, 0),
            "Pull Requests": type_counts.get(ContributionType.PULL_REQUEST, 0),
            "Issues": type_counts.get(ContributionType.ISSUE, 0),
            "Reviews": type_counts.get(ContributionType.REVIEW, 0),
        },
        details=details,
    )
