"""
Signal submission and query API endpoints.

This module provides REST API endpoints for:
- Submitting signals to the system
- Retrieving signal details
- Searching signals with filtering
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from migrationguard_ai.core.schemas import Signal
from migrationguard_ai.core.logging import get_logger
from migrationguard_ai.services.kafka_producer import KafkaProducerWrapper
from migrationguard_ai.api.dependencies import get_kafka_producer_dependency

logger = get_logger(__name__)

router = APIRouter()


# Request/Response models
class SignalSubmitRequest(BaseModel):
    """Request model for signal submission."""
    
    source: str = Field(..., description="Signal source type")
    merchant_id: str = Field(..., description="Merchant identifier")
    migration_stage: Optional[str] = Field(None, description="Current migration stage")
    severity: str = Field(..., description="Signal severity level")
    error_message: Optional[str] = Field(None, description="Error message if applicable")
    error_code: Optional[str] = Field(None, description="Error code if applicable")
    affected_resource: Optional[str] = Field(None, description="Affected resource identifier")
    raw_data: dict = Field(default_factory=dict, description="Raw signal data")
    context: dict = Field(default_factory=dict, description="Additional context")


class SignalSubmitResponse(BaseModel):
    """Response model for signal submission."""
    
    signal_id: str = Field(..., description="Unique signal identifier")
    status: str = Field(..., description="Submission status")
    message: str = Field(..., description="Status message")


class SignalResponse(BaseModel):
    """Response model for signal retrieval."""
    
    signal_id: str
    timestamp: str
    source: str
    merchant_id: str
    migration_stage: Optional[str]
    severity: str
    error_message: Optional[str]
    error_code: Optional[str]
    affected_resource: Optional[str]
    raw_data: dict
    context: dict


class SignalSearchResponse(BaseModel):
    """Response model for signal search."""
    
    signals: list[SignalResponse]
    total: int
    page: int
    page_size: int


@router.post(
    "/signals/submit",
    response_model=SignalSubmitResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit a signal",
    description="Submit a signal to the MigrationGuard AI system for processing",
)
async def submit_signal(
    request: SignalSubmitRequest,
    kafka_producer: KafkaProducerWrapper = Depends(get_kafka_producer_dependency),
) -> SignalSubmitResponse:
    """
    Submit a signal to the system.
    
    The signal will be normalized and published to Kafka for asynchronous processing.
    
    Args:
        request: Signal submission request
        kafka_producer: Kafka producer service (injected)
        
    Returns:
        SignalSubmitResponse: Submission confirmation with signal ID
        
    Raises:
        HTTPException: If signal submission fails
    """
    try:
        # Create Signal from request
        signal = Signal(
            source=request.source,  # type: ignore
            merchant_id=request.merchant_id,
            migration_stage=request.migration_stage,
            severity=request.severity,  # type: ignore
            error_message=request.error_message,
            error_code=request.error_code,
            affected_resource=request.affected_resource,
            raw_data=request.raw_data,
            context=request.context,
        )
        
        logger.info(
            "Signal submitted",
            signal_id=signal.signal_id,
            source=signal.source,
            merchant_id=signal.merchant_id,
            severity=signal.severity,
        )
        
        # Publish signal to Kafka
        await kafka_producer.send(
            topic="signals.normalized",
            message=signal.model_dump(mode="json"),
            key=signal.merchant_id,
        )
        
        logger.info(
            "Signal published to Kafka",
            signal_id=signal.signal_id,
            topic="signals.normalized",
        )
        
        return SignalSubmitResponse(
            signal_id=signal.signal_id,
            status="accepted",
            message="Signal accepted for processing",
        )
        
    except ValueError as e:
        logger.warning("Invalid signal data", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid signal data: {str(e)}",
        )
    except Exception as e:
        logger.error("Failed to submit signal", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit signal",
        )


@router.get(
    "/signals/{signal_id}",
    response_model=SignalResponse,
    summary="Get signal by ID",
    description="Retrieve a signal by its unique identifier",
)
async def get_signal(signal_id: UUID) -> SignalResponse:
    """
    Retrieve a signal by ID.
    
    Args:
        signal_id: Unique signal identifier
        
    Returns:
        SignalResponse: Signal details
        
    Raises:
        HTTPException: If signal not found
    """
    try:
        # TODO: Retrieve signal from database (will be implemented later)
        # signal = await signal_repository.get_by_id(signal_id)
        
        logger.info("Signal retrieved", signal_id=str(signal_id))
        
        # Placeholder response
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Signal {signal_id} not found",
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to retrieve signal", signal_id=str(signal_id), error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve signal",
        )


@router.get(
    "/signals/search",
    response_model=SignalSearchResponse,
    summary="Search signals",
    description="Search signals with filtering and pagination",
)
async def search_signals(
    merchant_id: Optional[str] = Query(None, description="Filter by merchant ID"),
    source: Optional[str] = Query(None, description="Filter by signal source"),
    severity: Optional[str] = Query(None, description="Filter by severity level"),
    start_date: Optional[str] = Query(None, description="Filter by start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="Filter by end date (ISO format)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=1000, description="Page size"),
) -> SignalSearchResponse:
    """
    Search signals with filtering.
    
    Args:
        merchant_id: Filter by merchant ID
        source: Filter by signal source
        severity: Filter by severity level
        start_date: Filter by start date
        end_date: Filter by end date
        page: Page number (1-indexed)
        page_size: Number of results per page
        
    Returns:
        SignalSearchResponse: Search results with pagination
        
    Raises:
        HTTPException: If search fails
    """
    try:
        logger.info(
            "Searching signals",
            merchant_id=merchant_id,
            source=source,
            severity=severity,
            start_date=start_date,
            end_date=end_date,
            page=page,
            page_size=page_size,
        )
        
        # TODO: Implement signal search (will be implemented later)
        # results = await signal_repository.search(
        #     merchant_id=merchant_id,
        #     source=source,
        #     severity=severity,
        #     start_date=start_date,
        #     end_date=end_date,
        #     page=page,
        #     page_size=page_size,
        # )
        
        # Placeholder response
        return SignalSearchResponse(
            signals=[],
            total=0,
            page=page,
            page_size=page_size,
        )
        
    except Exception as e:
        logger.error("Failed to search signals", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search signals",
        )
