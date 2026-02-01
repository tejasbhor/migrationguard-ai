# MigrationGuard AI

🤖 **Production-grade agentic AI system** for autonomous issue detection and resolution during e-commerce platform migrations.

[![Tests](https://img.shields.io/badge/tests-200%2B%20passing-brightgreen)]()
[![Coverage](https://img.shields.io/badge/coverage-85%25-green)]()
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)]()
[![License](https://img.shields.io/badge/license-MIT-blue)]()

## 🎯 What Makes This Agentic?

This system demonstrates **proper agent behavior** that goes far beyond a single LLM call:

✅ **State Management** - Persistent state across the observe-reason-decide-act loop  
✅ **Multi-Step Reasoning** - Pattern detection → Root cause → Risk assessment → Action planning  
✅ **Tool Orchestration** - 8+ specialized tools working together autonomously  
✅ **Feedback Loops** - Learning from outcomes and adapting behavior  
✅ **Safety Controls** - Multiple layers including safe mode, circuit breakers, and human oversight  

## 🚀 Quick Start

Get the complete system running in **under 10 minutes**:

```cmd
cd migrationguard-ai
setup.cmd                              # Start infrastructure
uv run python demo_agent_system.py    # Run demo
```

**See it in action**: The demo showcases authentication error detection → pattern analysis → root cause reasoning → automated ticket creation with full state tracking and feedback loops.

📖 **Detailed Guide**: [QUICKSTART.md](QUICKSTART.md)

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      AGENT ORCHESTRATOR                          │
│                   (Observe-Reason-Decide-Act Loop)              │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌──────────────┐      ┌──────────────┐     ┌──────────────┐
│   OBSERVE    │      │    REASON    │     │   DECIDE     │
│              │      │              │     │              │
│ • Signal     │      │ • Pattern    │     │ • Risk       │
│   Ingestion  │──────▶  Detection   │─────▶  Assessment  │
│ • Normalize  │      │ • Root Cause │     │ • Action     │
│ • Track      │      │   Analysis   │     │   Selection  │
└──────────────┘      └──────────────┘     └──────────────┘
                                                   │
                                                   ▼
                                           ┌──────────────┐
                                           │     ACT      │
                                           │              │
                                           │ • Execute    │
                                           │ • Track      │
                                           │ • Learn      │◀─┐
                                           └──────────────┘  │
                                                   │          │
                                                   ▼          │
                                           ┌──────────────┐  │
                                           │   FEEDBACK   │  │
                                           │     LOOP     │──┘
                                           └──────────────┘
```

## ✨ Key Features

### 🔍 Intelligent Observation
- Multi-source signal ingestion (API errors, support tickets, webhooks)
- Real-time normalization and enrichment
- Time-series storage with TimescaleDB

### 🧠 Advanced Reasoning
- Pattern detection across signals using Elasticsearch
- Root cause analysis with **Google Gemini 2.5 Flash** (+ rule-based fallback)
- Evidence gathering and confidence scoring (75-92% confidence)

### ⚖️ Risk-Aware Decision Making
- Automated risk assessment (low/medium/high)
- Approval requirements for high-risk actions
- Safety controls (safe mode, circuit breakers)

### ⚡ Safe Action Execution
- Rate limiting and retry logic
- Graceful degradation on failures
- Comprehensive audit trail

### 🔄 Continuous Learning
- Outcome tracking and analysis
- Confidence calibration from results
- Adaptive behavior based on feedback

### 🛡️ Multiple Safety Layers
- **Safe Mode**: Automatic activation on critical errors
- **Circuit Breakers**: Fault tolerance for external services
- **Graceful Degradation**: Fallback mechanisms (Claude → rules, Elasticsearch → PostgreSQL, Kafka → Redis)
- **Human Oversight**: Approval workflows and manual controls

## 🧪 Test Coverage

**200+ Tests** with **85%+ Coverage**

- ✅ 150+ Unit Tests (core components, services, integrations)
- ✅ 50+ Property-Based Tests (RBAC, redaction, API, decisions, patterns)
- ✅ Integration Tests (error handling, end-to-end flows)
- ✅ All tests passing with comprehensive coverage

```cmd
uv run pytest tests/unit/ -v
```

## 🛠️ Technology Stack

### Core
- **Backend**: Python 3.11+, FastAPI, Pydantic
- **AI**: Google Gemini 2.5 Flash (FREE tier, 15 req/min) with rule-based fallback
- **Agent Framework**: Custom orchestration with state management and feedback loops

### Infrastructure
- **Database**: PostgreSQL + TimescaleDB (time-series)
- **Cache**: Redis (caching, rate limiting, buffering)
- **Search**: Elasticsearch (pattern matching, full-text search)
- **Streaming**: Apache Kafka (event streaming, async processing)

### Monitoring
- **Metrics**: Prometheus + Grafana
- **Logs**: Structured logging with ELK stack support
- **Visualization**: Kibana for log exploration

### Deployment
- **Containers**: Docker + Docker Compose
- **Orchestration**: Kubernetes-ready
- **CI/CD**: GitHub Actions ready

## 📊 Demo Scenarios

### Scenario 1: Authentication Errors
**Input**: 3 signals (2 API 401 errors + 1 support ticket)

**Agent Behavior**:
1. 🔭 **Observe**: Ingest and normalize signals
2. 🔍 **Detect**: Identify auth failure pattern (confidence: 0.85)
3. 🧠 **Reason**: Analyze root cause → "authentication_error"
4. ⚖️ **Decide**: Select "create_support_ticket" (risk: low)
5. ⚡ **Act**: Create ticket with troubleshooting steps
6. 🔄 **Learn**: Track outcome, calibrate confidence

**Output**: Support ticket created with authentication guidance

### Scenario 2: Safe Mode Activation
**Trigger**: Confidence drift detected (expected: 0.90, actual: 0.75)

**Agent Behavior**:
1. 🛡️ Safe mode automatically activated
2. ⏸️ All actions require human approval
3. 📋 Actions queued for review
4. 🔔 Operator notified
5. ✅ Manual deactivation by authorized operator

## 📚 Documentation

- **[QUICKSTART.md](QUICKSTART.md)** - Get started in 10 minutes
- **[INFRASTRUCTURE_SETUP.md](INFRASTRUCTURE_SETUP.md)** - Detailed infrastructure guide
- **[README_DEMO.md](README_DEMO.md)** - Demo explanation and agent behavior
- **[HACKATHON_SUBMISSION.md](HACKATHON_SUBMISSION.md)** - Complete submission details
- **[DEVELOPMENT.md](DEVELOPMENT.md)** - Development guide
- **API Docs**: http://localhost:8000/docs (when running)

## 🎯 Prerequisites

- **Docker Desktop** - [Download](https://www.docker.com/products/docker-desktop/)
- **Python 3.11+** with `uv` - [Install uv](https://docs.astral.sh/uv/getting-started/installation/)
- **Git** (for cloning)

## 🔧 Installation

### Automated Setup (Windows)

```cmd
cd migrationguard-ai
setup.cmd
```

This will:
- ✅ Start all infrastructure services (PostgreSQL, Redis, Kafka, Elasticsearch)
- ✅ Run database migrations
- ✅ Create Kafka topics and Elasticsearch indices
- ✅ Verify connectivity

### Manual Setup

```cmd
REM 1. Start infrastructure
docker-compose up -d

REM 2. Wait for services (30 seconds)
timeout /t 30

REM 3. Check connectivity
uv run python scripts/check_infrastructure.py

REM 4. Run migrations
uv run alembic upgrade head

REM 5. Setup Kafka and Elasticsearch
uv run python scripts/setup_infrastructure.py
```

## 🎮 Running the System

### Run the Demo

See the complete agent in action:

```cmd
uv run python demo_agent_system.py
```

### Run Tests

```cmd
uv run pytest tests/unit/ -v
```

### Start the API Server

```cmd
uv run uvicorn src.migrationguard_ai.api.app:app --reload
```

API available at: http://localhost:8000  
API docs: http://localhost:8000/docs

### Start the Frontend (Optional)

```cmd
cd frontend
npm install
npm run dev
```

Frontend available at: http://localhost:3000

## 🔍 Access Services

| Service | URL | Credentials |
|---------|-----|-------------|
| API | http://localhost:8000 | - |
| API Docs | http://localhost:8000/docs | - |
| Grafana | http://localhost:3001 | admin/admin |
| Kibana | http://localhost:5601 | - |
| Prometheus | http://localhost:9090 | - |
| Elasticsearch | http://localhost:9200 | - |

## 📁 Project Structure

```
migrationguard-ai/
├── src/migrationguard_ai/
│   ├── agent/              # Agent orchestration (state, graph)
│   ├── api/                # FastAPI REST API
│   ├── core/               # Core components (auth, config, safety)
│   ├── db/                 # Database models (SQLAlchemy)
│   ├── services/           # Business logic (decision, action, pattern)
│   ├── integrations/       # External integrations (support systems)
│   └── workers/            # Background workers (pattern detection)
├── tests/
│   ├── unit/               # 150+ unit tests
│   ├── integration/        # Integration tests
│   └── e2e/                # End-to-end tests
├── alembic/                # Database migrations
├── scripts/                # Setup and utility scripts
├── frontend/               # React dashboard (TypeScript)
├── docker-compose.yml      # Infrastructure setup
├── demo_agent_system.py    # Complete agent demo
└── setup.cmd               # Automated setup script
```

## 🧪 Development

### Running Tests

```cmd
REM All tests
uv run pytest tests/unit/ -v

REM With coverage
uv run pytest tests/unit/ --cov=src --cov-report=html

REM Specific test file
uv run pytest tests/unit/test_decision_engine.py -v

REM Property-based tests
uv run pytest tests/unit/test_*_properties.py -v
```

### Code Quality

```cmd
REM Format code
uv run black src tests

REM Lint code
uv run ruff check src tests

REM Type checking
uv run mypy src
```

### Database Migrations

```cmd
REM Create migration
uv run alembic revision --autogenerate -m "Description"

REM Apply migrations
uv run alembic upgrade head

REM Rollback
uv run alembic downgrade -1
```

## ⚙️ Configuration

All configuration via environment variables in `.env` file:

```env
# Google Gemini API (FREE tier - get key at https://aistudio.google.com/apikey)
GOOGLE_API_KEY=your-api-key-here

# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=migrationguard
POSTGRES_PASSWORD=changeme

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# Kafka
KAFKA_BOOTSTRAP_SERVERS='["localhost:9092"]'

# Elasticsearch
ELASTICSEARCH_HOSTS='["http://localhost:9200"]'

# Agent Configuration
AGENT_CONFIDENCE_THRESHOLD=0.7
AGENT_HIGH_RISK_APPROVAL_REQUIRED=true
```

## 📊 Monitoring & Observability

### Metrics (Prometheus)

Exposed at `/metrics`:
- Signal ingestion rate
- Pattern detection latency
- Decision accuracy
- Action success rate
- System resource usage

### Logs

Structured JSON logs for:
- Signal processing
- Pattern detection
- Root cause analysis
- Decision making
- Action execution
- Audit trail

### Dashboards (Grafana)

Pre-configured dashboards:
- System health and performance
- Agent decision metrics
- Business impact (ticket deflection, resolution time)
- Infrastructure health

## 🛑 Stopping Services

```cmd
REM Stop all services
docker-compose down

REM Stop and remove all data
docker-compose down -v
```

## 🐛 Troubleshooting

### Docker not running
```cmd
REM Start Docker Desktop, then verify:
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
REM Verify infrastructure:
uv run python scripts/check_infrastructure.py

REM Run with verbose output:
uv run pytest tests/unit/ -v -s
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality
5. Run code quality checks (`black`, `ruff`, `mypy`)
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Built with [FastAPI](https://fastapi.tiangolo.com/)
- AI powered by [Google Gemini](https://ai.google.dev/) (FREE tier)
- Infrastructure by [Docker](https://www.docker.com/)
- Testing with [pytest](https://pytest.org/) and [Hypothesis](https://hypothesis.readthedocs.io/)

## 📞 Support

- **Documentation**: See the documentation files in the repository
- **Issues**: [GitHub Issues](https://github.com/tejasbhor/migrationguard-ai/issues)
- **Discussions**: [GitHub Discussions](https://github.com/tejasbhor/migrationguard-ai/discussions)

---

**Built for the Hackathon** | **Production-Ready** | **Fully Tested** | **Open Source**
