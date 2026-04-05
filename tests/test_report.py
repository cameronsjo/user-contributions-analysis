"""Tests for Jinja2 HTML report rendering."""

from contributions.rendering.report import render_report


def test_render_report_creates_file(sample_summary, tmp_path):
    output = tmp_path / "test-report.html"
    result = render_report(sample_summary, output)

    assert result == output
    assert output.exists()


def test_render_report_contains_profile(sample_summary, tmp_path):
    output = tmp_path / "test-report.html"
    render_report(sample_summary, output)
    html = output.read_text()

    assert "testuser" in html
    assert "Test User" in html


def test_render_report_contains_stats(sample_summary, tmp_path):
    output = tmp_path / "test-report.html"
    render_report(sample_summary, output)
    html = output.read_text()

    assert "Commits" in html
    assert "Pull Requests" in html
    assert "Issues" in html
    assert "Reviews" in html


def test_render_report_contains_repos(sample_summary, tmp_path):
    output = tmp_path / "test-report.html"
    render_report(sample_summary, output)
    html = output.read_text()

    assert "testuser/myrepo" in html


def test_render_report_creates_parent_dirs(sample_summary, tmp_path):
    output = tmp_path / "nested" / "dir" / "report.html"
    render_report(sample_summary, output)

    assert output.exists()


def test_render_report_valid_html(sample_summary, tmp_path):
    output = tmp_path / "test-report.html"
    render_report(sample_summary, output)
    html = output.read_text()

    assert html.startswith("<!DOCTYPE html>")
    assert "</html>" in html
