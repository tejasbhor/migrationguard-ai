"""
Property-based tests for error response completeness.

Feature: migrationguard-ai, Property 51: Error response completeness
Validates: Requirements 17.7

For any API error response (4xx or 5xx), the response body must include
an error_code and a human-readable error_message.
"""

from typing import Any

import pytest
from hypothesis import given, settings, strategies as st
from httpx import AsyncClient

from migrationguard_ai.api.app import app


@pytest.mark.asyncio
@given(
    invalid_data=st.dictionaries(
        st.text(min_size=1, max_size=50),
        st.one_of(st.none(), st.booleans(), st.integers(), st.text()),
        max_size=5,
    ),
)
@settings(max_examples=100, deadline=None)
async def test_validation_error_response_completeness(invalid_data: dict[str, Any]):
    """
    Property 51: Error response completeness
    
    For any validation error (422), the response must include:
    - error_code field
    - error_message field (human-readable)
    
    Validates: Requirements 17.7
    """
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Submit invalid data to trigger validation error
        response = await client.post("/api/v1/signals/submit", json=invalid_data)
        
        # Only check error responses
        if response.status_code >= 400:
            response_data = response.json()
            
            # Must have error_code
            assert "error_code" in response_data, (
                f"Error response missing 'error_code' field: {response_data}"
            )
            assert isinstance(response_data["error_code"], str), (
                f"error_code must be a string, got {type(response_data['error_code'])}"
            )
            assert len(response_data["error_code"]) > 0, (
                "error_code must not be empty"
            )
            
            # Must have error_message
            assert "error_message" in response_data, (
                f"Error response missing 'error_message' field: {response_data}"
            )
            assert isinstance(response_data["error_message"], str), (
                f"error_message must be a string, got {type(response_data['error_message'])}"
            )
            assert len(response_data["error_message"]) > 0, (
                "error_message must not be empty"
            )


@pytest.mark.asyncio
@settings(max_examples=50, deadline=None)
async def test_not_found_error_response_completeness():
    """
    Property 51: Error response completeness
    
    For 404 errors, the response must include error_code and error_message.
    
    Validates: Requirements 17.7
    """
    async with AsyncClient(app=app, base_url="http://test") as client:
        nonexistent_paths = [
            "/api/v1/nonexistent",
            "/api/v1/signals/invalid/path",
            "/api/v1/webhooks/unknown",
        ]
        
        for path in nonexistent_paths:
            response = await client.get(path)
            
            if response.status_code == 404:
                response_data = response.json()
                
                # Must have error_code
                assert "error_code" in response_data, (
                    f"404 response missing 'error_code' field for {path}"
                )
                assert isinstance(response_data["error_code"], str)
                assert len(response_data["error_code"]) > 0
                
                # Must have error_message
                assert "error_message" in response_data, (
                    f"404 response missing 'error_message' field for {path}"
                )
                assert isinstance(response_data["error_message"], str)
                assert len(response_data["error_message"]) > 0


@pytest.mark.asyncio
@settings(max_examples=50, deadline=None)
async def test_method_not_allowed_error_response_completeness():
    """
    Property 51: Error response completeness
    
    For 405 errors, the response must include error_code and error_message.
    
    Validates: Requirements 17.7
    """
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Try wrong HTTP method
        response = await client.get("/api/v1/signals/submit")
        
        if response.status_code == 405:
            response_data = response.json()
            
            # Must have error_code
            assert "error_code" in response_data, (
                "405 response missing 'error_code' field"
            )
            assert isinstance(response_data["error_code"], str)
            assert len(response_data["error_code"]) > 0
            
            # Must have error_message
            assert "error_message" in response_data, (
                "405 response missing 'error_message' field"
            )
            assert isinstance(response_data["error_message"], str)
            assert len(response_data["error_message"]) > 0


@pytest.mark.asyncio
@settings(max_examples=50, deadline=None)
async def test_malformed_json_error_response_completeness():
    """
    Property 51: Error response completeness
    
    For malformed JSON errors, the response must include error_code and error_message.
    
    Validates: Requirements 17.7
    """
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Send malformed JSON
        response = await client.post(
            "/api/v1/signals/submit",
            content=b"{invalid json}",
            headers={"Content-Type": "application/json"},
        )
        
        if response.status_code >= 400:
            response_data = response.json()
            
            # Must have error_code
            assert "error_code" in response_data, (
                "Malformed JSON error response missing 'error_code' field"
            )
            assert isinstance(response_data["error_code"], str)
            assert len(response_data["error_code"]) > 0
            
            # Must have error_message
            assert "error_message" in response_data, (
                "Malformed JSON error response missing 'error_message' field"
            )
            assert isinstance(response_data["error_message"], str)
            assert len(response_data["error_message"]) > 0


@pytest.mark.asyncio
@given(
    page=st.integers(max_value=0),  # Invalid page number
)
@settings(max_examples=50, deadline=None)
async def test_invalid_query_params_error_response_completeness(page: int):
    """
    Property 51: Error response completeness
    
    For invalid query parameter errors, the response must include
    error_code and error_message.
    
    Validates: Requirements 17.7
    """
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/signals/search",
            params={"page": page},
        )
        
        if response.status_code >= 400:
            response_data = response.json()
            
            # Must have error_code
            assert "error_code" in response_data, (
                "Invalid query params error response missing 'error_code' field"
            )
            assert isinstance(response_data["error_code"], str)
            assert len(response_data["error_code"]) > 0
            
            # Must have error_message
            assert "error_message" in response_data, (
                "Invalid query params error response missing 'error_message' field"
            )
            assert isinstance(response_data["error_message"], str)
            assert len(response_data["error_message"]) > 0


@pytest.mark.asyncio
@given(
    source=st.text(min_size=1, max_size=100).filter(
        lambda x: x not in ["support_ticket", "api_failure", "checkout_error", "webhook_failure"]
    ),
)
@settings(max_examples=100, deadline=None)
async def test_invalid_enum_value_error_response_completeness(source: str):
    """
    Property 51: Error response completeness
    
    For invalid enum value errors, the response must include
    error_code and error_message.
    
    Validates: Requirements 17.7
    """
    async with AsyncClient(app=app, base_url="http://test") as client:
        request_data = {
            "source": source,  # Invalid source value
            "merchant_id": "test_merchant",
            "severity": "high",
            "raw_data": {},
            "context": {},
        }
        
        response = await client.post("/api/v1/signals/submit", json=request_data)
        
        if response.status_code >= 400:
            response_data = response.json()
            
            # Must have error_code
            assert "error_code" in response_data, (
                "Invalid enum error response missing 'error_code' field"
            )
            assert isinstance(response_data["error_code"], str)
            assert len(response_data["error_code"]) > 0
            
            # Must have error_message
            assert "error_message" in response_data, (
                "Invalid enum error response missing 'error_message' field"
            )
            assert isinstance(response_data["error_message"], str)
            assert len(response_data["error_message"]) > 0


@pytest.mark.asyncio
@settings(max_examples=50, deadline=None)
async def test_error_response_message_is_human_readable():
    """
    Property 51: Error response completeness
    
    Error messages should be human-readable (not just stack traces or codes).
    
    Validates: Requirements 17.7
    """
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Trigger validation error
        response = await client.post(
            "/api/v1/signals/submit",
            json={"invalid": "data"},
        )
        
        if response.status_code >= 400:
            response_data = response.json()
            error_message = response_data.get("error_message", "")
            
            # Message should be human-readable
            # Check that it's not just a code or stack trace
            assert len(error_message) > 10, (
                "Error message too short to be human-readable"
            )
            
            # Should contain some common words
            assert any(word in error_message.lower() for word in [
                "error", "invalid", "failed", "missing", "required", "validation"
            ]), (
                f"Error message doesn't appear to be human-readable: {error_message}"
            )


@pytest.mark.asyncio
@given(
    webhook_data=st.dictionaries(
        st.text(min_size=1, max_size=50),
        st.one_of(st.none(), st.booleans(), st.integers()),
        max_size=5,
    ),
)
@settings(max_examples=100, deadline=None)
async def test_webhook_error_response_completeness(webhook_data: dict[str, Any]):
    """
    Property 51: Error response completeness
    
    Webhook endpoint errors must include error_code and error_message.
    
    Validates: Requirements 17.7
    """
    async with AsyncClient(app=app, base_url="http://test") as client:
        webhook_endpoints = [
            "/api/v1/webhooks/zendesk",
            "/api/v1/webhooks/intercom",
            "/api/v1/webhooks/freshdesk",
        ]
        
        for endpoint in webhook_endpoints:
            response = await client.post(endpoint, json=webhook_data)
            
            if response.status_code >= 400:
                response_data = response.json()
                
                # Must have error_code
                assert "error_code" in response_data, (
                    f"Webhook error response missing 'error_code' field for {endpoint}"
                )
                assert isinstance(response_data["error_code"], str)
                assert len(response_data["error_code"]) > 0
                
                # Must have error_message
                assert "error_message" in response_data, (
                    f"Webhook error response missing 'error_message' field for {endpoint}"
                )
                assert isinstance(response_data["error_message"], str)
                assert len(response_data["error_message"]) > 0
