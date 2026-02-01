"""
Unit tests for signal ingestion system.

Tests:
- Webhook endpoints with sample payloads
- Signal normalization for each source type
- Error handling for malformed requests

Validates: Requirements 1.6, 14.2, 17.2
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from migrationguard_ai.api.app import create_app
from migrationguard_ai.services.signal_normalizer import SignalNormalizer


@pytest.fixture
def mock_kafka_producer():
    """Mock Kafka producer for testing."""
    producer = AsyncMock()
    producer.send = AsyncMock()
    producer.start = AsyncMock()
    producer.stop = AsyncMock()
    producer._started = True
    return producer


@pytest.fixture
def client(mock_kafka_producer):
    """Create test client for API with mocked Kafka producer."""
    app = create_app()
    
    # Override the Kafka producer dependency
    async def override_kafka_producer():
        yield mock_kafka_producer
    
    from migrationguard_ai.api import dependencies
    app.dependency_overrides[dependencies.get_kafka_producer_dependency] = override_kafka_producer
    
    return TestClient(app)


# Sample webhook payloads
SAMPLE_ZENDESK_PAYLOAD = {
    "ticket": {
        "id": 12345,
        "subject": "API Error: 500 Internal Server Error",
        "description": "Getting 500 errors when calling /api/products",
        "priority": "high",
        "status": "open",
        "requester_id": 67890,
        "created_at": "2024-01-15T10:30:00Z",
        "custom_fields": {
            "merchant_id": "merchant_123",
            "migration_stage": "testing",
        },
        "tags": ["api", "error", "migration"],
    },
    "event_type": "ticket.created",
}

SAMPLE_INTERCOM_PAYLOAD = {
    "topic": "conversation.user.created",
    "data": {
        "item": {
            "id": "conv_123",
            "state": "open",
            "created_at": 1705315800,
            "user": {
                "id": "user_456",
                "user_id": "merchant_456",
            },
            "conversation_parts": {
                "conversation_parts": [
                    {
                        "body": "Checkout is broken after migration",
                        "created_at": 1705315800,
                    }
                ]
            },
        }
    },
}

SAMPLE_FRESHDESK_PAYLOAD = {
    "ticket_id": 54321,
    "subject": "Webhook delivery failures",
    "description_text": "Webhooks are not being delivered to our endpoint",
    "priority": 3,
    "status": 2,
    "requester_id": 98765,
    "created_at": "2024-01-15T10:30:00Z",
    "custom_fields": {
        "merchant_id": "merchant_789",
        "migration_stage": "production",
    },
    "event_type": "ticket_created",
}


class TestWebhookEndpoints:
    """Test webhook endpoint functionality."""
    
    def test_zendesk_webhook_success(self, client):
        """Test Zendesk webhook with valid payload."""
        response = client.post(
            "/api/v1/webhooks/zendesk",
            json=SAMPLE_ZENDESK_PAYLOAD,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "accepted"
        assert "signal_id" in data
    
    def test_intercom_webhook_success(self, client):
        """Test Intercom webhook with valid payload."""
        response = client.post(
            "/api/v1/webhooks/intercom",
            json=SAMPLE_INTERCOM_PAYLOAD,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "accepted"
        assert "signal_id" in data
    
    def test_freshdesk_webhook_success(self, client):
        """Test Freshdesk webhook with valid payload."""
        response = client.post(
            "/api/v1/webhooks/freshdesk",
            json=SAMPLE_FRESHDESK_PAYLOAD,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "accepted"
        assert "signal_id" in data


class TestSignalNormalizer:
    """Test signal normalization for each source type."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.normalizer = SignalNormalizer()
    
    def test_normalize_zendesk_ticket(self):
        """Test normalization of Zendesk ticket."""
        signal = self.normalizer.normalize("zendesk", SAMPLE_ZENDESK_PAYLOAD)
        
        assert signal.source == "support_ticket"
        assert signal.merchant_id == "merchant_123"
        assert signal.migration_stage == "testing"
        assert signal.severity == "high"
        assert signal.error_message is not None
        assert "500 errors" in signal.error_message
        assert signal.context["ticket_id"] == 12345
    
    def test_normalize_intercom_conversation(self):
        """Test normalization of Intercom conversation."""
        signal = self.normalizer.normalize("intercom", SAMPLE_INTERCOM_PAYLOAD)
        
        assert signal.source == "support_ticket"
        assert signal.merchant_id == "merchant_456"
        assert signal.severity == "medium"
        assert signal.error_message is not None
        assert "Checkout" in signal.error_message
        assert signal.context["conversation_id"] == "conv_123"
    
    def test_normalize_freshdesk_ticket(self):
        """Test normalization of Freshdesk ticket."""
        signal = self.normalizer.normalize("freshdesk", SAMPLE_FRESHDESK_PAYLOAD)
        
        assert signal.source == "support_ticket"
        assert signal.merchant_id == "merchant_789"
        assert signal.migration_stage == "production"
        assert signal.severity == "high"
        assert signal.error_message is not None
        assert "Webhook" in signal.error_message
        # Freshdesk uses ticket_id not id
        assert signal.context["ticket_id"] == 54321
    
    def test_normalize_api_failure(self):
        """Test normalization of API failure."""
        api_failure_data = {
            "merchant_id": "merchant_api",
            "status_code": 500,
            "error_message": "Internal Server Error",
            "error_code": "ERR_500",
            "endpoint": "/api/products",
            "method": "GET",
            "response_time_ms": 1500,
        }
        
        signal = self.normalizer.normalize("api_failure", api_failure_data)
        
        assert signal.source == "api_failure"
        assert signal.merchant_id == "merchant_api"
        assert signal.severity == "critical"
        assert signal.error_message == "Internal Server Error"
        assert signal.error_code == "ERR_500"
        assert signal.affected_resource == "/api/products"
        assert signal.context["status_code"] == 500
    
    def test_normalize_checkout_error(self):
        """Test normalization of checkout error."""
        checkout_error_data = {
            "merchant_id": "merchant_checkout",
            "error_message": "Payment gateway timeout",
            "error_code": "PAYMENT_TIMEOUT",
            "cart_id": "cart_123",
            "cart_value": 150.00,
            "payment_method": "credit_card",
            "checkout_step": "payment",
        }
        
        signal = self.normalizer.normalize("checkout_error", checkout_error_data)
        
        assert signal.source == "checkout_error"
        assert signal.merchant_id == "merchant_checkout"
        assert signal.severity == "high"
        assert signal.error_message == "Payment gateway timeout"
        assert signal.error_code == "PAYMENT_TIMEOUT"
        assert signal.affected_resource == "cart_123"
        assert signal.context["cart_value"] == 150.00
    
    def test_normalize_webhook_failure(self):
        """Test normalization of webhook failure."""
        webhook_failure_data = {
            "merchant_id": "merchant_webhook",
            "error_message": "Connection timeout",
            "error_code": "WEBHOOK_TIMEOUT",
            "webhook_url": "https://merchant.com/webhook",
            "event_type": "order.created",
            "failure_count": 3,
            "last_attempt": "2024-01-15T10:30:00Z",
        }
        
        signal = self.normalizer.normalize("webhook_failure", webhook_failure_data)
        
        assert signal.source == "webhook_failure"
        assert signal.merchant_id == "merchant_webhook"
        assert signal.severity == "high"
        assert signal.error_message == "Connection timeout"
        assert signal.error_code == "WEBHOOK_TIMEOUT"
        assert signal.affected_resource == "https://merchant.com/webhook"
        assert signal.context["failure_count"] == 3
    
    def test_normalize_unsupported_source(self):
        """Test normalization with unsupported source type."""
        with pytest.raises(ValueError, match="Unsupported source type"):
            self.normalizer.normalize("unknown_source", {})
    
    def test_normalize_with_missing_merchant_id(self):
        """Test normalization when merchant ID is missing."""
        minimal_zendesk = {
            "ticket": {
                "id": 999,
                "subject": "Test",
                "description": "Test description",
                "priority": "normal",
                "status": "open",
                "requester_id": 111,
            }
        }
        
        signal = self.normalizer.normalize("zendesk", minimal_zendesk)
        
        # Should fallback to requester_id
        assert signal.merchant_id == "111"
    
    def test_severity_mapping_zendesk(self):
        """Test severity mapping for Zendesk priorities."""
        test_cases = [
            ("urgent", "critical"),
            ("high", "high"),
            ("normal", "medium"),
            ("low", "low"),
        ]
        
        for priority, expected_severity in test_cases:
            payload = {
                "ticket": {
                    "id": 1,
                    "subject": "Test",
                    "description": "Test",
                    "priority": priority,
                    "status": "open",
                    "requester_id": 1,
                }
            }
            
            signal = self.normalizer.normalize("zendesk", payload)
            assert signal.severity == expected_severity
    
    def test_severity_mapping_freshdesk(self):
        """Test severity mapping for Freshdesk priorities."""
        test_cases = [
            (1, "low"),
            (2, "medium"),
            (3, "high"),
            (4, "critical"),
        ]
        
        for priority, expected_severity in test_cases:
            payload = {
                "ticket_id": 1,
                "subject": "Test",
                "description_text": "Test",
                "priority": priority,
                "status": 2,
                "requester_id": 1,
            }
            
            signal = self.normalizer.normalize("freshdesk", payload)
            assert signal.severity == expected_severity


class TestSignalSubmissionAPI:
    """Test signal submission API endpoint."""
    
    def test_submit_valid_signal(self, client):
        """Test submitting a valid signal."""
        request_data = {
            "source": "api_failure",
            "merchant_id": "test_merchant",
            "severity": "high",
            "error_message": "Test error",
            "error_code": "TEST_001",
            "raw_data": {"test": "data"},
            "context": {},
        }
        
        response = client.post("/api/v1/signals/submit", json=request_data)
        
        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "accepted"
        assert "signal_id" in data
    
    def test_submit_signal_missing_required_fields(self, client):
        """Test submitting signal with missing required fields."""
        request_data = {
            "source": "api_failure",
            # Missing merchant_id and severity
        }
        
        response = client.post("/api/v1/signals/submit", json=request_data)
        
        assert response.status_code == 422
        data = response.json()
        assert "error_code" in data
        assert "error_message" in data
    
    def test_submit_signal_invalid_source(self, client):
        """Test submitting signal with invalid source."""
        request_data = {
            "source": "invalid_source",
            "merchant_id": "test_merchant",
            "severity": "high",
            "raw_data": {},
            "context": {},
        }
        
        response = client.post("/api/v1/signals/submit", json=request_data)
        
        assert response.status_code == 422
    
    def test_submit_signal_invalid_severity(self, client):
        """Test submitting signal with invalid severity."""
        request_data = {
            "source": "api_failure",
            "merchant_id": "test_merchant",
            "severity": "invalid_severity",
            "raw_data": {},
            "context": {},
        }
        
        response = client.post("/api/v1/signals/submit", json=request_data)
        
        assert response.status_code == 422


class TestHealthEndpoints:
    """Test health check endpoints."""
    
    def test_health_endpoint(self, client):
        """Test basic health check."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "migrationguard-ai"
    
    def test_readiness_endpoint(self, client):
        """Test readiness check."""
        response = client.get("/health/ready")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert "checks" in data
    
    def test_liveness_endpoint(self, client):
        """Test liveness check."""
        response = client.get("/health/live")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"
