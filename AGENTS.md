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

<!-- BEGIN BEADS INTEGRATION v:1 profile:minimal hash:ca08a54f -->
## Beads Issue Tracker

This project uses **bd (beads)** for issue tracking. Run `bd prime` to see full workflow context and commands.

### Quick Reference

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --claim  # Claim work
bd close <id>         # Complete work
```

### Rules

- Use `bd` for ALL task tracking — do NOT use TodoWrite, TaskCreate, or markdown TODO lists
- Run `bd prime` for detailed command reference and session close protocol
- Use `bd remember` for persistent knowledge — do NOT use MEMORY.md files

## Session Completion

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **File issues for remaining work** - Create issues for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **PUSH TO REMOTE** - This is MANDATORY:
   ```bash
   git pull --rebase
   bd dolt push
   git push
   git status  # MUST show "up to date with origin"
   ```
5. **Clean up** - Clear stashes, prune remote branches
6. **Verify** - All changes committed AND pushed
7. **Hand off** - Provide context for next session

**CRITICAL RULES:**
- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing - that leaves work stranded locally
- NEVER say "ready to push when you are" - YOU must push
- If push fails, resolve and retry until it succeeds
<!-- END BEADS INTEGRATION -->
