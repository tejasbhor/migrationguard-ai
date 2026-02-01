"""
Webhook receivers for external support systems.

This module provides webhook endpoints for:
- Zendesk ticket events
- Intercom conversation events
- Freshdesk ticket events

Each webhook includes signature verification for security.
"""

import hashlib
import hmac
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Header, Request, status
from pydantic import BaseModel, Field

from migrationguard_ai.core.config import get_settings
from migrationguard_ai.core.logging import get_logger
from migrationguard_ai.services.kafka_producer import KafkaProducerWrapper
from migrationguard_ai.services.signal_normalizer import SignalNormalizer
from migrationguard_ai.api.dependencies import (
    get_kafka_producer_dependency,
    get_signal_normalizer_dependency,
)

logger = get_logger(__name__)
settings = get_settings()

router = APIRouter()


# Response models
class WebhookResponse(BaseModel):
    """Standard webhook response."""
    
    status: str = Field(..., description="Processing status")
    message: str = Field(..., description="Status message")
    signal_id: str | None = Field(None, description="Created signal ID if applicable")


# Webhook signature verification
def verify_zendesk_signature(payload: bytes, signature: str, secret: str) -> bool:
    """
    Verify Zendesk webhook signature.
    
    Args:
        payload: Raw request body
        signature: Signature from X-Zendesk-Webhook-Signature header
        secret: Webhook secret key
        
    Returns:
        bool: True if signature is valid
    """
    if not secret:
        logger.warning("Zendesk webhook secret not configured")
        return False
    
    expected_signature = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature, expected_signature)


def verify_intercom_signature(payload: bytes, signature: str, secret: str) -> bool:
    """
    Verify Intercom webhook signature.
    
    Args:
        payload: Raw request body
        signature: Signature from X-Hub-Signature header
        secret: Webhook secret key
        
    Returns:
        bool: True if signature is valid
    """
    if not secret:
        logger.warning("Intercom webhook secret not configured")
        return False
    
    expected_signature = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha1
    ).hexdigest()
    
    # Intercom sends signature as "sha1=<hash>"
    if signature.startswith("sha1="):
        signature = signature[5:]
    
    return hmac.compare_digest(signature, expected_signature)


def verify_freshdesk_signature(payload: bytes, signature: str, secret: str) -> bool:
    """
    Verify Freshdesk webhook signature.
    
    Args:
        payload: Raw request body
        signature: Signature from X-Freshdesk-Signature header
        secret: Webhook secret key
        
    Returns:
        bool: True if signature is valid
    """
    if not secret:
        logger.warning("Freshdesk webhook secret not configured")
        return False
    
    expected_signature = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature, expected_signature)


@router.post(
    "/webhooks/zendesk",
    response_model=WebhookResponse,
    status_code=status.HTTP_200_OK,
    summary="Zendesk webhook receiver",
    description="Receive ticket events from Zendesk",
)
async def zendesk_webhook(
    request: Request,
    kafka_producer: KafkaProducerWrapper = Depends(get_kafka_producer_dependency),
    normalizer: SignalNormalizer = Depends(get_signal_normalizer_dependency),
    x_zendesk_webhook_signature: str | None = Header(None, alias="X-Zendesk-Webhook-Signature"),
) -> WebhookResponse:
    """
    Receive and process Zendesk webhook events.
    
    Zendesk sends webhook events for ticket creation, updates, and status changes.
    
    Args:
        request: FastAPI request object
        kafka_producer: Kafka producer service (injected)
        normalizer: Signal normalizer service (injected)
        x_zendesk_webhook_signature: Webhook signature for verification
        
    Returns:
        WebhookResponse: Processing confirmation
        
    Raises:
        HTTPException: If signature verification fails or processing fails
    """
    try:
        # Read raw body for signature verification
        body = await request.body()
        
        # Verify signature (skip in development if secret not configured)
        webhook_secret = getattr(settings, "zendesk_webhook_secret", "")
        if webhook_secret and x_zendesk_webhook_signature:
            if not verify_zendesk_signature(body, x_zendesk_webhook_signature, webhook_secret):
                logger.warning("Invalid Zendesk webhook signature")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid webhook signature",
                )
        
        # Parse JSON payload
        payload = await request.json()
        
        logger.info(
            "Zendesk webhook received",
            ticket_id=payload.get("ticket", {}).get("id"),
            event_type=payload.get("event_type"),
        )
        
        # Normalize signal
        signal = normalizer.normalize("zendesk", payload)
        
        # Publish to Kafka
        await kafka_producer.send(
            topic="signals.normalized",
            message=signal.model_dump(mode="json"),
            key=signal.merchant_id,
        )
        
        logger.info(
            "Zendesk signal published",
            signal_id=signal.signal_id,
            merchant_id=signal.merchant_id,
        )
        
        return WebhookResponse(
            status="accepted",
            message="Zendesk webhook processed successfully",
            signal_id=signal.signal_id,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to process Zendesk webhook", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process webhook",
        )


@router.post(
    "/webhooks/intercom",
    response_model=WebhookResponse,
    status_code=status.HTTP_200_OK,
    summary="Intercom webhook receiver",
    description="Receive conversation events from Intercom",
)
async def intercom_webhook(
    request: Request,
    kafka_producer: KafkaProducerWrapper = Depends(get_kafka_producer_dependency),
    normalizer: SignalNormalizer = Depends(get_signal_normalizer_dependency),
    x_hub_signature: str | None = Header(None, alias="X-Hub-Signature"),
) -> WebhookResponse:
    """
    Receive and process Intercom webhook events.
    
    Intercom sends webhook events for conversation creation, updates, and user messages.
    
    Args:
        request: FastAPI request object
        kafka_producer: Kafka producer service (injected)
        normalizer: Signal normalizer service (injected)
        x_hub_signature: Webhook signature for verification
        
    Returns:
        WebhookResponse: Processing confirmation
        
    Raises:
        HTTPException: If signature verification fails or processing fails
    """
    try:
        # Read raw body for signature verification
        body = await request.body()
        
        # Verify signature (skip in development if secret not configured)
        webhook_secret = getattr(settings, "intercom_webhook_secret", "")
        if webhook_secret and x_hub_signature:
            if not verify_intercom_signature(body, x_hub_signature, webhook_secret):
                logger.warning("Invalid Intercom webhook signature")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid webhook signature",
                )
        
        # Parse JSON payload
        payload = await request.json()
        
        logger.info(
            "Intercom webhook received",
            conversation_id=payload.get("data", {}).get("item", {}).get("id"),
            topic=payload.get("topic"),
        )
        
        # Normalize signal
        signal = normalizer.normalize("intercom", payload)
        
        # Publish to Kafka
        await kafka_producer.send(
            topic="signals.normalized",
            message=signal.model_dump(mode="json"),
            key=signal.merchant_id,
        )
        
        logger.info(
            "Intercom signal published",
            signal_id=signal.signal_id,
            merchant_id=signal.merchant_id,
        )
        
        return WebhookResponse(
            status="accepted",
            message="Intercom webhook processed successfully",
            signal_id=signal.signal_id,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to process Intercom webhook", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process webhook",
        )


@router.post(
    "/webhooks/freshdesk",
    response_model=WebhookResponse,
    status_code=status.HTTP_200_OK,
    summary="Freshdesk webhook receiver",
    description="Receive ticket events from Freshdesk",
)
async def freshdesk_webhook(
    request: Request,
    kafka_producer: KafkaProducerWrapper = Depends(get_kafka_producer_dependency),
    normalizer: SignalNormalizer = Depends(get_signal_normalizer_dependency),
    x_freshdesk_signature: str | None = Header(None, alias="X-Freshdesk-Signature"),
) -> WebhookResponse:
    """
    Receive and process Freshdesk webhook events.
    
    Freshdesk sends webhook events for ticket creation, updates, and status changes.
    
    Args:
        request: FastAPI request object
        kafka_producer: Kafka producer service (injected)
        normalizer: Signal normalizer service (injected)
        x_freshdesk_signature: Webhook signature for verification
        
    Returns:
        WebhookResponse: Processing confirmation
        
    Raises:
        HTTPException: If signature verification fails or processing fails
    """
    try:
        # Read raw body for signature verification
        body = await request.body()
        
        # Verify signature (skip in development if secret not configured)
        webhook_secret = getattr(settings, "freshdesk_webhook_secret", "")
        if webhook_secret and x_freshdesk_signature:
            if not verify_freshdesk_signature(body, x_freshdesk_signature, webhook_secret):
                logger.warning("Invalid Freshdesk webhook signature")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid webhook signature",
                )
        
        # Parse JSON payload
        payload = await request.json()
        
        logger.info(
            "Freshdesk webhook received",
            ticket_id=payload.get("ticket_id"),
            event_type=payload.get("event_type"),
        )
        
        # Normalize signal
        signal = normalizer.normalize("freshdesk", payload)
        
        # Publish to Kafka
        await kafka_producer.send(
            topic="signals.normalized",
            message=signal.model_dump(mode="json"),
            key=signal.merchant_id,
        )
        
        logger.info(
            "Freshdesk signal published",
            signal_id=signal.signal_id,
            merchant_id=signal.merchant_id,
        )
        
        return WebhookResponse(
            status="accepted",
            message="Freshdesk webhook processed successfully",
            signal_id=signal.signal_id,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to process Freshdesk webhook", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process webhook",
        )
