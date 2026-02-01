"""
Elasticsearch index definitions for patterns and signals.

This module defines the mappings and settings for Elasticsearch indices
used by the pattern detection system.
"""

from typing import Any

# Patterns index mapping
PATTERNS_INDEX_MAPPING: dict[str, Any] = {
    "properties": {
        "pattern_id": {"type": "keyword"},
        "pattern_type": {
            "type": "keyword",
            # api_failure, checkout_issue, webhook_problem, config_error, migration_stage_issue
        },
        "confidence": {"type": "float"},
        "signal_ids": {"type": "keyword"},
        "merchant_ids": {"type": "keyword"},
        "first_seen": {"type": "date"},
        "last_seen": {"type": "date"},
        "frequency": {"type": "integer"},
        "characteristics": {
            "type": "object",
            "enabled": True,
        },
        # Searchable text fields
        "error_message": {
            "type": "text",
            "analyzer": "standard",
            "fields": {
                "keyword": {"type": "keyword", "ignore_above": 256}
            },
        },
        "error_code": {"type": "keyword"},
        "affected_resources": {"type": "keyword"},
        "migration_stages": {"type": "keyword"},
        # Metadata
        "created_at": {"type": "date"},
        "updated_at": {"type": "date"},
    }
}

# Patterns index settings
PATTERNS_INDEX_SETTINGS: dict[str, Any] = {
    "number_of_shards": 2,
    "number_of_replicas": 1,
    "analysis": {
        "analyzer": {
            "error_analyzer": {
                "type": "custom",
                "tokenizer": "standard",
                "filter": ["lowercase", "stop", "snowball"],
            }
        }
    },
}

# Signals index mapping (for search and pattern matching)
SIGNALS_INDEX_MAPPING: dict[str, Any] = {
    "properties": {
        "signal_id": {"type": "keyword"},
        "timestamp": {"type": "date"},
        "source": {
            "type": "keyword",
            # support_ticket, api_failure, checkout_error, webhook_failure
        },
        "merchant_id": {"type": "keyword"},
        "migration_stage": {"type": "keyword"},
        "severity": {
            "type": "keyword",
            # low, medium, high, critical
        },
        # Searchable fields
        "error_message": {
            "type": "text",
            "analyzer": "error_analyzer",
            "fields": {
                "keyword": {"type": "keyword", "ignore_above": 256}
            },
        },
        "error_code": {"type": "keyword"},
        "affected_resource": {"type": "keyword"},
        # Context fields
        "context": {
            "type": "object",
            "enabled": True,
        },
        # Raw data (not indexed for search)
        "raw_data": {
            "type": "object",
            "enabled": False,
        },
        # Pattern matching fields
        "pattern_id": {"type": "keyword"},
        "pattern_matched": {"type": "boolean"},
    }
}

# Signals index settings
SIGNALS_INDEX_SETTINGS: dict[str, Any] = {
    "number_of_shards": 3,
    "number_of_replicas": 1,
    "analysis": {
        "analyzer": {
            "error_analyzer": {
                "type": "custom",
                "tokenizer": "standard",
                "filter": ["lowercase", "stop", "snowball"],
            }
        }
    },
    # Index lifecycle management
    "lifecycle": {
        "name": "signals_policy",
        "rollover_alias": "signals",
    },
}


async def create_indices(es_client) -> None:
    """
    Create all required Elasticsearch indices.

    Args:
        es_client: ElasticsearchClient instance

    Raises:
        Exception: If index creation fails
    """
    from migrationguard_ai.core.logging import get_logger

    logger = get_logger(__name__)

    # Create patterns index
    try:
        created = await es_client.create_index(
            index_name="patterns",
            mappings=PATTERNS_INDEX_MAPPING,
            settings=PATTERNS_INDEX_SETTINGS,
        )
        if created:
            logger.info("Patterns index created")
        else:
            logger.info("Patterns index already exists")
    except Exception as e:
        logger.error("Failed to create patterns index", error=str(e))
        raise

    # Create signals index
    try:
        created = await es_client.create_index(
            index_name="signals",
            mappings=SIGNALS_INDEX_MAPPING,
            settings=SIGNALS_INDEX_SETTINGS,
        )
        if created:
            logger.info("Signals index created")
        else:
            logger.info("Signals index already exists")
    except Exception as e:
        logger.error("Failed to create signals index", error=str(e))
        raise


# Common search queries

def build_similarity_query(
    error_message: str,
    error_code: str | None = None,
    merchant_id: str | None = None,
    min_score: float = 0.5,
) -> dict[str, Any]:
    """
    Build a query to find similar signals.

    Args:
        error_message: Error message to match
        error_code: Optional error code to match
        merchant_id: Optional merchant ID to filter
        min_score: Minimum similarity score (0-1)

    Returns:
        dict: Elasticsearch query DSL
    """
    must_clauses = [
        {
            "more_like_this": {
                "fields": ["error_message"],
                "like": error_message,
                "min_term_freq": 1,
                "min_doc_freq": 1,
                "minimum_should_match": "70%",
            }
        }
    ]

    if error_code:
        must_clauses.append({"term": {"error_code": error_code}})

    if merchant_id:
        must_clauses.append({"term": {"merchant_id": merchant_id}})

    return {
        "bool": {
            "must": must_clauses,
            "minimum_should_match": 1,
        }
    }


def build_pattern_match_query(
    pattern_type: str,
    time_range_minutes: int = 120,
) -> dict[str, Any]:
    """
    Build a query to find signals matching a pattern type.

    Args:
        pattern_type: Type of pattern to match
        time_range_minutes: Time window in minutes

    Returns:
        dict: Elasticsearch query DSL
    """
    return {
        "bool": {
            "must": [
                {"term": {"pattern_matched": False}},
                {
                    "range": {
                        "timestamp": {
                            "gte": f"now-{time_range_minutes}m",
                            "lte": "now",
                        }
                    }
                },
            ]
        }
    }


def build_cross_merchant_query(
    error_code: str,
    min_merchants: int = 2,
    time_range_minutes: int = 60,
) -> dict[str, Any]:
    """
    Build a query to find cross-merchant patterns.

    Args:
        error_code: Error code to search for
        min_merchants: Minimum number of merchants affected
        time_range_minutes: Time window in minutes

    Returns:
        dict: Elasticsearch query DSL with aggregations
    """
    return {
        "bool": {
            "must": [
                {"term": {"error_code": error_code}},
                {
                    "range": {
                        "timestamp": {
                            "gte": f"now-{time_range_minutes}m",
                            "lte": "now",
                        }
                    }
                },
            ]
        }
    }
