@echo off
REM MigrationGuard AI - Infrastructure Setup Script for Windows

echo ============================================================
echo MigrationGuard AI - Infrastructure Setup
echo ============================================================
echo.

REM Check if Docker is running
docker --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not installed or not in PATH
    echo Please install Docker Desktop from https://www.docker.com/products/docker-desktop/
    exit /b 1
)

echo [1/6] Checking Docker status...
docker ps >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not running
    echo Please start Docker Desktop and try again
    exit /b 1
)
echo   OK Docker is running

echo.
echo [2/6] Starting infrastructure services...
docker-compose up -d
if errorlevel 1 (
    echo [ERROR] Failed to start services
    exit /b 1
)
echo   OK Services started

echo.
echo [3/6] Waiting for services to be healthy (30 seconds)...
timeout /t 30 /nobreak >nul
echo   OK Wait complete

echo.
echo [4/6] Checking infrastructure connectivity...
uv run python scripts/check_infrastructure.py
if errorlevel 1 (
    echo [WARNING] Some services may not be ready yet
    echo You can check status with: docker-compose ps
    echo And retry with: docker-compose restart
)

echo.
echo [5/6] Running database migrations...
uv run alembic upgrade head
if errorlevel 1 (
    echo [ERROR] Database migration failed
    echo Check PostgreSQL logs: docker-compose logs postgres
    exit /b 1
)
echo   OK Migrations applied

echo.
echo [6/6] Setting up Kafka topics and Elasticsearch indices...
uv run python scripts/setup_infrastructure.py
if errorlevel 1 (
    echo [ERROR] Infrastructure setup failed
    exit /b 1
)

echo.
echo ============================================================
echo Setup Complete!
echo ============================================================
echo.
echo Services running:
echo   - PostgreSQL:     localhost:5432
echo   - Redis:          localhost:6379
echo   - Kafka:          localhost:9092
echo   - Elasticsearch:  http://localhost:9200
echo   - Kibana:         http://localhost:5601
echo   - Prometheus:     http://localhost:9090
echo   - Grafana:        http://localhost:3001
echo.
echo Next steps:
echo   1. Configure ANTHROPIC_API_KEY in .env file
echo   2. Run demo: uv run python demo_agent_system.py
echo   3. Run tests: uv run pytest tests/unit/ -v
echo   4. Start API: uv run uvicorn src.migrationguard_ai.api.app:app --reload
echo.
echo To stop services: docker-compose down
echo To view logs: docker-compose logs [service-name]
echo.
