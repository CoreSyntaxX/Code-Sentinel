# SourceSentinel Makefile
# Provides convenient commands for installation and running

.PHONY: help install install-dev install-web install-github test clean run scan

# Default target
help:
	@echo "SourceSentinel - Multi-language source code security scanner"
	@echo ""
	@echo "Available commands:"
	@echo "  make install          - Install the package in editable mode"
	@echo "  make install-dev      - Install with development dependencies"
	@echo "  make install-web      - Install with web crawler dependencies"
	@echo "  make install-github  - Install with GitHub integration"
	@echo "  make install-all     - Install all dependencies"
	@echo "  make test            - Run the test suite"
	@echo "  make test-cov        - Run tests with coverage report"
	@echo "  make lint            - Run code linters"
	@echo "  make format          - Format code"
	@echo "  make clean           - Remove build artifacts"
	@echo "  make run             - Run the scanner"
	@echo "  make scan            - Run a quick scan on test_project"
	@echo "  make docker-build    - Build Docker image"
	@echo "  make docker-run      - Run scanner in Docker"

# Installation commands
install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"

install-web:
	pip install -e ".[web]"

install-github:
	pip install -e ".[github]"

install-all:
	pip install -e ".[all]"

# Development commands
test:
	pytest tests/ -v

test-cov:
	pytest tests/ --cov=src --cov-report=html --cov-report=term

test-unit:
	pytest tests/unit/ -v

test-integration:
	pytest tests/integration/ -v

lint:
	flake8 src/ tests/ --max-line-length=100 --ignore=E203,W503

format:
	black src/ tests/ --line-length=100
	isort src/ tests/ --profile=black

typecheck:
	mypy src/ --ignore-missing-imports

# Run commands
run:
	python -m src.main

scan:
	python -m src.main scan test_project/

scan-html:
	python -m src.main scan test_project/ --format html --output reports/scan_report.html

# Docker commands
docker-build:
	docker build -t sourcesentinel:latest .

docker-run:
	docker run --rm -v $(PWD):/app sourcesentinel:latest scan /app/test_project/

# Cleanup
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .mypy_cache/
	rm -rf __pycache__/
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name ".DS_Store" -delete

