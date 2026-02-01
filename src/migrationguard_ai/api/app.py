"""
FastAPI application factory and configuration.

This module creates and configures the FastAPI application with:
- CORS middleware
- Logging middleware
- Error handling middleware
- Dependency injection
- OpenAPI documentation
- Health check endpoints
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from migrationguard_ai.core.config import get_settings
from migrationguard_ai.core.logging import get_logger
from migrationguard_ai.api.middleware.logging import LoggingMiddleware
from migrationguard_ai.api.middleware.error_handler import ErrorHandlerMiddleware

logger = get_logger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager.
    
    Handles startup and shutdown events for the FastAPI application.
    """
    # Startup
    logger.info("Starting MigrationGuard AI API", environment=settings.ENVIRONMENT)
    
    # Initialize services here (database connections, Kafka producers, etc.)
    # These will be added as we implement the services
    
    yield
    
    # Shutdown
    logger.info("Shutting down MigrationGuard AI API")
    
    # Cleanup services here


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Returns:
        FastAPI: Configured FastAPI application instance
    """
    app = FastAPI(
        title="MigrationGuard AI",
        description="Production-grade agentic AI system for self-healing support during e-commerce migration",
        version="0.1.0",
        docs_url="/api/docs" if settings.ENVIRONMENT != "production" else None,
        redoc_url="/api/redoc" if settings.ENVIRONMENT != "production" else None,
        openapi_url="/api/openapi.json" if settings.ENVIRONMENT != "production" else None,
        lifespan=lifespan,
    )
    
    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add custom middleware
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(ErrorHandlerMiddleware)
    
    # Register exception handlers
    register_exception_handlers(app)
    
    # Register routes
    register_routes(app)
    
    return app


def register_exception_handlers(app: FastAPI) -> None:
    """
    Register custom exception handlers.
    
    Args:
        app: FastAPI application instance
    """
    
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        """Handle HTTP exceptions with structured error responses."""
        logger.warning(
            "HTTP exception",
            status_code=exc.status_code,
            detail=exc.detail,
            path=request.url.path,
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error_code": f"HTTP_{exc.status_code}",
                "error_message": exc.detail,
                "path": request.url.path,
            },
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        """Handle request validation errors with detailed error messages."""
        logger.warning(
            "Validation error",
            errors=exc.errors(),
            path=request.url.path,
        )
        
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error_code": "VALIDATION_ERROR",
                "error_message": "Request validation failed",
                "details": exc.errors(),
                "path": request.url.path,
            },
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Handle unexpected exceptions with generic error response."""
        logger.error(
            "Unexpected error",
            error=str(exc),
            error_type=type(exc).__name__,
            path=request.url.path,
            exc_info=True,
        )
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error_code": "INTERNAL_SERVER_ERROR",
                "error_message": "An unexpected error occurred",
                "path": request.url.path,
            },
        )


def register_routes(app: FastAPI) -> None:
    """
    Register API routes.
    
    Args:
        app: FastAPI application instance
    """
    # Health check endpoints
    @app.get("/health", tags=["Health"])
    async def health_check() -> dict:
        """
        Basic health check endpoint.
        
        Returns:
            dict: Health status
        """
        return {
            "status": "healthy",
            "service": "migrationguard-ai",
            "version": "0.1.0",
        }
    
    @app.get("/health/ready", tags=["Health"])
    async def readiness_check() -> dict:
        """
        Readiness check endpoint.
        
        Checks if the service is ready to accept requests.
        This should verify connections to dependencies (database, Kafka, etc.).
        
        Returns:
            dict: Readiness status
        """
        # TODO: Add actual dependency checks
        # - Database connection
        # - Kafka connection
        # - Redis connection
        # - Elasticsearch connection
        
        return {
            "status": "ready",
            "service": "migrationguard-ai",
            "checks": {
                "database": "healthy",
                "kafka": "healthy",
                "redis": "healthy",
                "elasticsearch": "healthy",
            },
        }
    
    @app.get("/health/live", tags=["Health"])
    async def liveness_check() -> dict:
        """
        Liveness check endpoint.
        
        Checks if the service is alive and responding.
        
        Returns:
            dict: Liveness status
        """
        return {
            "status": "alive",
            "service": "migrationguard-ai",
        }
    
    @app.get("/metrics", tags=["Monitoring"])
    async def prometheus_metrics():
        """
        Prometheus metrics endpoint.
        
        Exposes metrics in Prometheus text format for scraping.
        
        Returns:
            Response: Metrics in Prometheus format
        """
        from fastapi.responses import Response
        from migrationguard_ai.services.metrics_exporter import get_metrics_exporter
        
        exporter = get_metrics_exporter()
        metrics_data = exporter.get_metrics()
        
        return Response(
            content=metrics_data,
            media_type="text/plain; version=0.0.4; charset=utf-8"
        )
    
    # Import and register API routes
    from migrationguard_ai.api.routes import signals, webhooks, approvals, metrics, issues, auth
    
    app.include_router(auth.router, prefix="/api/v1", tags=["Authentication"])
    app.include_router(signals.router, prefix="/api/v1", tags=["Signals"])
    app.include_router(webhooks.router, prefix="/api/v1", tags=["Webhooks"])
    app.include_router(approvals.router, tags=["Approvals"])
    app.include_router(metrics.router, tags=["Metrics"])
    app.include_router(issues.router, tags=["Issues"])


# Create the application instance
app = create_app()
