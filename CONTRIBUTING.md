# Contributing

Thanks for your interest in contributing!

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone git@github.com:<your-username>/user-contributions-analysis.git`
3. Install dependencies: `uv sync`
4. Create a branch: `git checkout -b my-feature`

## Development

```bash
make dev       # Install dependencies
make test      # Run tests
make lint      # Check linting
make format    # Auto-format
```

## Commit Format

This project uses [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` — new feature
- `fix:` — bug fix
- `docs:` — documentation only
- `refactor:` — code change that neither fixes a bug nor adds a feature
- `test:` — adding or correcting tests
- `chore:` — maintenance tasks

## Pull Requests

1. Keep PRs focused — one feature or fix per PR
2. Ensure `make lint` and `make test` pass
3. Write tests for new functionality
4. Update documentation if needed

## Code of Conduct

Be respectful and constructive. We're all here to build something useful.
