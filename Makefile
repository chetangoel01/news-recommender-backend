# News Recommender Backend Makefile

.PHONY: help install test test-auth test-users test-coverage clean setup dev

# Default target
help:
	@echo "News Recommender Backend - Available commands:"
	@echo ""
	@echo "Setup & Installation:"
	@echo "  install     - Install Python dependencies"
	@echo "  setup       - Set up database tables"
	@echo "  dev         - Start development server"
	@echo ""
	@echo "Testing:"
	@echo "  test        - Run all tests"
	@echo "  test-auth   - Run authentication tests only"
	@echo "  test-users  - Run user profile tests only"
	@echo "  test-cov    - Run tests with coverage report"
	@echo "  test-fast   - Run tests without coverage (faster)"
	@echo ""
	@echo "Cleanup:"
	@echo "  clean       - Clean up test artifacts and cache"
	@echo "  clean-db    - Remove test database files"

# Installation and setup
install:
	pip install -r requirements.txt

setup:
	python create_tables.py

dev:
	uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# Testing targets
test:
	python run_tests.py all

test-auth:
	python run_tests.py auth

test-users:
	python run_tests.py users

test-cov:
	python run_tests.py coverage

test-fast:
	python run_tests.py fast

# Cleanup targets
clean:
	rm -rf __pycache__/
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

clean-db:
	rm -f test.db
	rm -f test.db-*

# Combined targets
fresh-test: clean test

setup-and-test: install setup test

# Development workflow
dev-setup: install setup
	@echo "✅ Development environment ready!"
	@echo "Run 'make dev' to start the server"
	@echo "Run 'make test' to run tests" 