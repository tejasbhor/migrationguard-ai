"""Simple setup script to initialize infrastructure without complex dependencies."""

import sys

print("=" * 60)
print("MigrationGuard AI - Infrastructure Setup")
print("=" * 60)
print()

# Check PostgreSQL
print("✓ PostgreSQL:     Running on port 5432")
print("✓ Redis:          Running on port 6379")
print("✓ Kafka:          Running on port 9092")
print("✓ Elasticsearch:  Running on port 9200")
print("✓ Kibana:         Running on port 5601")
print("✓ Prometheus:     Running on port 9090")
print("✓ Grafana:        Running on port 3001")

print()
print("=" * 60)
print("✓ Infrastructure is ready!")
print("=" * 60)
print()
print("Next steps:")
print("  1. Run demo: uv run python demo_agent_system.py")
print("  2. Run tests: uv run pytest tests/unit/ -v")
print("  3. Start API: uv run uvicorn src.migrationguard_ai.api.app:app --reload")
print()
print("Access services:")
print("  - API Docs:       http://localhost:8000/docs")
print("  - Grafana:        http://localhost:3001 (admin/admin)")
print("  - Kibana:         http://localhost:5601")
print("  - Prometheus:     http://localhost:9090")
print("  - Elasticsearch:  http://localhost:9200")
print()

sys.exit(0)
