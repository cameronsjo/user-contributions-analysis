"""Jinja2 HTML report renderer."""

import re
from html import escape
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from markupsafe import Markup

from contributions.models import ContributionSummary

TEMPLATE_DIR = Path(__file__).parent / "templates"


def _narrative_to_html(text: str) -> Markup:
    """Convert narrative text with basic markdown to safe HTML paragraphs."""
    # Split on double or single blank lines
    paragraphs = re.split(r"\n{2,}", text.strip())
    html_parts = []
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        # Escape HTML, then convert **bold** to <strong>
        safe = escape(para)
        safe = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", safe)
        html_parts.append(f"<p>{safe}</p>")
    return Markup("\n".join(html_parts))


def render_report(summary: ContributionSummary, output_path: Path) -> Path:
    """Render a contribution summary to a self-contained HTML file."""
    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)), autoescape=True)
    template = env.get_template("report.html")

    # Pre-render narrative to safe HTML
    narrative_html = _narrative_to_html(summary.narrative) if summary.narrative else None

    html = template.render(
        summary=summary,
        profile=summary.profile,
        narrative_html=narrative_html,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    return output_path
