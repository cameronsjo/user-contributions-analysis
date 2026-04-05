"""CLI entrypoint for contribution analysis."""

import asyncio
import webbrowser
from pathlib import Path

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from contributions.config import Settings
from contributions.models import CalendarDay, Contribution, RepoSummary, UserProfile
from contributions.narrative import generate_narrative
from contributions.providers.gitea import GiteaProvider
from contributions.providers.github import GitHubProvider
from contributions.providers.github_graphql import fetch_graphql_contributions
from contributions.rendering.report import render_report
from contributions.summarizer import summarize

console = Console()


@click.command()
@click.argument("username")
@click.option("--output", "-o", type=click.Path(), default=None, help="Output file path")
@click.option("--open", "open_browser", is_flag=True, help="Open report in browser after generation")
@click.option("--gitea-url", default=None, help="Gitea instance URL (overrides GITEA_URL env var)")
@click.option("--gitea-user", default=None, help="Gitea username (defaults to same as GitHub username)")
@click.option("--no-narrative", is_flag=True, help="Skip AI narrative summary generation")
def main(
    username: str,
    output: str | None,
    open_browser: bool,
    gitea_url: str | None,
    gitea_user: str | None,
    no_narrative: bool,
) -> None:
    """Generate a contribution report for a GitHub/Gitea user."""
    asyncio.run(_generate(username, output, open_browser, gitea_url, gitea_user, no_narrative))


async def _generate(
    username: str,
    output: str | None,
    open_browser: bool,
    gitea_url: str | None,
    gitea_user: str | None,
    no_narrative: bool,
) -> None:
    settings = Settings()
    output_path = Path(output) if output else Path("output") / f"{username}-report.html"
    gitea_base = gitea_url or settings.gitea_url
    gitea_username = gitea_user or username

    all_contributions: list[Contribution] = []
    all_repos: list[RepoSummary] = []
    profile: UserProfile | None = None
    calendar: list[CalendarDay] = []
    private_contributions = 0
    providers_used: list[str] = []

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
        task = progress.add_task("Starting...", total=None)

        # GitHub REST API
        progress.update(task, description="Fetching GitHub profile...")
        async with GitHubProvider(token=settings.github_token) as github:
            profile = await github.get_profile(username)
            progress.update(task, description=f"Found {profile.display_name or profile.username}")

            progress.update(task, description="Fetching GitHub repos...")
            gh_repos = await github.get_repos(username)
            all_repos.extend(gh_repos)

            progress.update(task, description="Fetching GitHub contributions...")
            gh_contributions = await github.get_all_contributions(username)
            all_contributions.extend(gh_contributions)
            providers_used.append("github")

        # GitHub GraphQL (if token available)
        if settings.github_token:
            progress.update(task, description="Fetching GitHub GraphQL data (full year)...")
            graphql_data = await fetch_graphql_contributions(settings.github_token, username)
            if graphql_data:
                private_contributions = graphql_data.private_contributions
                calendar = [CalendarDay(date=d.date, count=d.count) for d in graphql_data.calendar_days]

                # Enrich repo data with GraphQL counts where REST didn't capture
                _enrich_repos_from_graphql(all_repos, graphql_data)
                progress.update(task, description=f"GraphQL: {graphql_data.calendar_total} contributions this year")

        # Gitea (if configured)
        if gitea_base:
            progress.update(task, description=f"Fetching Gitea profile from {gitea_base}...")
            try:
                async with GiteaProvider(base_url=gitea_base, token=settings.gitea_token) as gitea:
                    gitea_profile = await gitea.get_profile(gitea_username)
                    if not profile:
                        profile = gitea_profile

                    progress.update(task, description="Fetching Gitea repos...")
                    gitea_repos = await gitea.get_repos(gitea_username)
                    all_repos.extend(gitea_repos)

                    progress.update(task, description="Fetching Gitea contributions...")
                    gitea_contributions = await gitea.get_all_contributions(gitea_username)
                    all_contributions.extend(gitea_contributions)
                    providers_used.append("gitea")
                    progress.update(task, description=f"Gitea: {len(gitea_contributions)} contributions")
            except Exception as e:
                console.print(f"[yellow]Warning:[/yellow] Gitea fetch failed: {e}")

        # Summarize
        progress.update(task, description="Summarizing...")
        summary = summarize(profile, all_contributions, all_repos)
        summary.calendar = calendar
        summary.private_contributions = private_contributions
        summary.providers = providers_used

        # Narrative (optional)
        if not no_narrative and settings.anthropic_api_key:
            progress.update(task, description="Generating narrative summary...")
            summary.narrative = await generate_narrative(summary, api_key=settings.anthropic_api_key)

        # Render
        progress.update(task, description="Rendering report...")
        render_report(summary, output_path)
        progress.update(task, completed=True, description="Done!")

    console.print(f"\n[green]Report generated:[/green] {output_path}")
    source_label = " + ".join(providers_used)
    console.print(
        f"  [dim]{summary.total_contributions} contributions across {len(all_repos)} repos ({source_label})[/dim]"
    )
    if private_contributions:
        console.print(f"  [dim]+{private_contributions} private contributions[/dim]")
    if summary.narrative:
        console.print("  [dim]Includes AI narrative summary[/dim]")

    if open_browser:
        webbrowser.open(f"file://{output_path.resolve()}")


def _enrich_repos_from_graphql(repos: list[RepoSummary], graphql_data) -> None:
    """Supplement REST repo data with GraphQL contribution counts."""
    repo_map = {r.name: r for r in repos}
    for name, data in graphql_data.commit_repos.items():
        if name not in repo_map:
            repos.append(
                RepoSummary(
                    name=name,
                    url=data["url"],
                    language=data.get("language"),
                    stars=data.get("stars", 0),
                    is_fork=data.get("is_fork", False),
                )
            )
