"""
Property-based tests for HTTP status code correctness.

Feature: migrationguard-ai, Property 50: HTTP status code correctness
Validates: Requirements 17.5

For any API response, the HTTP status code must match the outcome:
- 2xx for success
- 4xx for client errors
- 5xx for server errors
"""

from typing import Any

import pytest
from hypothesis import given, settings, strategies as st
from httpx import AsyncClient

from migrationguard_ai.api.app import app


@pytest.mark.asyncio
@given(
    source=st.sampled_from(["support_ticket", "api_failure", "checkout_error", "webhook_failure"]),
    merchant_id=st.text(min_size=1, max_size=100),
    severity=st.sampled_from(["low", "medium", "high", "critical"]),
)
@settings(max_examples=100, deadline=None)
async def test_successful_signal_submission_returns_2xx(
    source: str,
    merchant_id: str,
    severity: str,
):
    """
    Property 50: HTTP status code correctness
    
    For any valid signal submission, the API should return 2xx status code.
    Specifically, it should return 202 Accepted for async processing.
    
    Validates: Requirements 17.5
    """
    async with AsyncClient(app=app, base_url="http://test") as client:
        request_data = {
            "source": source,
            "merchant_id": merchant_id,
            "severity": severity,
            "raw_data": {},
            "context": {},
        }
        
        response = await client.post("/api/v1/signals/submit", json=request_data)
        
        # Successful submission should return 2xx
        assert 200 <= response.status_code < 300, (
            f"Expected 2xx status code for successful submission, got {response.status_code}"
        )
        
        # Specifically, async processing should return 202 Accepted
        assert response.status_code == 202, (
            f"Expected 202 Accepted for async processing, got {response.status_code}"
        )


@pytest.mark.asyncio
@settings(max_examples=100, deadline=None)
async def test_health_endpoints_return_2xx():
    """
    Property 50: HTTP status code correctness
    
    Health check endpoints should return 2xx when healthy.
    
    Validates: Requirements 17.5
    """
    async with AsyncClient(app=app, base_url="http://test") as client:
        endpoints = ["/health", "/health/ready", "/health/live"]
        
        for endpoint in endpoints:
            response = await client.get(endpoint)
            
            # Health checks should return 2xx when healthy
            assert 200 <= response.status_code < 300, (
                f"Expected 2xx status code for {endpoint}, got {response.status_code}"
            )


@pytest.mark.asyncio
@given(
    invalid_data=st.dictionaries(
        st.text(min_size=1, max_size=50),
        st.one_of(st.none(), st.booleans(), st.integers(), st.text()),
        max_size=5,
    ),
)
@settings(max_examples=100, deadline=None)
async def test_invalid_signal_submission_returns_4xx(invalid_data: dict[str, Any]):
    """
    Property 50: HTTP status code correctness
    
    For any invalid signal submission (missing required fields),
    the API should return 4xx status code.
    
    Validates: Requirements 17.5
    """
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Submit data that's missing required fields
        response = await client.post("/api/v1/signals/submit", json=invalid_data)
        
        # Invalid request should return 4xx (client error)
        assert 400 <= response.status_code < 500, (
            f"Expected 4xx status code for invalid request, got {response.status_code}"
        )


@pytest.mark.asyncio
@settings(max_examples=50, deadline=None)
async def test_nonexistent_endpoint_returns_404():
    """
    Property 50: HTTP status code correctness
    
    Requests to non-existent endpoints should return 404.
    
    Validates: Requirements 17.5
    """
    async with AsyncClient(app=app, base_url="http://test") as client:
        nonexistent_paths = [
            "/api/v1/nonexistent",
            "/api/v1/signals/invalid/path",
            "/api/v1/webhooks/unknown",
        ]
        
        for path in nonexistent_paths:
            response = await client.get(path)
            
            # Non-existent endpoints should return 404
            assert response.status_code == 404, (
                f"Expected 404 for {path}, got {response.status_code}"
            )


@pytest.mark.asyncio
@given(
    page=st.integers(min_value=1, max_value=100),
    page_size=st.integers(min_value=1, max_value=1000),
)
@settings(max_examples=100, deadline=None)
async def test_valid_search_returns_2xx(page: int, page_size: int):
    """
    Property 50: HTTP status code correctness
    
    Valid search requests should return 2xx status code.
    
    Validates: Requirements 17.5
    """
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/signals/search",
            params={"page": page, "page_size": page_size},
        )
        
        # Valid search should return 2xx
        assert 200 <= response.status_code < 300, (
            f"Expected 2xx status code for valid search, got {response.status_code}"
        )


@pytest.mark.asyncio
@given(
    page=st.integers(max_value=0),  # Invalid page number
)
@settings(max_examples=50, deadline=None)
async def test_invalid_search_params_return_4xx(page: int):
    """
    Property 50: HTTP status code correctness
    
    Invalid search parameters should return 4xx status code.
    
    Validates: Requirements 17.5
    """
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/signals/search",
            params={"page": page},
        )
        
        # Invalid parameters should return 4xx
        assert 400 <= response.status_code < 500, (
            f"Expected 4xx status code for invalid parameters, got {response.status_code}"
        )


@pytest.mark.asyncio
@given(
    webhook_data=st.dictionaries(
        st.text(min_size=1, max_size=50),
        st.one_of(st.none(), st.booleans(), st.integers(), st.text()),
        max_size=10,
    ),
)
@settings(max_examples=100, deadline=None)
async def test_webhook_endpoints_return_2xx_or_4xx(webhook_data: dict[str, Any]):
    """
    Property 50: HTTP status code correctness
    
    Webhook endpoints should return:
    - 2xx for successful processing
    - 4xx for invalid data or authentication failures
    
    Validates: Requirements 17.5
    """
    async with AsyncClient(app=app, base_url="http://test") as client:
        webhook_endpoints = [
            "/api/v1/webhooks/zendesk",
            "/api/v1/webhooks/intercom",
            "/api/v1/webhooks/freshdesk",
        ]
        
        for endpoint in webhook_endpoints:
            response = await client.post(endpoint, json=webhook_data)
            
            # Webhooks should return 2xx (success) or 4xx (client error)
            # Never 5xx unless there's an actual server error
            assert (200 <= response.status_code < 300) or (400 <= response.status_code < 500), (
                f"Expected 2xx or 4xx status code for {endpoint}, got {response.status_code}"
            )


@pytest.mark.asyncio
@settings(max_examples=50, deadline=None)
async def test_method_not_allowed_returns_405():
    """
    Property 50: HTTP status code correctness
    
    Using wrong HTTP method should return 405 Method Not Allowed.
    
    Validates: Requirements 17.5
    """
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Try GET on POST-only endpoint
        response = await client.get("/api/v1/signals/submit")
        
        # Wrong method should return 405
        assert response.status_code == 405, (
            f"Expected 405 for wrong HTTP method, got {response.status_code}"
        )


@pytest.mark.asyncio
@settings(max_examples=50, deadline=None)
async def test_malformed_json_returns_4xx():
    """
    Property 50: HTTP status code correctness
    
    Malformed JSON should return 4xx status code.
    
    Validates: Requirements 17.5
    """
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Send malformed JSON
        response = await client.post(
            "/api/v1/signals/submit",
            content=b"{invalid json}",
            headers={"Content-Type": "application/json"},
        )
        
        # Malformed JSON should return 4xx
        assert 400 <= response.status_code < 500, (
            f"Expected 4xx status code for malformed JSON, got {response.status_code}"
        )
