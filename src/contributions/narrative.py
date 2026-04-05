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
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text
    except Exception:
        logger.warning("Failed to generate narrative summary", exc_info=True)
        return None


def _build_prompt(summary: ContributionSummary) -> str:
    """Build a prompt for Claude to summarize contributions."""
    profile = summary.profile

    top_repos_text = ""
    if summary.top_repos:
        repo_lines = []
        for r in summary.top_repos[:10]:
            lang = f" ({r.language})" if r.language else ""
            repo_lines.append(f"  - {r.name}{lang}: {r.commits} commits, {r.pull_requests} PRs, {r.stars} stars")
        top_repos_text = "\n".join(repo_lines)

    languages_text = ", ".join(
        f"{lang} ({count} repos)"
        for lang, count in sorted(summary.languages.items(), key=lambda x: x[1], reverse=True)[:10]
    )

    monthly_text = ""
    if summary.monthly_activity:
        monthly_lines = [f"  - {m.month}: {m.total} contributions" for m in summary.monthly_activity]
        monthly_text = "\n".join(monthly_lines)

    created = profile.created_at.strftime("%B %Y") if profile.created_at else "N/A"
    name = profile.display_name or "N/A"
    bio = profile.bio or "N/A"

    return (
        "Analyze this developer's contribution data and write a concise, "
        "insightful summary (3-5 paragraphs). Focus on:\n"
        "- What kind of developer they appear to be\n"
        "- Notable patterns in their activity\n"
        "- Interesting observations about their project portfolio\n"
        "- A brief characterization of their open-source profile\n\n"
        "Be specific and data-driven. Reference actual numbers and repo names. "
        "Write in third person. Don't be sycophantic.\n\n"
        f"## Developer Profile\n"
        f"- Username: {profile.username}\n"
        f"- Name: {name}\n"
        f"- Bio: {bio}\n"
        f"- Account created: {created}\n"
        f"- Public repos: {profile.public_repos}\n"
        f"- Followers: {profile.followers}\n\n"
        f"## Contribution Totals\n"
        f"- Commits: {summary.total_commits}\n"
        f"- Pull Requests: {summary.total_pull_requests}\n"
        f"- Issues: {summary.total_issues}\n"
        f"- Reviews: {summary.total_reviews}\n"
        f"- Total: {summary.total_contributions}\n\n"
        f"## Top Repositories\n"
        f"{top_repos_text or '  None tracked'}\n\n"
        f"## Languages\n"
        f"{languages_text or 'None detected'}\n\n"
        f"## Monthly Activity\n"
        f"{monthly_text or '  No monthly data available'}"
    )
