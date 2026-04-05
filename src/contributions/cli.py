"""CLI entrypoint for contribution analysis."""

import asyncio
import webbrowser
from pathlib import Path

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from contributions.config import Settings
from contributions.providers.github import GitHubProvider
from contributions.rendering.report import render_report
from contributions.summarizer import summarize

console = Console()


@click.command()
@click.argument("username")
@click.option("--output", "-o", type=click.Path(), default=None, help="Output file path")
@click.option("--open", "open_browser", is_flag=True, help="Open report in browser after generation")
def main(username: str, output: str | None, open_browser: bool) -> None:
    """Generate a contribution report for a GitHub user."""
    asyncio.run(_generate(username, output, open_browser))


async def _generate(username: str, output: str | None, open_browser: bool) -> None:
    settings = Settings()
    output_path = Path(output) if output else Path("output") / f"{username}-report.html"

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
        async with GitHubProvider(token=settings.github_token) as github:
            task = progress.add_task("Fetching profile...", total=None)
            profile = await github.get_profile(username)
            progress.update(task, description=f"Found {profile.display_name or profile.username}")

            progress.update(task, description="Fetching repos...")
            repos = await github.get_repos(username)
            progress.update(task, description=f"Found {len(repos)} repos")

            progress.update(task, description="Fetching contributions...")
            contributions = await github.get_all_contributions(username)
            progress.update(task, description=f"Found {len(contributions)} contributions")

            progress.update(task, description="Summarizing...")
            summary = summarize(profile, contributions, repos)

            progress.update(task, description="Rendering report...")
            render_report(summary, output_path)
            progress.update(task, completed=True, description="Done!")

    console.print(f"\n[green]Report generated:[/green] {output_path}")
    console.print(f"  [dim]{summary.total_contributions} total contributions across {len(repos)} repos[/dim]")

    if open_browser:
        webbrowser.open(f"file://{output_path.resolve()}")
