.PHONY: test test-cov test-integration

test:
	uv run pytest

test-cov:
	uv run pytest --cov=. --cov-report=term-missing

test-integration:
	uv run pytest -m integration
