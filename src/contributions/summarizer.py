"""Pure Python contribution summarization — no LLM needed for v0.1.0."""

from collections import Counter, defaultdict

from contributions.models import (
    Contribution,
    ContributionSummary,
    ContributionType,
    MonthlyActivity,
    RepoSummary,
    UserProfile,
)


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

    # Language breakdown from repos
    languages: dict[str, int] = Counter(r.language for r in repos if r.language)

    # Top repos by total activity
    top_repos = sorted(
        [r for r in repos if (r.commits + r.pull_requests + r.issues + r.reviews) > 0],
        key=lambda r: r.commits + r.pull_requests + r.issues + r.reviews + r.stars,
        reverse=True,
    )[:15]

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
    )
