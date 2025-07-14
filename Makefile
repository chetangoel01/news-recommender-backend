# News Recommender Backend Makefile

.PHONY: help install test test-auth test-users test-coverage clean setup dev index-build index-update index-schedule

# Default target
help:
	@echo "News Recommender Backend - Available commands:"
	@echo ""
	@echo "Setup & Installation:"
	@echo "  install     - Install Python dependencies"
	@echo "  setup       - Verify database setup"
	@echo "  dev         - Start development server"
	@echo ""
	@echo "Testing:"
	@echo "  test           - Run all tests"
	@echo "  test-auth      - Run authentication tests only"
	@echo "  test-users     - Run user profile tests only"
	@echo "  test-articles  - Run content management tests only"
	@echo "  test-cov       - Run tests with coverage report"
	@echo "  test-fast      - Run tests without coverage (faster)"
	@echo ""
	@echo "FAISS Index Management (OPTIONAL - not used in current API):"
	@echo "  index-build    - Build complete FAISS index from database"
	@echo "  index-update   - Incrementally update FAISS index"
	@echo "  index-cleanup  - Remove deleted articles from index"
	@echo "  index-schedule - Start automated index maintenance"
	@echo "  index-stats    - Show index and database statistics"
	@echo ""
	@echo "Cleanup:"
	@echo "  clean       - Clean up test artifacts and cache"
	@echo "  clean-db    - Remove test database files"
	@echo "  clean-index    - Remove FAISS index files (optional cleanup)"

# Installation and setup
install:
	pip install -r requirements.txt

setup:
	@echo "Database tables are created automatically by the application"
	@echo "Run 'make test' to verify setup"

dev:
	uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# Testing targets
test:
	python run_tests.py all

test-auth:
	python run_tests.py auth

test-users:
	python run_tests.py users

test-articles:
	python run_tests.py articles

test-cov:
	python run_tests.py coverage

test-fast:
	python run_tests.py fast

# FAISS Index Management targets (OPTIONAL - not used in current API endpoints)
# These are kept for potential future integration when article scale exceeds pgvector limits
index-build:
	python -m pipeline.build_faiss_index

index-update:
	python -m pipeline.incremental_index_update

index-cleanup:
	python -m pipeline.incremental_index_update cleanup

index-schedule:
	python -m pipeline.index_scheduler --mode hourly

index-schedule-daily:
	python -m pipeline.index_scheduler --mode daily

index-stats:
	python -m pipeline.index_scheduler --mode on-demand

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

clean-index:
	rm -rf pipeline/embeddings/
	rm -rf pipeline/logs/

# Combined targets
fresh-test: clean test

setup-and-test: install setup test

# Development workflow
dev-setup: install setup
	@echo "✅ Development environment ready!"
	@echo "Run 'make dev' to start the server"
	@echo "Run 'make test' to run tests" 