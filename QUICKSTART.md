# MigrationGuard AI - Quick Start Guide

Get the complete agentic AI system running in under 10 minutes!

## What You'll Get

A fully functional agentic AI system that:
- **Observes** signals from multiple sources (API errors, support tickets, webhooks)
- **Detects patterns** across signals using Elasticsearch
- **Reasons** about root causes using Claude AI (with rule-based fallback)
- **Decides** on actions with risk assessment and safety controls
- **Acts** autonomously with human oversight integration
- **Learns** from outcomes through feedback loops

## Prerequisites

1. **Docker Desktop** - [Download here](https://www.docker.com/products/docker-desktop/)
2. **Python 3.11+** with `uv` - [Install uv](https://docs.astral.sh/uv/getting-started/installation/)
3. **Git** (already installed if you cloned this repo)

## Quick Setup (Windows)

### Option 1: Automated Setup (Recommended)

```cmd
cd migrationguard-ai
setup.cmd
```

This script will:
1. Check Docker is running
2. Start all infrastructure services
3. Wait for services to be healthy
4. Run database migrations
5. Create Kafka topics and Elasticsearch indices

### Option 2: Manual Setup

```cmd
cd migrationguard-ai

REM 1. Start infrastructure
docker-compose up -d

REM 2. Wait 30 seconds for services to start
timeout /t 30

REM 3. Check connectivity
uv run python scripts/check_infrastructure.py

REM 4. Run migrations
uv run alembic upgrade head

REM 5. Setup Kafka and Elasticsearch
uv run python scripts/setup_infrastructure.py
```

## Verify Setup

Check all services are healthy:

```cmd
docker-compose ps
```

All services should show "healthy" status.

## Run the Demo

The demo showcases the complete agentic AI system:

```cmd
uv run python demo_agent_system.py
```

You'll see:
- **Scenario 1**: Authentication errors → Pattern detection → Root cause analysis → Support ticket creation
- **Scenario 2**: Safe mode activation → All actions require approval → Manual deactivation

## Run Tests

Verify everything works:

```cmd
uv run pytest tests/unit/ -v
```

Expected: **200+ tests passing** with high coverage.

## Start the API Server

```cmd
uv run uvicorn src.migrationguard_ai.api.app:app --reload
```

API will be available at: http://localhost:8000

API docs: http://localhost:8000/docs

## Start the Frontend (Optional)

```cmd
cd frontend
npm install
npm run dev
```

Frontend will be available at: http://localhost:3000

## Access Monitoring Tools

- **Grafana**: http://localhost:3001 (admin/admin)
- **Kibana**: http://localhost:5601
- **Prometheus**: http://localhost:9090
- **Elasticsearch**: http://localhost:9200

## What Makes This "Agentic"?

This system goes **far beyond a single LLM call**:

### 1. **State Management**
- Persistent state across the observe-reason-decide-act loop
- Issue tracking from signal ingestion to action execution
- Audit trail for all decisions and actions

### 2. **Multi-Step Reasoning**
- Pattern detection across multiple signals
- Root cause analysis with evidence gathering
- Decision-making with risk assessment
- Action planning with safety controls

### 3. **Tool Usage**
- **Decision Engine**: Risk-based decision making
- **Action Executor**: Safe action execution with rate limiting
- **Pattern Detector**: Cross-signal correlation
- **Root Cause Analyzer**: Multi-step reasoning (Claude AI + rule-based fallback)
- **Safe Mode Manager**: Emergency controls
- **Circuit Breakers**: Fault tolerance

### 4. **Feedback Loops**
- Outcome tracking after action execution
- Confidence calibration based on results
- Adaptive behavior (safe mode triggers on failures)
- Learning from patterns

### 5. **Safety Layers**
- **Safe Mode**: Stops automated actions on critical errors
- **Circuit Breakers**: Prevents cascade failures
- **Graceful Degradation**: Falls back to rule-based reasoning
- **Rate Limiting**: Prevents action spam
- **Human Oversight**: Approval requirements for high-risk actions

### 6. **Autonomous Operation**
- Continuous signal monitoring
- Automatic pattern detection
- Self-healing capabilities
- Proactive issue resolution

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                   AGENTIC AI SYSTEM                          │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  1. OBSERVE                                                   │
│     ├─ Signal Ingestion (API, Webhooks, Support)            │
│     ├─ Normalization                                         │
│     └─ State Tracking                                        │
│                                                               │
│  2. DETECT PATTERNS                                          │
│     ├─ Cross-Signal Correlation                             │
│     ├─ Temporal Analysis                                     │
│     └─ Pattern Matching (Elasticsearch)                      │
│                                                               │
│  3. REASON (Root Cause Analysis)                            │
│     ├─ Claude AI Analysis (primary)                         │
│     ├─ Rule-Based Fallback (graceful degradation)           │
│     ├─ Evidence Gathering                                    │
│     └─ Confidence Scoring                                    │
│                                                               │
│  4. DECIDE                                                   │
│     ├─ Risk Assessment                                       │
│     ├─ Action Selection                                      │
│     ├─ Safety Checks (Safe Mode, Circuit Breakers)          │
│     └─ Approval Requirements                                 │
│                                                               │
│  5. ACT                                                      │
│     ├─ Action Execution                                      │
│     ├─ Rate Limiting                                         │
│     ├─ Retry Logic                                           │
│     └─ Result Tracking                                       │
│                                                               │
│  6. LEARN (Feedback Loop)                                    │
│     ├─ Outcome Analysis                                      │
│     ├─ Confidence Calibration                                │
│     ├─ Pattern Refinement                                    │
│     └─ Adaptive Behavior                                     │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## Infrastructure Components

| Service | Purpose | Port |
|---------|---------|------|
| PostgreSQL + TimescaleDB | Time-series signal storage | 5432 |
| Redis | Caching, rate limiting, buffering | 6379 |
| Kafka | Event streaming, async processing | 9092 |
| Elasticsearch | Pattern search, full-text search | 9200 |
| Kibana | Elasticsearch visualization | 5601 |
| Prometheus | Metrics collection | 9090 |
| Grafana | Metrics dashboards | 3001 |

## Key Features Demonstrated

### ✅ Proper Agent Behavior
- Autonomous operation with minimal human intervention
- State persistence across the decision loop
- Multi-step reasoning chains
- Tool usage and orchestration

### ✅ Safety & Reliability
- Safe mode for critical errors
- Circuit breakers for external services
- Graceful degradation (Claude → rule-based)
- Rate limiting and retry logic

### ✅ Human Oversight
- Approval requirements for high-risk actions
- Audit trail for all decisions
- Manual safe mode activation/deactivation
- Feedback integration

### ✅ Production-Ready
- Comprehensive test coverage (200+ tests)
- Monitoring and observability
- Error handling and logging
- Scalable architecture

## Next Steps

1. **Configure Claude API** (optional, system works with rule-based fallback):
   ```
   Edit .env file:
   ANTHROPIC_API_KEY=your-api-key-here
   ```

2. **Explore the API**:
   - Visit http://localhost:8000/docs
   - Try the `/api/v1/signals` endpoint
   - Test the `/api/v1/issues` endpoint

3. **View Metrics**:
   - Open Grafana: http://localhost:3001
   - Add Prometheus datasource
   - Create dashboards for signal rates, decision latency, action success rates

4. **Customize Patterns**:
   - Edit `services/pattern_detector.py`
   - Add new pattern types
   - Adjust confidence thresholds

5. **Add Actions**:
   - Edit `services/action_executor.py`
   - Implement new action types
   - Add integrations (Slack, PagerDuty, etc.)

## Troubleshooting

### Docker not running
```cmd
REM Start Docker Desktop, then:
docker ps
```

### Services not healthy
```cmd
REM Check logs:
docker-compose logs [service-name]

REM Restart services:
docker-compose restart
```

### Database connection errors
```cmd
REM Reset database:
docker-compose down -v
docker-compose up -d postgres
timeout /t 10
uv run alembic upgrade head
```

### Tests failing
```cmd
REM Ensure infrastructure is running:
uv run python scripts/check_infrastructure.py

REM Run tests with verbose output:
uv run pytest tests/unit/ -v -s
```

## Stopping Services

```cmd
REM Stop all services:
docker-compose down

REM Stop and remove all data:
docker-compose down -v
```

## Documentation

- **Full Setup Guide**: [INFRASTRUCTURE_SETUP.md](INFRASTRUCTURE_SETUP.md)
- **Demo Explanation**: [README_DEMO.md](README_DEMO.md)
- **Development Guide**: [DEVELOPMENT.md](DEVELOPMENT.md)
- **API Documentation**: http://localhost:8000/docs (when running)

## Support

For issues:
1. Check service logs: `docker-compose logs [service]`
2. Run health check: `uv run python scripts/check_infrastructure.py`
3. Review documentation
4. Check test output: `uv run pytest tests/unit/ -v`

---

**Ready to see the agent in action?**

```cmd
uv run python demo_agent_system.py
```

🚀 **Let's go!**
