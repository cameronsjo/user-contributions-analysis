"""Narrative summarization of contributions using Claude API.

Optional — works without an API key, just returns None.
"""

import logging

from contributions.models import ContributionSummary

logger = logging.getLogger(__name__)


async def generate_narrative(summary: ContributionSummary, api_key: str | None = None) -> str | None:
    """Generate a narrative summary of contributions using Claude.

    Returns None if no API key is configured or the request fails.
    """
    if not api_key:
        return None

    try:
        import anthropic
    except ImportError:
        logger.warning("anthropic package not installed, skipping narrative generation")
        return None

    prompt = _build_prompt(summary)

    try:
        client = anthropic.AsyncAnthropic(api_key=api_key)
        message = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text
    except Exception:
        logger.warning("Failed to generate narrative summary", exc_info=True)
        return None


def _build_prompt(summary: ContributionSummary) -> str:
    """Build a prompt that feeds actual commit messages and PR titles."""
    profile = summary.profile
    created = profile.created_at.strftime("%B %Y") if profile.created_at else "N/A"

    # Date range context
    range_ctx = ""
    if summary.date_from or summary.date_to:
        f = summary.date_from or "the beginning"
        t = summary.date_to or "present"
        range_ctx = f"This report covers: {f} to {t}.\n\n"

    # Build the actual work log from details
    work_log_lines: list[str] = []
    for repo_detail in summary.details:
        repo_lines = [f"\n### {repo_detail.repo_name}"]

        # PRs first — they tell the story best
        for pr in repo_detail.pull_requests:
            state = f" [{pr.state}]" if pr.state != "open" else ""
            repo_lines.append(f"  PR #{pr.number}: {pr.title}{state}")

        # Commit messages (deduplicate merge commits, cap at 30)
        seen_messages: set[str] = set()
        commit_lines: list[str] = []
        for commit in repo_detail.commits:
            first_line = commit.message.split("\n")[0].strip()
            if first_line in seen_messages or first_line.startswith("Merge"):
                continue
            seen_messages.add(first_line)
            commit_lines.append(f"  commit: {first_line}")
        repo_lines.extend(commit_lines[:30])
        if len(commit_lines) > 30:
            repo_lines.append(f"  ...and {len(commit_lines) - 30} more commits")

        # Issues
        for issue in repo_detail.issues:
            repo_lines.append(f"  Issue #{issue.number}: {issue.title} [{issue.state}]")

        # Reviews
        for review in repo_detail.reviews:
            repo_lines.append(f"  Review on PR #{review.pr_number}: {review.pr_title}")

        work_log_lines.extend(repo_lines)

    work_log = "\n".join(work_log_lines) if work_log_lines else "  No detailed contributions available"

    return (
        "You are analyzing a developer's actual work output. Below are their "
        "real commit messages, PR titles, and issues from the time period.\n\n"
        "Write a narrative (3-5 paragraphs) that tells the story of what they "
        "actually built and worked on. Focus on:\n"
        "- What projects/features they shipped or progressed\n"
        "- The themes and patterns in their work (what problems were they solving?)\n"
        "- How the work connects across repos (if it does)\n"
        "- The technical scope — were they doing infra, features, fixes, tooling?\n\n"
        "Write like a knowledgeable colleague summarizing someone's work for a "
        "team standup or performance review. Be specific — name actual projects, "
        "features, and patterns you see in the commit messages. Write in third "
        "person. Don't be sycophantic or generic.\n\n"
        f"{range_ctx}"
        f"## Developer: {profile.display_name or profile.username} "
        f"(@{profile.username})\n"
        f"- Bio: {profile.bio or 'N/A'}\n"
        f"- Account created: {created}\n\n"
        f"## Stats\n"
        f"- {summary.total_commits} commits, "
        f"{summary.total_pull_requests} PRs, "
        f"{summary.total_issues} issues, "
        f"{summary.total_reviews} reviews\n\n"
        f"## Actual Work Log\n"
        f"{work_log}"
    )
