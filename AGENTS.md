# user-contributions-analysis

Pull a user's public contributions from GitHub and Gitea, summarize them, and generate static HTML reports.

## Tech Stack

- **Language:** Python 3.12
- **Dependencies:** httpx, Jinja2, Pydantic, Click, Rich
- **Package Manager:** uv
- **Linting:** ruff

## Commands

```bash
make dev       # Install dependencies
make test      # Run tests (pytest)
make lint      # Lint check (ruff check + ruff format --check)
make format    # Auto-format (ruff format + ruff check --fix)
make report    # Generate sample report
```

## Project Structure

```
src/contributions/       # Main package
  cli.py                 # Click CLI entrypoint
  config.py              # pydantic-settings configuration
  models.py              # Normalized contribution data models
  summarizer.py          # Contribution aggregation/summarization
  providers/             # Data source providers
    base.py              # Provider protocol
    github.py            # GitHub REST API provider
  rendering/             # Output renderers
    report.py            # Jinja2 HTML report renderer
    templates/           # Jinja2 templates
tests/                   # pytest test suite
```

## Conventions

- Provider pattern: each data source implements the `ContributionProvider` protocol
- All contribution data is normalized to provider-agnostic Pydantic models before summarization
- Async everywhere: providers use `httpx.AsyncClient`
- Config via environment variables with `.env` file support (pydantic-settings)

## Issue Tracking

This project tracks issues on GitHub. The `bd` (beads) tool was retired
(cadence-groundwork#138); a `.beads/` directory may still be present in this
repo, but it's dormant data, not the active issue queue — don't run `bd`
commands, and don't treat it as a task list.

Use `TodoWrite`/`TaskCreate` for in-session task tracking and open GitHub
issues for anything that needs follow-up beyond the session.

## Session Completion

When ending a work session, commit and push your changes, file GitHub issues
for remaining follow-up work, and confirm `git status` is clean before
signing off. See `cadence:outro` if available.
