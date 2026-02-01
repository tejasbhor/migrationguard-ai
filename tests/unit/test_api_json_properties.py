"""
Property-based tests for API JSON format.

Feature: migrationguard-ai, Property 48: JSON request/response format
Validates: Requirements 17.2

For any API endpoint, requests and responses must be valid JSON
(parseable without errors).
"""

import json
from typing import Any

import pytest
from hypothesis import given, settings, strategies as st
from httpx import AsyncClient

from migrationguard_ai.api.app import app


# Strategy for generating valid JSON-serializable data
json_value = st.recursive(
    st.none() | st.booleans() | st.floats(allow_nan=False, allow_infinity=False) | st.text(),
    lambda children: st.lists(children, max_size=5) | st.dictionaries(st.text(), children, max_size=5),
    max_leaves=10,
)


@pytest.mark.asyncio
@given(
    source=st.sampled_from(["support_ticket", "api_failure", "checkout_error", "webhook_failure"]),
    merchant_id=st.text(min_size=1, max_size=100),
    severity=st.sampled_from(["low", "medium", "high", "critical"]),
    error_message=st.one_of(st.none(), st.text(max_size=500)),
    raw_data=st.dictionaries(st.text(min_size=1, max_size=50), json_value, max_size=10),
)
@settings(max_examples=100, deadline=None)
async def test_signal_submit_json_format(
    source: str,
    merchant_id: str,
    severity: str,
    error_message: str | None,
    raw_data: dict[str, Any],
):
    """
    Property 48: JSON request/response format
    
    For any valid signal submission request, the API should:
    1. Accept valid JSON request body
    2. Return valid JSON response body
    3. Response should be parseable without errors
    
    Validates: Requirements 17.2
    """
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Construct request payload
        request_data = {
            "source": source,
            "merchant_id": merchant_id,
            "severity": severity,
            "error_message": error_message,
            "raw_data": raw_data,
            "context": {},
        }
        
        # Verify request is valid JSON
        request_json = json.dumps(request_data)
        assert isinstance(request_json, str)
        
        # Make request
        response = await client.post(
            "/api/v1/signals/submit",
            json=request_data,
        )
        
        # Verify response is valid JSON
        try:
            response_data = response.json()
            assert isinstance(response_data, dict)
        except json.JSONDecodeError as e:
            pytest.fail(f"Response is not valid JSON: {e}")
        
        # Verify response can be serialized back to JSON
        response_json = json.dumps(response_data)
        assert isinstance(response_json, str)


@pytest.mark.asyncio
@settings(max_examples=100, deadline=None)
async def test_health_check_json_format():
    """
    Property 48: JSON request/response format
    
    Health check endpoints should return valid JSON.
    
    Validates: Requirements 17.2
    """
    async with AsyncClient(app=app, base_url="http://test") as client:
        endpoints = ["/health", "/health/ready", "/health/live"]
        
        for endpoint in endpoints:
            response = await client.get(endpoint)
            
            # Verify response is valid JSON
            try:
                response_data = response.json()
                assert isinstance(response_data, dict)
            except json.JSONDecodeError as e:
                pytest.fail(f"Response from {endpoint} is not valid JSON: {e}")
            
            # Verify response can be serialized back to JSON
            response_json = json.dumps(response_data)
            assert isinstance(response_json, str)


@pytest.mark.asyncio
@given(
    page=st.integers(min_value=1, max_value=100),
    page_size=st.integers(min_value=1, max_value=1000),
)
@settings(max_examples=100, deadline=None)
async def test_signal_search_json_format(page: int, page_size: int):
    """
    Property 48: JSON request/response format
    
    Signal search endpoint should return valid JSON for any valid query parameters.
    
    Validates: Requirements 17.2
    """
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/signals/search",
            params={"page": page, "page_size": page_size},
        )
        
        # Verify response is valid JSON
        try:
            response_data = response.json()
            assert isinstance(response_data, dict)
        except json.JSONDecodeError as e:
            pytest.fail(f"Response is not valid JSON: {e}")
        
        # Verify response can be serialized back to JSON
        response_json = json.dumps(response_data)
        assert isinstance(response_json, str)


@pytest.mark.asyncio
@given(
    webhook_data=st.dictionaries(
        st.text(min_size=1, max_size=50),
        json_value,
        max_size=20,
    ),
)
@settings(max_examples=100, deadline=None)
async def test_webhook_endpoints_json_format(webhook_data: dict[str, Any]):
    """
    Property 48: JSON request/response format
    
    Webhook endpoints should accept and return valid JSON.
    
    Validates: Requirements 17.2
    """
    async with AsyncClient(app=app, base_url="http://test") as client:
        webhook_endpoints = [
            "/api/v1/webhooks/zendesk",
            "/api/v1/webhooks/intercom",
            "/api/v1/webhooks/freshdesk",
        ]
        
        for endpoint in webhook_endpoints:
            # Verify request is valid JSON
            request_json = json.dumps(webhook_data)
            assert isinstance(request_json, str)
            
            # Make request
            response = await client.post(endpoint, json=webhook_data)
            
            # Verify response is valid JSON
            try:
                response_data = response.json()
                assert isinstance(response_data, dict)
            except json.JSONDecodeError as e:
                pytest.fail(f"Response from {endpoint} is not valid JSON: {e}")
            
            # Verify response can be serialized back to JSON
            response_json = json.dumps(response_data)
            assert isinstance(response_json, str)


@pytest.mark.asyncio
@settings(max_examples=50, deadline=None)
async def test_error_responses_json_format():
    """
    Property 48: JSON request/response format
    
    Error responses should be valid JSON.
    
    Validates: Requirements 17.2
    """
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Test 404 error
        response = await client.get("/api/v1/nonexistent")
        try:
            response_data = response.json()
            assert isinstance(response_data, dict)
        except json.JSONDecodeError as e:
            pytest.fail(f"404 error response is not valid JSON: {e}")
        
        # Test validation error (422)
        response = await client.post(
            "/api/v1/signals/submit",
            json={"invalid": "data"},  # Missing required fields
        )
        try:
            response_data = response.json()
            assert isinstance(response_data, dict)
        except json.JSONDecodeError as e:
            pytest.fail(f"Validation error response is not valid JSON: {e}")
