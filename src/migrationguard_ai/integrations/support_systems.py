"""
Support System Integrations for MigrationGuard AI.

This module provides clients for integrating with external support systems:
- Zendesk (OAuth)
- Intercom (OAuth)
- Freshdesk (API Key)
"""

import logging
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod
from datetime import datetime
import httpx

from migrationguard_ai.core.config import get_settings
from migrationguard_ai.core.circuit_breaker import support_system_circuit_breaker


logger = logging.getLogger(__name__)


class SupportSystemClient(ABC):
    """Abstract base class for support system clients."""
    
    @abstractmethod
    async def create_ticket(
        self,
        subject: str,
        description: str,
        merchant_id: str,
        priority: str = "normal",
        tags: Optional[list[str]] = None
    ) -> Dict[str, Any]:
        """Create a new support ticket."""
        pass
    
    @abstractmethod
    async def update_ticket(
        self,
        ticket_id: str,
        comment: Optional[str] = None,
        status: Optional[str] = None,
        tags: Optional[list[str]] = None
    ) -> Dict[str, Any]:
        """Update an existing ticket."""
        pass
    
    @abstractmethod
    async def resolve_ticket(
        self,
        ticket_id: str,
        resolution_comment: str
    ) -> Dict[str, Any]:
        """Resolve a ticket."""
        pass
    
    @abstractmethod
    async def get_ticket(self, ticket_id: str) -> Dict[str, Any]:
        """Get ticket details."""
        pass


class ZendeskClient(SupportSystemClient):
    """
    Zendesk API client with OAuth authentication.
    
    Docs: https://developer.zendesk.com/api-reference/
    """
    
    def __init__(
        self,
        subdomain: str,
        oauth_token: str,
        timeout: int = 30
    ):
        """
        Initialize Zendesk client.
        
        Args:
            subdomain: Zendesk subdomain (e.g., 'mycompany')
            oauth_token: OAuth access token
            timeout: Request timeout in seconds
        """
        self.base_url = f"https://{subdomain}.zendesk.com/api/v2"
        self.oauth_token = oauth_token
        self.timeout = timeout
        self.client = httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {oauth_token}",
                "Content-Type": "application/json"
            },
            timeout=timeout
        )
    
    @support_system_circuit_breaker
    async def create_ticket(
        self,
        subject: str,
        description: str,
        merchant_id: str,
        priority: str = "normal",
        tags: Optional[list[str]] = None
    ) -> Dict[str, Any]:
        """Create a new Zendesk ticket."""
        try:
            payload = {
                "ticket": {
                    "subject": subject,
                    "comment": {"body": description},
                    "priority": priority,
                    "tags": tags or [],
                    "custom_fields": [
                        {"id": "merchant_id", "value": merchant_id}
                    ]
                }
            }
            
            response = await self.client.post(
                f"{self.base_url}/tickets.json",
                json=payload
            )
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"Created Zendesk ticket: {result['ticket']['id']}")
            return result["ticket"]
            
        except httpx.HTTPError as e:
            logger.error(f"Zendesk API error: {e}")
            raise
    
    @support_system_circuit_breaker
    async def update_ticket(
        self,
        ticket_id: str,
        comment: Optional[str] = None,
        status: Optional[str] = None,
        tags: Optional[list[str]] = None
    ) -> Dict[str, Any]:
        """Update a Zendesk ticket."""
        try:
            payload = {"ticket": {}}
            
            if comment:
                payload["ticket"]["comment"] = {"body": comment}
            if status:
                payload["ticket"]["status"] = status
            if tags:
                payload["ticket"]["tags"] = tags
            
            response = await self.client.put(
                f"{self.base_url}/tickets/{ticket_id}.json",
                json=payload
            )
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"Updated Zendesk ticket: {ticket_id}")
            return result["ticket"]
            
        except httpx.HTTPError as e:
            logger.error(f"Zendesk API error: {e}")
            raise
    
    async def resolve_ticket(
        self,
        ticket_id: str,
        resolution_comment: str
    ) -> Dict[str, Any]:
        """Resolve a Zendesk ticket."""
        return await self.update_ticket(
            ticket_id=ticket_id,
            comment=resolution_comment,
            status="solved"
        )
    
    @support_system_circuit_breaker
    async def get_ticket(self, ticket_id: str) -> Dict[str, Any]:
        """Get Zendesk ticket details."""
        try:
            response = await self.client.get(
                f"{self.base_url}/tickets/{ticket_id}.json"
            )
            response.raise_for_status()
            
            result = response.json()
            return result["ticket"]
            
        except httpx.HTTPError as e:
            logger.error(f"Zendesk API error: {e}")
            raise
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


class IntercomClient(SupportSystemClient):
    """
    Intercom API client with OAuth authentication.
    
    Docs: https://developers.intercom.com/docs/references/rest-api/
    """
    
    def __init__(
        self,
        access_token: str,
        timeout: int = 30
    ):
        """
        Initialize Intercom client.
        
        Args:
            access_token: OAuth access token
            timeout: Request timeout in seconds
        """
        self.base_url = "https://api.intercom.io"
        self.access_token = access_token
        self.timeout = timeout
        self.client = httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            timeout=timeout
        )
    
    @support_system_circuit_breaker
    async def create_ticket(
        self,
        subject: str,
        description: str,
        merchant_id: str,
        priority: str = "normal",
        tags: Optional[list[str]] = None
    ) -> Dict[str, Any]:
        """Create a new Intercom conversation (ticket)."""
        try:
            # Map priority to Intercom priority
            priority_map = {
                "low": "low",
                "normal": "medium",
                "high": "high",
                "urgent": "urgent"
            }
            
            payload = {
                "from": {
                    "type": "user",
                    "id": merchant_id
                },
                "body": f"{subject}\n\n{description}",
                "priority": priority_map.get(priority, "medium")
            }
            
            response = await self.client.post(
                f"{self.base_url}/conversations",
                json=payload
            )
            response.raise_for_status()
            
            result = response.json()
            
            # Add tags if provided
            if tags:
                await self._add_tags(result["id"], tags)
            
            logger.info(f"Created Intercom conversation: {result['id']}")
            return result
            
        except httpx.HTTPError as e:
            logger.error(f"Intercom API error: {e}")
            raise
    
    @support_system_circuit_breaker
    async def update_ticket(
        self,
        ticket_id: str,
        comment: Optional[str] = None,
        status: Optional[str] = None,
        tags: Optional[list[str]] = None
    ) -> Dict[str, Any]:
        """Update an Intercom conversation."""
        try:
            result = {}
            
            # Add comment (reply)
            if comment:
                payload = {
                    "message_type": "comment",
                    "type": "admin",
                    "body": comment
                }
                
                response = await self.client.post(
                    f"{self.base_url}/conversations/{ticket_id}/reply",
                    json=payload
                )
                response.raise_for_status()
                result = response.json()
            
            # Update status
            if status:
                status_map = {
                    "open": "open",
                    "closed": "closed",
                    "solved": "closed"
                }
                
                payload = {
                    "state": status_map.get(status, "open")
                }
                
                response = await self.client.put(
                    f"{self.base_url}/conversations/{ticket_id}",
                    json=payload
                )
                response.raise_for_status()
                result = response.json()
            
            # Add tags
            if tags:
                await self._add_tags(ticket_id, tags)
            
            logger.info(f"Updated Intercom conversation: {ticket_id}")
            return result
            
        except httpx.HTTPError as e:
            logger.error(f"Intercom API error: {e}")
            raise
    
    async def resolve_ticket(
        self,
        ticket_id: str,
        resolution_comment: str
    ) -> Dict[str, Any]:
        """Resolve an Intercom conversation."""
        return await self.update_ticket(
            ticket_id=ticket_id,
            comment=resolution_comment,
            status="closed"
        )
    
    @support_system_circuit_breaker
    async def get_ticket(self, ticket_id: str) -> Dict[str, Any]:
        """Get Intercom conversation details."""
        try:
            response = await self.client.get(
                f"{self.base_url}/conversations/{ticket_id}"
            )
            response.raise_for_status()
            
            return response.json()
            
        except httpx.HTTPError as e:
            logger.error(f"Intercom API error: {e}")
            raise
    
    async def _add_tags(self, conversation_id: str, tags: list[str]):
        """Add tags to a conversation."""
        try:
            payload = {
                "id": conversation_id,
                "admin_id": "system",
                "tags": [{"name": tag} for tag in tags]
            }
            
            await self.client.post(
                f"{self.base_url}/conversations/{conversation_id}/tags",
                json=payload
            )
            
        except httpx.HTTPError as e:
            logger.warning(f"Failed to add tags: {e}")
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


class FreshdeskClient(SupportSystemClient):
    """
    Freshdesk API client with API key authentication.
    
    Docs: https://developers.freshdesk.com/api/
    """
    
    def __init__(
        self,
        domain: str,
        api_key: str,
        timeout: int = 30
    ):
        """
        Initialize Freshdesk client.
        
        Args:
            domain: Freshdesk domain (e.g., 'mycompany.freshdesk.com')
            api_key: API key
            timeout: Request timeout in seconds
        """
        self.base_url = f"https://{domain}/api/v2"
        self.api_key = api_key
        self.timeout = timeout
        self.client = httpx.AsyncClient(
            auth=(api_key, "X"),  # Freshdesk uses API key as username
            headers={"Content-Type": "application/json"},
            timeout=timeout
        )
    
    @support_system_circuit_breaker
    async def create_ticket(
        self,
        subject: str,
        description: str,
        merchant_id: str,
        priority: str = "normal",
        tags: Optional[list[str]] = None
    ) -> Dict[str, Any]:
        """Create a new Freshdesk ticket."""
        try:
            # Map priority to Freshdesk priority (1-4)
            priority_map = {
                "low": 1,
                "normal": 2,
                "high": 3,
                "urgent": 4
            }
            
            payload = {
                "subject": subject,
                "description": description,
                "priority": priority_map.get(priority, 2),
                "status": 2,  # Open
                "tags": tags or [],
                "custom_fields": {
                    "merchant_id": merchant_id
                }
            }
            
            response = await self.client.post(
                f"{self.base_url}/tickets",
                json=payload
            )
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"Created Freshdesk ticket: {result['id']}")
            return result
            
        except httpx.HTTPError as e:
            logger.error(f"Freshdesk API error: {e}")
            raise
    
    @support_system_circuit_breaker
    async def update_ticket(
        self,
        ticket_id: str,
        comment: Optional[str] = None,
        status: Optional[str] = None,
        tags: Optional[list[str]] = None
    ) -> Dict[str, Any]:
        """Update a Freshdesk ticket."""
        try:
            payload = {}
            
            # Update status
            if status:
                status_map = {
                    "open": 2,
                    "pending": 3,
                    "resolved": 4,
                    "closed": 5
                }
                payload["status"] = status_map.get(status, 2)
            
            # Add tags
            if tags:
                payload["tags"] = tags
            
            # Update ticket
            if payload:
                response = await self.client.put(
                    f"{self.base_url}/tickets/{ticket_id}",
                    json=payload
                )
                response.raise_for_status()
                result = response.json()
            else:
                result = await self.get_ticket(ticket_id)
            
            # Add comment as note
            if comment:
                note_payload = {
                    "body": comment,
                    "private": False
                }
                
                await self.client.post(
                    f"{self.base_url}/tickets/{ticket_id}/notes",
                    json=note_payload
                )
            
            logger.info(f"Updated Freshdesk ticket: {ticket_id}")
            return result
            
        except httpx.HTTPError as e:
            logger.error(f"Freshdesk API error: {e}")
            raise
    
    async def resolve_ticket(
        self,
        ticket_id: str,
        resolution_comment: str
    ) -> Dict[str, Any]:
        """Resolve a Freshdesk ticket."""
        return await self.update_ticket(
            ticket_id=ticket_id,
            comment=resolution_comment,
            status="resolved"
        )
    
    @support_system_circuit_breaker
    async def get_ticket(self, ticket_id: str) -> Dict[str, Any]:
        """Get Freshdesk ticket details."""
        try:
            response = await self.client.get(
                f"{self.base_url}/tickets/{ticket_id}"
            )
            response.raise_for_status()
            
            return response.json()
            
        except httpx.HTTPError as e:
            logger.error(f"Freshdesk API error: {e}")
            raise
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


class SupportSystemIntegrations:
    """
    Unified interface for all support system integrations.
    
    Provides a single entry point for interacting with multiple support systems.
    """
    
    def __init__(self):
        """Initialize support system clients from configuration."""
        settings = get_settings()
        
        self.zendesk = None
        self.intercom = None
        self.freshdesk = None
        
        # Initialize Zendesk if configured
        if hasattr(settings, 'ZENDESK_SUBDOMAIN') and hasattr(settings, 'ZENDESK_OAUTH_TOKEN'):
            self.zendesk = ZendeskClient(
                subdomain=settings.ZENDESK_SUBDOMAIN,
                oauth_token=settings.ZENDESK_OAUTH_TOKEN
            )
        
        # Initialize Intercom if configured
        if hasattr(settings, 'INTERCOM_ACCESS_TOKEN'):
            self.intercom = IntercomClient(
                access_token=settings.INTERCOM_ACCESS_TOKEN
            )
        
        # Initialize Freshdesk if configured
        if hasattr(settings, 'FRESHDESK_DOMAIN') and hasattr(settings, 'FRESHDESK_API_KEY'):
            self.freshdesk = FreshdeskClient(
                domain=settings.FRESHDESK_DOMAIN,
                api_key=settings.FRESHDESK_API_KEY
            )
    
    def get_client(self, system: str) -> Optional[SupportSystemClient]:
        """
        Get client for specified support system.
        
        Args:
            system: Support system name ('zendesk', 'intercom', 'freshdesk')
            
        Returns:
            Support system client or None if not configured
        """
        clients = {
            "zendesk": self.zendesk,
            "intercom": self.intercom,
            "freshdesk": self.freshdesk
        }
        return clients.get(system.lower())
    
    async def close_all(self):
        """Close all HTTP clients."""
        if self.zendesk:
            await self.zendesk.close()
        if self.intercom:
            await self.intercom.close()
        if self.freshdesk:
            await self.freshdesk.close()
