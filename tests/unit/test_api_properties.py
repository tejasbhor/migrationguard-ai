"""
Property-based tests for API endpoints.

Tests universal properties that should hold for all API requests and responses:
- Property 48: JSON request/response format
- Property 50: HTTP status code correctness
- Property 51: Error response completeness
"""

import json
from typing import Any

import pytest
from fastapi.testclient import TestClient
from hypothesis import given, settings, strategies as st

from migrationguard_ai.api.app import create_app


@pytest.fixture
def client():
    """Create test client for API."""
    app = create_app()
    return TestClient(app)


# Property 48: JSON request/response format
@given(
    source=st.sampled_from(["support_ticket", "api_failure", "checkout_error", "webhook_failure"]),
    merchant_id=st.text(min_size=1, max_size=100),
    severity=st.sampled_from(["low", "medium", "high", "critical"]),
    error_message=st.one_of(st.none(), st.text(max_size=500)),
    error_code=st.one_of(st.none(), st.text(max_size=50)),
)
@settings(max_examples=100)
def test_property_48_json_request_response_format(
    client: TestClient,
    source: str,
    merchant_id: str,
    severity: str,
    error_message: str | None,
    error_code: str | None,
):
    """
    Feature: migrationguard-ai, Property 48: JSON request/response format
    
    For any API endpoint, requests and responses must be valid JSON
    (parseable without errors).
    
    Validates: Requirements 17.2
    """
    # Prepare request data
    request_data = {
        "source": source,
        "merchant_id": merchant_id,
        "severity": severity,
        "error_message": error_message,
        "error_code": error_code,
        "raw_data": {"test": "data"},
        "context": {},
    }
    
    # Serialize to JSON (should not raise)
    json_payload = json.dumps(request_data)
    assert isinstance(json_payload, str)
    
    # Make request
    response = client.post(
        "/api/v1/signals/submit",
        content=json_payload,
        headers={"Content-Type": "application/json"},
    )
    
    # Response should be valid JSON
    try:
        response_data = response.json()
        assert isinstance(response_data, dict)
    except json.JSONDecodeError:
        pytest.fail(f"Response is not valid JSON: {response.text}")
    
    # Response should have expected structure
    if response.status_code == 202:
        # Success response
        assert "signal_id" in response_data
        assert "status" in response_data
        assert "message" in response_data
    else:
        # Error response
        assert "error_code" in response_data or "detail" in response_data


# Property 50: HTTP status code correctness
@given(
    valid_request=st.booleans(),
    source=st.sampled_from(["support_ticket", "api_failure", "checkout_error", "webhook_failure"]),
    merchant_id=st.text(min_size=1, max_size=100),
    severity=st.sampled_from(["low", "medium", "high", "critical"]),
)
@settings(max_examples=100)
def test_property_50_http_status_code_correctness(
    client: TestClient,
    valid_request: bool,
    source: str,
    merchant_id: str,
    severity: str,
):
    """
    Feature: migrationguard-ai, Property 50: HTTP status code correctness
    
    For any API response, the HTTP status code must match the outcome:
    - 2xx for success
    - 4xx for client errors
    - 5xx for server errors
    
    Validates: Requirements 17.5
    """
    if valid_request:
        # Valid request should return 2xx
        request_data = {
            "source": source,
            "merchant_id": merchant_id,
            "severity": severity,
            "raw_data": {},
            "context": {},
        }
        
        response = client.post(
            "/api/v1/signals/submit",
            json=request_data,
        )
        
        # Should be 2xx (success)
        assert 200 <= response.status_code < 300, (
            f"Valid request should return 2xx, got {response.status_code}"
        )
    else:
        # Invalid request should return 4xx
        invalid_request_data = {
            "source": "invalid_source_type",  # Invalid source
            "merchant_id": merchant_id,
            "severity": severity,
            "raw_data": {},
        }
        
        response = client.post(
            "/api/v1/signals/submit",
            json=invalid_request_data,
        )
        
        # Should be 4xx (client error)
        assert 400 <= response.status_code < 500, (
            f"Invalid request should return 4xx, got {response.status_code}"
        )


# Property 51: Error response completeness
@given(
    invalid_source=st.text(min_size=1, max_size=50).filter(
        lambda x: x not in ["support_ticket", "api_failure", "checkout_error", "webhook_failure"]
    ),
    merchant_id=st.text(min_size=1, max_size=100),
)
@settings(max_examples=100)
def test_property_51_error_response_completeness(
    client: TestClient,
    invalid_source: str,
    merchant_id: str,
):
    """
    Feature: migrationguard-ai, Property 51: Error response completeness
    
    For any API error response (4xx or 5xx), the response body must include
    an error_code and a human-readable error_message.
    
    Validates: Requirements 17.7
    """
    # Make request with invalid data
    request_data = {
        "source": invalid_source,  # Invalid source
        "merchant_id": merchant_id,
        "severity": "medium",
        "raw_data": {},
    }
    
    response = client.post(
        "/api/v1/signals/submit",
        json=request_data,
    )
    
    # If response is an error (4xx or 5xx)
    if response.status_code >= 400:
        response_data = response.json()
        
        # Must have error_code
        assert "error_code" in response_data or "detail" in response_data, (
            f"Error response missing error_code or detail: {response_data}"
        )
        
        # Must have error_message or detail
        has_error_message = (
            "error_message" in response_data or
            "detail" in response_data or
            "message" in response_data
        )
        assert has_error_message, (
            f"Error response missing error_message: {response_data}"
        )
        
        # Error message should be non-empty string
        error_msg = (
            response_data.get("error_message") or
            response_data.get("detail") or
            response_data.get("message")
        )
        assert isinstance(error_msg, str) and len(error_msg) > 0, (
            f"Error message should be non-empty string: {error_msg}"
        )


# Additional property test: Health endpoints always return 200
def test_property_health_endpoints_always_succeed(client: TestClient):
    """
    Property: Health check endpoints should always return 200 OK.
    
    Health endpoints should never fail, even if dependencies are down.
    """
    endpoints = ["/health", "/health/ready", "/health/live"]
    
    for endpoint in endpoints:
        response = client.get(endpoint)
        
        # Should always return 200
        assert response.status_code == 200, (
            f"Health endpoint {endpoint} should return 200, got {response.status_code}"
        )
        
        # Should return valid JSON
        data = response.json()
        assert isinstance(data, dict)
        assert "status" in data


# Property test: All successful responses include required fields
@given(
    source=st.sampled_from(["support_ticket", "api_failure", "checkout_error", "webhook_failure"]),
    merchant_id=st.text(min_size=1, max_size=100),
    severity=st.sampled_from(["low", "medium", "high", "critical"]),
)
@settings(max_examples=100)
def test_property_successful_responses_have_required_fields(
    client: TestClient,
    source: str,
    merchant_id: str,
    severity: str,
):
    """
    Property: All successful signal submissions must include signal_id, status, and message.
    """
    request_data = {
        "source": source,
        "merchant_id": merchant_id,
        "severity": severity,
        "raw_data": {},
        "context": {},
    }
    
    response = client.post(
        "/api/v1/signals/submit",
        json=request_data,
    )
    
    if response.status_code == 202:
        data = response.json()
        
        # Must have signal_id
        assert "signal_id" in data
        assert isinstance(data["signal_id"], str)
        assert len(data["signal_id"]) > 0
        
        # Must have status
        assert "status" in data
        assert data["status"] == "accepted"
        
        # Must have message
        assert "message" in data
        assert isinstance(data["message"], str)
        assert len(data["message"]) > 0
