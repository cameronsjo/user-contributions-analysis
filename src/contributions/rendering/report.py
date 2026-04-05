"""Jinja2 HTML report renderer."""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from contributions.models import ContributionSummary

TEMPLATE_DIR = Path(__file__).parent / "templates"


def render_report(summary: ContributionSummary, output_path: Path) -> Path:
    """Render a contribution summary to a self-contained HTML file."""
    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)), autoescape=True)
    template = env.get_template("report.html")

    html = template.render(
        summary=summary,
        profile=summary.profile,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    return output_path
