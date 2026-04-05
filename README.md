# user-contributions-analysis

Pull a user's public contributions from GitHub (and eventually Gitea), summarize them, and generate a static HTML report.

## Getting Started

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) for dependency management

### Installation

```bash
uv sync
```

### Usage

```bash
uv run contributions <username>
```

Options:

- `--output <path>` — output file path (default: `output/<username>-report.html`)
- `--open` — open the report in your browser after generation

### Configuration

Copy `.env.example` to `.env` and optionally set:

- `GITHUB_TOKEN` — GitHub personal access token for higher rate limits (5000/hr vs 60/hr)

## Development

```bash
make dev       # Install dependencies
make test      # Run tests
make lint      # Run linter
make format    # Auto-format code
make report    # Generate a sample report
```

## License

MIT
