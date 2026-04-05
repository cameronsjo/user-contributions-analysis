# ADR 0001: Initial Architecture

## Status

Accepted

## Context

We need a tool to pull a user's public contributions from GitHub (and eventually Gitea), normalize them into a common format, summarize them, and render visual reports.

## Decision

- **Python 3.12** with httpx for async API calls, Pydantic for data modeling, Jinja2 for HTML report rendering
- **Provider pattern** — each data source (GitHub, Gitea) implements a common protocol, returning normalized Pydantic models
- **CLI-first** with Click, static HTML output via Jinja2 templates
- **FastAPI + React** planned for later phases when interactive charts and a web UI are needed
- **No database** in v0.1.0 — fetch fresh each run. Caching layer can be added later

## Consequences

- Provider pattern makes adding Gitea (or GitLab, Codeberg, etc.) straightforward
- Normalized models mean summarization and rendering are provider-agnostic
- CLI-first means fast iteration before committing to a web framework
- No persistence means repeated runs hit the API each time (acceptable for v0.1.0)
