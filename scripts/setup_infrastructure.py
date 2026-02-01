"""Setup infrastructure: create Kafka topics and Elasticsearch indices."""

import asyncio
import sys
from typing import List

from elasticsearch import AsyncElasticsearch
from kafka.admin import KafkaAdminClient, NewTopic
from kafka.errors import TopicAlreadyExistsError


async def create_elasticsearch_indices(hosts: List[str] = None):
    """Create Elasticsearch indices for MigrationGuard AI."""
    if hosts is None:
        hosts = ["http://localhost:9200"]
    
    print("\n📊 Setting up Elasticsearch indices...")
    
    client = AsyncElasticsearch(hosts=hosts)
    
    # Define index mappings
    indices = {
        "migrationguard-signals": {
            "mappings": {
                "properties": {
                    "signal_id": {"type": "keyword"},
                    "timestamp": {"type": "date"},
                    "source": {"type": "keyword"},
                    "signal_type": {"type": "keyword"},
                    "severity": {"type": "keyword"},
                    "merchant_id": {"type": "keyword"},
                    "metadata": {"type": "object", "enabled": False},
                    "normalized_data": {"type": "object", "enabled": False},
                }
            }
        },
        "migrationguard-patterns": {
            "mappings": {
                "properties": {
                    "pattern_id": {"type": "keyword"},
                    "pattern_type": {"type": "keyword"},
                    "description": {"type": "text"},
                    "severity": {"type": "keyword"},
                    "confidence": {"type": "float"},
                    "signals": {"type": "keyword"},
                    "metadata": {"type": "object", "enabled": False},
                    "created_at": {"type": "date"},
                }
            }
        },
        "migrationguard-issues": {
            "mappings": {
                "properties": {
                    "issue_id": {"type": "keyword"},
                    "title": {"type": "text"},
                    "description": {"type": "text"},
                    "severity": {"type": "keyword"},
                    "status": {"type": "keyword"},
                    "merchant_id": {"type": "keyword"},
                    "root_cause": {"type": "object", "enabled": False},
                    "created_at": {"type": "date"},
                    "updated_at": {"type": "date"},
                }
            }
        },
    }
    
    for index_name, index_config in indices.items():
        try:
            exists = await client.indices.exists(index=index_name)
            if exists:
                print(f"  ✓ Index '{index_name}' already exists")
            else:
                await client.indices.create(index=index_name, body=index_config)
                print(f"  ✓ Created index '{index_name}'")
        except Exception as e:
            print(f"  ✗ Error creating index '{index_name}': {e}")
    
    await client.close()


def create_kafka_topics(bootstrap_servers: List[str] = None):
    """Create Kafka topics for MigrationGuard AI."""
    if bootstrap_servers is None:
        bootstrap_servers = ["localhost:9092"]
    
    print("\n📨 Setting up Kafka topics...")
    
    admin_client = KafkaAdminClient(
        bootstrap_servers=bootstrap_servers,
        client_id="migrationguard-setup"
    )
    
    # Define topics
    topics = [
        NewTopic(name="signals", num_partitions=3, replication_factor=1),
        NewTopic(name="patterns", num_partitions=2, replication_factor=1),
        NewTopic(name="decisions", num_partitions=2, replication_factor=1),
        NewTopic(name="actions", num_partitions=2, replication_factor=1),
        NewTopic(name="audit-trail", num_partitions=1, replication_factor=1),
    ]
    
    for topic in topics:
        try:
            admin_client.create_topics([topic], validate_only=False)
            print(f"  ✓ Created topic '{topic.name}'")
        except TopicAlreadyExistsError:
            print(f"  ✓ Topic '{topic.name}' already exists")
        except Exception as e:
            print(f"  ✗ Error creating topic '{topic.name}': {e}")
    
    admin_client.close()


async def main():
    """Run infrastructure setup."""
    print("=" * 60)
    print("MigrationGuard AI - Infrastructure Setup")
    print("=" * 60)
    
    try:
        # Create Kafka topics
        create_kafka_topics()
        
        # Create Elasticsearch indices
        await create_elasticsearch_indices()
        
        print("\n" + "=" * 60)
        print("✓ Infrastructure setup complete!")
        print("=" * 60)
        sys.exit(0)
        
    except Exception as e:
        print(f"\n✗ Setup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
