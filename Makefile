.PHONY: help install dev-install test test-cov lint format type-check clean docker-up docker-down docker-logs migrate migrate-create run

help:
	@echo "MigrationGuard AI - Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install          Install production dependencies"
	@echo "  make dev-install      Install development dependencies"
	@echo ""
	@echo "Development:"
	@echo "  make run              Start the application"
	@echo "  make docker-up        Start infrastructure services"
	@echo "  make docker-down      Stop infrastructure services"
	@echo "  make docker-logs      View infrastructure logs"
	@echo ""
	@echo "Database:"
	@echo "  make migrate          Run database migrations"
	@echo "  make migrate-create   Create a new migration"
	@echo ""
	@echo "Testing:"
	@echo "  make test             Run all tests"
	@echo "  make test-cov         Run tests with coverage report"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint             Run linter (ruff)"
	@echo "  make format           Format code (black)"
	@echo "  make type-check       Run type checker (mypy)"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean            Remove generated files"

install:
	uv pip install -e .

dev-install:
	uv pip install -e ".[dev]"

test:
	pytest

test-cov:
	pytest --cov=src --cov-report=html --cov-report=term-missing

lint:
	ruff check src tests

format:
	black src tests

type-check:
	mypy src

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .pytest_cache .coverage htmlcov .mypy_cache .ruff_cache

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

migrate:
	alembic upgrade head

migrate-create:
	@read -p "Enter migration message: " msg; \
	alembic revision --autogenerate -m "$$msg"

run:
	uvicorn migrationguard_ai.api.main:app --reload --host 0.0.0.0 --port 8000
