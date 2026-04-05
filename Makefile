.PHONY: dev test lint format report clean

dev:
	uv sync

test:
	uv run pytest tests/ -v

lint:
	uv run ruff check src/ tests/
	uv run ruff format --check src/ tests/

format:
	uv run ruff format src/ tests/
	uv run ruff check --fix src/ tests/

report:
	uv run contributions cameronsjo

clean:
	rm -rf output/ .pytest_cache/ .ruff_cache/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
