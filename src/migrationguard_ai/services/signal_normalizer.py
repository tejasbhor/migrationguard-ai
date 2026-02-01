"""
Signal normalizer service.

This module transforms diverse signal formats from different sources
into a common Signal schema for unified processing.
"""

from datetime import datetime
from typing import Any

from migrationguard_ai.core.schemas import Signal
from migrationguard_ai.core.logging import get_logger

logger = get_logger(__name__)


class SignalNormalizer:
    """
    Normalizes signals from different sources into a common format.
    
    Supports:
    - Zendesk tickets
    - Intercom conversations
    - Freshdesk tickets
    - API failures
    - Checkout errors
    - Webhook failures
    """
    
    def normalize(self, source_type: str, raw_data: dict) -> Signal:
        """
        Normalize a signal from any source.
        
        Args:
            source_type: Type of signal source
            raw_data: Raw signal data from source
            
        Returns:
            Signal: Normalized signal
            
        Raises:
            ValueError: If source type is unsupported or data is invalid
        """
        normalizers = {
            "zendesk": self.normalize_zendesk,
            "intercom": self.normalize_intercom,
            "freshdesk": self.normalize_freshdesk,
            "api_failure": self.normalize_api_failure,
            "checkout_error": self.normalize_checkout_error,
            "webhook_failure": self.normalize_webhook_failure,
        }
        
        normalizer = normalizers.get(source_type)
        if not normalizer:
            raise ValueError(f"Unsupported source type: {source_type}")
        
        try:
            signal = normalizer(raw_data)
            logger.info(
                "Signal normalized",
                signal_id=signal.signal_id,
                source=signal.source,
                merchant_id=signal.merchant_id,
            )
            return signal
        except Exception as e:
            logger.error(
                "Failed to normalize signal",
                source_type=source_type,
                error=str(e),
                exc_info=True,
            )
            raise ValueError(f"Failed to normalize {source_type} signal: {str(e)}")
    
    def normalize_zendesk(self, raw_data: dict) -> Signal:
        """
        Normalize Zendesk ticket data.
        
        Args:
            raw_data: Raw Zendesk webhook payload
            
        Returns:
            Signal: Normalized signal
        """
        ticket = raw_data.get("ticket", {})
        
        # Extract merchant ID from custom fields or tags
        merchant_id = self._extract_merchant_id(ticket)
        
        # Determine severity from priority
        severity = self._map_zendesk_priority(ticket.get("priority", "normal"))
        
        # Extract error information from description
        description = ticket.get("description", "")
        error_message = description[:500] if description else None
        
        return Signal(
            source="support_ticket",
            merchant_id=merchant_id,
            migration_stage=self._extract_migration_stage(ticket),
            severity=severity,
            error_message=error_message,
            error_code=None,
            affected_resource=ticket.get("subject"),
            raw_data=raw_data,
            context={
                "ticket_id": ticket.get("id"),
                "status": ticket.get("status"),
                "requester_id": ticket.get("requester_id"),
                "created_at": ticket.get("created_at"),
            },
        )
    
    def normalize_intercom(self, raw_data: dict) -> Signal:
        """
        Normalize Intercom conversation data.
        
        Args:
            raw_data: Raw Intercom webhook payload
            
        Returns:
            Signal: Normalized signal
        """
        data = raw_data.get("data", {})
        item = data.get("item", {})
        
        # Extract merchant ID from user data
        user = item.get("user", {})
        merchant_id = user.get("user_id") or user.get("id", "unknown")
        
        # Determine severity from conversation state
        severity = self._map_intercom_state(item.get("state", "open"))
        
        # Extract first message as error message
        conversation_parts = item.get("conversation_parts", {}).get("conversation_parts", [])
        error_message = None
        if conversation_parts:
            error_message = conversation_parts[0].get("body", "")[:500]
        
        return Signal(
            source="support_ticket",
            merchant_id=merchant_id,
            migration_stage=None,
            severity=severity,
            error_message=error_message,
            error_code=None,
            affected_resource=item.get("id"),
            raw_data=raw_data,
            context={
                "conversation_id": item.get("id"),
                "state": item.get("state"),
                "created_at": item.get("created_at"),
            },
        )
    
    def normalize_freshdesk(self, raw_data: dict) -> Signal:
        """
        Normalize Freshdesk ticket data.
        
        Args:
            raw_data: Raw Freshdesk webhook payload
            
        Returns:
            Signal: Normalized signal
        """
        ticket = raw_data.get("ticket", raw_data)
        
        # Extract merchant ID from custom fields
        merchant_id = self._extract_merchant_id(ticket)
        
        # Determine severity from priority
        severity = self._map_freshdesk_priority(ticket.get("priority", 2))
        
        # Extract error information
        description = ticket.get("description_text", ticket.get("description", ""))
        error_message = description[:500] if description else None
        
        return Signal(
            source="support_ticket",
            merchant_id=merchant_id,
            migration_stage=self._extract_migration_stage(ticket),
            severity=severity,
            error_message=error_message,
            error_code=None,
            affected_resource=ticket.get("subject"),
            raw_data=raw_data,
            context={
                "ticket_id": ticket.get("ticket_id") or ticket.get("id"),
                "status": ticket.get("status"),
                "requester_id": ticket.get("requester_id"),
                "created_at": ticket.get("created_at"),
            },
        )
    
    def normalize_api_failure(self, raw_data: dict) -> Signal:
        """
        Normalize API failure data.
        
        Args:
            raw_data: Raw API failure data
            
        Returns:
            Signal: Normalized signal
        """
        merchant_id = raw_data.get("merchant_id", "unknown")
        
        # Determine severity from status code
        status_code = raw_data.get("status_code", 500)
        severity = self._map_http_status_to_severity(status_code)
        
        return Signal(
            source="api_failure",
            merchant_id=merchant_id,
            migration_stage=raw_data.get("migration_stage"),
            severity=severity,
            error_message=raw_data.get("error_message"),
            error_code=raw_data.get("error_code") or str(status_code),
            affected_resource=raw_data.get("endpoint"),
            raw_data=raw_data,
            context={
                "method": raw_data.get("method"),
                "status_code": status_code,
                "response_time_ms": raw_data.get("response_time_ms"),
            },
        )
    
    def normalize_checkout_error(self, raw_data: dict) -> Signal:
        """
        Normalize checkout error data.
        
        Args:
            raw_data: Raw checkout error data
            
        Returns:
            Signal: Normalized signal
        """
        merchant_id = raw_data.get("merchant_id", "unknown")
        
        # Checkout errors are always high severity
        severity = "high"
        
        return Signal(
            source="checkout_error",
            merchant_id=merchant_id,
            migration_stage=raw_data.get("migration_stage"),
            severity=severity,
            error_message=raw_data.get("error_message"),
            error_code=raw_data.get("error_code"),
            affected_resource=raw_data.get("cart_id") or raw_data.get("order_id"),
            raw_data=raw_data,
            context={
                "cart_value": raw_data.get("cart_value"),
                "payment_method": raw_data.get("payment_method"),
                "step": raw_data.get("checkout_step"),
            },
        )
    
    def normalize_webhook_failure(self, raw_data: dict) -> Signal:
        """
        Normalize webhook failure data.
        
        Args:
            raw_data: Raw webhook failure data
            
        Returns:
            Signal: Normalized signal
        """
        merchant_id = raw_data.get("merchant_id", "unknown")
        
        # Determine severity from failure count
        failure_count = raw_data.get("failure_count", 1)
        severity = "critical" if failure_count >= 5 else "high" if failure_count >= 3 else "medium"
        
        return Signal(
            source="webhook_failure",
            merchant_id=merchant_id,
            migration_stage=raw_data.get("migration_stage"),
            severity=severity,
            error_message=raw_data.get("error_message"),
            error_code=raw_data.get("error_code"),
            affected_resource=raw_data.get("webhook_url"),
            raw_data=raw_data,
            context={
                "webhook_event": raw_data.get("event_type"),
                "failure_count": failure_count,
                "last_attempt": raw_data.get("last_attempt"),
            },
        )
    
    # Helper methods
    
    def _extract_merchant_id(self, ticket_data: dict) -> str:
        """Extract merchant ID from ticket data."""
        # Try custom fields first
        custom_fields = ticket_data.get("custom_fields", {})
        if isinstance(custom_fields, dict):
            merchant_id = custom_fields.get("merchant_id")
            if merchant_id:
                return str(merchant_id)
        
        # Try tags
        tags = ticket_data.get("tags", [])
        for tag in tags:
            if tag.startswith("merchant:"):
                return tag.split(":", 1)[1]
        
        # Fallback to requester ID
        return str(ticket_data.get("requester_id", "unknown"))
    
    def _extract_migration_stage(self, ticket_data: dict) -> str | None:
        """Extract migration stage from ticket data."""
        # Try custom fields
        custom_fields = ticket_data.get("custom_fields", {})
        if isinstance(custom_fields, dict):
            stage = custom_fields.get("migration_stage")
            if stage:
                return str(stage)
        
        # Try tags
        tags = ticket_data.get("tags", [])
        for tag in tags:
            if tag.startswith("stage:"):
                return tag.split(":", 1)[1]
        
        return None
    
    def _map_zendesk_priority(self, priority: str) -> str:
        """Map Zendesk priority to severity."""
        mapping = {
            "urgent": "critical",
            "high": "high",
            "normal": "medium",
            "low": "low",
        }
        return mapping.get(priority, "medium")
    
    def _map_freshdesk_priority(self, priority: int) -> str:
        """Map Freshdesk priority (1-4) to severity."""
        mapping = {
            1: "low",
            2: "medium",
            3: "high",
            4: "critical",
        }
        return mapping.get(priority, "medium")
    
    def _map_intercom_state(self, state: str) -> str:
        """Map Intercom conversation state to severity."""
        mapping = {
            "open": "medium",
            "snoozed": "low",
            "closed": "low",
        }
        return mapping.get(state, "medium")
    
    def _map_http_status_to_severity(self, status_code: int) -> str:
        """Map HTTP status code to severity."""
        if status_code >= 500:
            return "critical"
        elif status_code >= 400:
            return "high"
        elif status_code >= 300:
            return "medium"
        else:
            return "low"


# Singleton instance
_normalizer: SignalNormalizer | None = None


def get_signal_normalizer() -> SignalNormalizer:
    """
    Get the singleton signal normalizer instance.
    
    Returns:
        SignalNormalizer: Signal normalizer instance
    """
    global _normalizer
    if _normalizer is None:
        _normalizer = SignalNormalizer()
    return _normalizer
