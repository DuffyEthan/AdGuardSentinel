.PHONY: help check format type lint test clean install ci-check format-check

PYTHON = python3.11
PIP = pip
PYTEST = pytest
BLACK = black
FLAKE8 = flake8
MYPY = mypy

help:
		@echo "Available commands:"
		@echo "  make check     - Run all code quality checks"
		@echo "  make format    - Format code with black"
		@echo "  make lint      - Run flake8 linting"
		@echo "  make type      - Run mypy type checking"
		@echo "  make test      - Run tests"
		@echo "  make ci-check  - Run CI-style checks"
		@echo "  make install   - Install dependencies"
		@echo "  make clean     - Clean up generated files"

install:
		$(PIP) install -r requirements.txt
		$(PIP) install black flake8 mypy pytest pytest-cov

format: 
		$(BLACK) .

format-check:
		$(BLACK) --check .

lint:
		$(FLAKE8) . --count --select=E9,F63,F7,F82 --show-source --statistics
		$(FLAKE8) . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics

type:
		$(MYPY) --ignore-missing-imports app/ db/ tests/

type-report:
		$(MYPY) --ignore-missing-imports --html-report mypy-html-report app/ db/ tests/

test:
		$(PYTEST) tests/ -v --cov=./ --cov-report=html

test-coverage: 
		$(PYTEST) tests/ -v --cov=./ --cov-report=xml  --cov-report=html

check: format-check lint type test

ci-check: format-check lint type

fix: format
		@echo "Code formatted, run "make lint" to see the remaining issues."

clean:
		rm -rf .mypy_cache/
		rm -rf mypy-html-report/
		rm -rf .pytest_cache/
		rm -rf htmlcov/
		rm -rf .coverage
		rm -rf coverage.xml
		find . -type f -name "*.pyc" -delete
		find . -type d -name "__pycache__" -delete	 
