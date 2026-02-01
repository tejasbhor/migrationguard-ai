"""
Error handling middleware for FastAPI.

This middleware provides centralized error handling and recovery
for the API layer.
"""

from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from migrationguard_ai.core.logging import get_logger

logger = get_logger(__name__)


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """
    Middleware to handle errors and provide graceful degradation.
    
    This middleware catches errors that escape route handlers and
    ensures they are properly logged and handled.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process the request with error handling.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware or route handler
            
        Returns:
            Response: HTTP response
        """
        try:
            response = await call_next(request)
            return response
            
        except Exception as e:
            # Log the error with context
            logger.error(
                "Unhandled error in request processing",
                path=request.url.path,
                method=request.method,
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )
            
            # Re-raise to be handled by exception handlers
            raise
