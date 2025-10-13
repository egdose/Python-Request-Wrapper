# Makefile for RequestWrapper development

.PHONY: help install install-dev test lint format type-check clean build upload docs

help:
	@echo "RequestWrapper Development Commands:"
	@echo "  install      - Install package in development mode"
	@echo "  install-dev  - Install with development dependencies"
	@echo "  test         - Run tests with coverage"
	@echo "  lint         - Run linting checks"
	@echo "  format       - Format code with black and isort"
	@echo "  type-check   - Run type checking with mypy"
	@echo "  clean        - Clean build artifacts"
	@echo "  build        - Build distribution packages"
	@echo "  docs         - Generate documentation"

install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"

test:
	pytest --cov=src/request_wrapper --cov-report=html --cov-report=term-missing

test-verbose:
	pytest -v --cov=src/request_wrapper --cov-report=html --cov-report=term-missing

lint:
	flake8 src/ tests/

format:
	black src/ tests/
	isort src/ tests/

type-check:
	mypy src/

check-all: lint type-check test

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .mypy_cache/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

build: clean
	python -m build

upload:
	python -m twine upload dist/*

docs:
	@echo "Documentation is in README.md"

# Development workflow
dev-setup: install-dev
	@echo "Development environment setup complete!"
	@echo "Run 'make test' to run tests"
	@echo "Run 'make check-all' to run all checks"