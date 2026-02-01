"""Check infrastructure connectivity and health."""

import asyncio
import sys
from typing import Dict, List, Tuple

try:
    import redis
except ImportError:
    redis = None

try:
    from elasticsearch import AsyncElasticsearch
except ImportError:
    AsyncElasticsearch = None

try:
    from kafka import KafkaProducer
    from kafka.errors import KafkaError
except ImportError:
    KafkaProducer = None
    KafkaError = None

try:
    from sqlalchemy import create_engine, text
    from sqlalchemy.exc import OperationalError
except ImportError:
    create_engine = None
    OperationalError = None


def check_postgres(host: str = "localhost", port: int = 5432, 
                   user: str = "migrationguard", password: str = "changeme",
                   db: str = "migrationguard") -> Tuple[bool, str]:
    """Check PostgreSQL connectivity."""
    if not create_engine:
        return False, "SQLAlchemy not installed"
    
    try:
        url = f"postgresql://{user}:{password}@{host}:{port}/{db}"
        engine = create_engine(url)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            return True, f"Connected - {version[:50]}..."
    except OperationalError as e:
        return False, f"Connection failed: {str(e)}"
    except Exception as e:
        return False, f"Error: {str(e)}"


def check_redis(host: str = "localhost", port: int = 6379, db: int = 0) -> Tuple[bool, str]:
    """Check Redis connectivity."""
    if not redis:
        return False, "Redis library not installed"
    
    try:
        client = redis.Redis(host=host, port=port, db=db, socket_connect_timeout=5)
        client.ping()
        info = client.info()
        return True, f"Connected - Redis {info['redis_version']}"
    except redis.ConnectionError as e:
        return False, f"Connection failed: {str(e)}"
    except Exception as e:
        return False, f"Error: {str(e)}"


def check_kafka(bootstrap_servers: List[str] = None) -> Tuple[bool, str]:
    """Check Kafka connectivity."""
    if not KafkaProducer:
        return False, "kafka-python not installed"
    
    if bootstrap_servers is None:
        bootstrap_servers = ["localhost:9092"]
    
    try:
        # Try to create a producer
        producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            request_timeout_ms=5000,
            api_version_auto_timeout_ms=5000
        )
        metadata = producer.list_topics(timeout=5)
        producer.close()
        return True, f"Connected - {len(metadata)} topics available"
    except KafkaError as e:
        return False, f"Connection failed: {str(e)}"
    except Exception as e:
        return False, f"Error: {str(e)}"


async def check_elasticsearch(hosts: List[str] = None) -> Tuple[bool, str]:
    """Check Elasticsearch connectivity."""
    if not AsyncElasticsearch:
        return False, "Elasticsearch library not installed"
    
    if hosts is None:
        hosts = ["http://localhost:9200"]
    
    try:
        client = AsyncElasticsearch(hosts=hosts, request_timeout=5)
        info = await client.info()
        version = info['version']['number']
        await client.close()
        return True, f"Connected - Elasticsearch {version}"
    except Exception as e:
        return False, f"Connection failed: {str(e)}"


async def main():
    """Run all infrastructure checks."""
    print("=" * 60)
    print("MigrationGuard AI - Infrastructure Health Check")
    print("=" * 60)
    print()
    
    checks = {
        "PostgreSQL": check_postgres(),
        "Redis": check_redis(),
        "Kafka": check_kafka(),
        "Elasticsearch": await check_elasticsearch(),
    }
    
    all_healthy = True
    for service, (healthy, message) in checks.items():
        status = "✓" if healthy else "✗"
        print(f"{status} {service:20} {message}")
        if not healthy:
            all_healthy = False
    
    print()
    print("=" * 60)
    if all_healthy:
        print("✓ All services are healthy!")
        sys.exit(0)
    else:
        print("✗ Some services are not available")
        print("\nTo start services, run:")
        print("  docker-compose up -d")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
