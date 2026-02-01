"""
Elasticsearch client wrapper for pattern and signal indexing.

This module provides a wrapper around the Elasticsearch client with:
- Index creation and management
- Document indexing and search
- Custom analyzers for text search
- Error handling and retry logic
"""

from typing import Any, Optional
from datetime import datetime

from elasticsearch import AsyncElasticsearch
from elasticsearch.exceptions import NotFoundError, ConnectionError as ESConnectionError

from migrationguard_ai.core.config import get_settings
from migrationguard_ai.core.logging import get_logger
from migrationguard_ai.core.circuit_breaker import elasticsearch_circuit_breaker

logger = get_logger(__name__)


class ElasticsearchClient:
    """Async Elasticsearch client with index management and search capabilities."""

    def __init__(self) -> None:
        """Initialize Elasticsearch client wrapper."""
        self.settings = get_settings()
        self.client: Optional[AsyncElasticsearch] = None
        self._started = False

    async def start(self) -> None:
        """Start the Elasticsearch client."""
        if self._started:
            logger.warning("Elasticsearch client already started")
            return

        try:
            self.client = AsyncElasticsearch(
                hosts=[self.settings.elasticsearch_url],
                verify_certs=False,  # For development; enable in production
                request_timeout=30,
            )
            
            # Test connection
            await self.client.info()
            
            self._started = True
            logger.info(
                "Elasticsearch client started",
                url=self.settings.elasticsearch_url,
            )
        except Exception as e:
            logger.error("Failed to start Elasticsearch client", error=str(e))
            raise

    async def stop(self) -> None:
        """Stop the Elasticsearch client."""
        if not self._started or self.client is None:
            logger.warning("Elasticsearch client not started")
            return

        try:
            await self.client.close()
            self._started = False
            logger.info("Elasticsearch client stopped")
        except Exception as e:
            logger.error("Error stopping Elasticsearch client", error=str(e))
            raise

    @elasticsearch_circuit_breaker
    async def create_index(
        self,
        index_name: str,
        mappings: dict[str, Any],
        settings: Optional[dict[str, Any]] = None,
    ) -> bool:
        """
        Create an index with specified mappings and settings.

        Args:
            index_name: Name of the index to create
            mappings: Field mappings for the index
            settings: Optional index settings (analyzers, shards, etc.)

        Returns:
            bool: True if index was created, False if it already exists

        Raises:
            RuntimeError: If client is not started
            Exception: If index creation fails
        """
        if not self._started or self.client is None:
            raise RuntimeError("Elasticsearch client not started. Call start() first.")

        try:
            # Check if index already exists
            exists = await self.client.indices.exists(index=index_name)
            if exists:
                logger.info("Index already exists", index=index_name)
                return False

            # Create index with mappings and settings
            body = {"mappings": mappings}
            if settings:
                body["settings"] = settings

            await self.client.indices.create(index=index_name, body=body)
            
            logger.info("Index created", index=index_name)
            return True

        except Exception as e:
            logger.error(
                "Failed to create index",
                index=index_name,
                error=str(e),
                exc_info=True,
            )
            raise

    @elasticsearch_circuit_breaker
    async def index_document(
        self,
        index_name: str,
        document: dict[str, Any],
        doc_id: Optional[str] = None,
    ) -> str:
        """
        Index a document.

        Args:
            index_name: Name of the index
            document: Document data to index
            doc_id: Optional document ID (auto-generated if not provided)

        Returns:
            str: Document ID

        Raises:
            RuntimeError: If client is not started
            Exception: If indexing fails
        """
        if not self._started or self.client is None:
            raise RuntimeError("Elasticsearch client not started. Call start() first.")

        try:
            response = await self.client.index(
                index=index_name,
                id=doc_id,
                document=document,
            )

            logger.debug(
                "Document indexed",
                index=index_name,
                doc_id=response["_id"],
            )

            return response["_id"]

        except Exception as e:
            logger.error(
                "Failed to index document",
                index=index_name,
                doc_id=doc_id,
                error=str(e),
                exc_info=True,
            )
            raise

    @elasticsearch_circuit_breaker
    async def bulk_index(
        self,
        index_name: str,
        documents: list[dict[str, Any]],
    ) -> tuple[int, int]:
        """
        Bulk index multiple documents.

        Args:
            index_name: Name of the index
            documents: List of documents to index

        Returns:
            tuple[int, int]: (successful_count, failed_count)

        Raises:
            RuntimeError: If client is not started
            Exception: If bulk indexing fails
        """
        if not self._started or self.client is None:
            raise RuntimeError("Elasticsearch client not started. Call start() first.")

        try:
            from elasticsearch.helpers import async_bulk

            # Prepare bulk actions
            actions = [
                {
                    "_index": index_name,
                    "_source": doc,
                }
                for doc in documents
            ]

            success, failed = await async_bulk(
                self.client,
                actions,
                raise_on_error=False,
            )

            logger.info(
                "Bulk indexing completed",
                index=index_name,
                success=success,
                failed=len(failed) if isinstance(failed, list) else failed,
            )

            return success, len(failed) if isinstance(failed, list) else failed

        except Exception as e:
            logger.error(
                "Failed to bulk index documents",
                index=index_name,
                count=len(documents),
                error=str(e),
                exc_info=True,
            )
            raise

    @elasticsearch_circuit_breaker
    async def search(
        self,
        index_name: str,
        query: dict[str, Any],
        size: int = 10,
        from_: int = 0,
        sort: Optional[list[dict[str, Any]]] = None,
    ) -> dict[str, Any]:
        """
        Search documents in an index.

        Args:
            index_name: Name of the index to search
            query: Elasticsearch query DSL
            size: Number of results to return
            from_: Offset for pagination
            sort: Optional sort criteria

        Returns:
            dict: Search results with hits and metadata

        Raises:
            RuntimeError: If client is not started
            Exception: If search fails
        """
        if not self._started or self.client is None:
            raise RuntimeError("Elasticsearch client not started. Call start() first.")

        try:
            body = {"query": query, "size": size, "from": from_}
            if sort:
                body["sort"] = sort

            response = await self.client.search(index=index_name, body=body)

            logger.debug(
                "Search completed",
                index=index_name,
                hits=response["hits"]["total"]["value"],
            )

            return response

        except NotFoundError:
            logger.warning("Index not found", index=index_name)
            return {"hits": {"total": {"value": 0}, "hits": []}}
        except Exception as e:
            logger.error(
                "Search failed",
                index=index_name,
                error=str(e),
                exc_info=True,
            )
            raise

    async def get_document(
        self,
        index_name: str,
        doc_id: str,
    ) -> Optional[dict[str, Any]]:
        """
        Get a document by ID.

        Args:
            index_name: Name of the index
            doc_id: Document ID

        Returns:
            Optional[dict]: Document data or None if not found

        Raises:
            RuntimeError: If client is not started
        """
        if not self._started or self.client is None:
            raise RuntimeError("Elasticsearch client not started. Call start() first.")

        try:
            response = await self.client.get(index=index_name, id=doc_id)
            return response["_source"]

        except NotFoundError:
            logger.debug("Document not found", index=index_name, doc_id=doc_id)
            return None
        except Exception as e:
            logger.error(
                "Failed to get document",
                index=index_name,
                doc_id=doc_id,
                error=str(e),
                exc_info=True,
            )
            raise

    async def delete_document(
        self,
        index_name: str,
        doc_id: str,
    ) -> bool:
        """
        Delete a document by ID.

        Args:
            index_name: Name of the index
            doc_id: Document ID

        Returns:
            bool: True if deleted, False if not found

        Raises:
            RuntimeError: If client is not started
        """
        if not self._started or self.client is None:
            raise RuntimeError("Elasticsearch client not started. Call start() first.")

        try:
            await self.client.delete(index=index_name, id=doc_id)
            logger.info("Document deleted", index=index_name, doc_id=doc_id)
            return True

        except NotFoundError:
            logger.debug("Document not found for deletion", index=index_name, doc_id=doc_id)
            return False
        except Exception as e:
            logger.error(
                "Failed to delete document",
                index=index_name,
                doc_id=doc_id,
                error=str(e),
                exc_info=True,
            )
            raise

    async def update_document(
        self,
        index_name: str,
        doc_id: str,
        partial_doc: dict[str, Any],
    ) -> bool:
        """
        Update a document with partial data.

        Args:
            index_name: Name of the index
            doc_id: Document ID
            partial_doc: Partial document data to update

        Returns:
            bool: True if updated, False if not found

        Raises:
            RuntimeError: If client is not started
        """
        if not self._started or self.client is None:
            raise RuntimeError("Elasticsearch client not started. Call start() first.")

        try:
            await self.client.update(
                index=index_name,
                id=doc_id,
                body={"doc": partial_doc},
            )
            logger.info("Document updated", index=index_name, doc_id=doc_id)
            return True

        except NotFoundError:
            logger.debug("Document not found for update", index=index_name, doc_id=doc_id)
            return False
        except Exception as e:
            logger.error(
                "Failed to update document",
                index=index_name,
                doc_id=doc_id,
                error=str(e),
                exc_info=True,
            )
            raise

    async def __aenter__(self) -> "ElasticsearchClient":
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.stop()


# Singleton instance
_client_instance: Optional[ElasticsearchClient] = None


async def get_elasticsearch_client() -> ElasticsearchClient:
    """
    Get or create the Elasticsearch client singleton.

    Returns:
        ElasticsearchClient instance
    """
    global _client_instance

    if _client_instance is None:
        _client_instance = ElasticsearchClient()
        await _client_instance.start()

    return _client_instance


async def close_elasticsearch_client() -> None:
    """Close the Elasticsearch client singleton."""
    global _client_instance

    if _client_instance is not None:
        await _client_instance.stop()
        _client_instance = None
