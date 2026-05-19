# AI System Monitoring Platform

> Production-grade monitoring for AI models — latency, drift, anomalies, alerts, and real-time dashboards.

---

## Overview

This platform monitors AI models in production, tracking every inference, detecting drift, identifying anomalies, and alerting your team before failures impact users.

**Modeled after:** OpenAI, Google Vertex AI, AWS SageMaker Monitoring, Datadog, MLflow, WhyLabs, Arize AI.

---

## Architecture

```
AI Models
    ↓
Inference APIs  (FastAPI — Module 1)
    ↓
Monitoring Collector  (psutil, pynvml — Module 2)
    ↓
Metrics Processing  (latency stats, P95/P99 — Module 3)
    ↓
Drift Detection  (PSI, KS-test — Module 4)
    ↓
Anomaly Detection  (Z-score, Isolation Forest — Module 5)
    ↓
Centralized Logging  (Structured JSON — Module 6)
    ↓
Alerting System  (Slack, Email — Module 7)
    ↓
Dashboard Visualization  (React UI — Module 8)
    ↓
Multi-Model Management  (register, version, compare — Module 9)
    ↓
API Management Layer  (REST endpoints — Module 10)
```

---

## Modules

| # | Module | Purpose | Key Tech |
|---|--------|---------|----------|
| 1 | Inference Tracker | Log every prediction | FastAPI, SQLite |
| 2 | Metrics Collector | CPU, RAM, GPU usage | psutil, pynvml |
| 3 | Latency Monitor | avg, P95, P99 stats | Statistical analysis |
| 4 | Drift Detector | Confidence & latency drift | PSI, KS-test |
| 5 | Anomaly Detector | Z-score + Isolation Forest | scikit-learn |
| 6 | Structured Logger | JSON logs for every event | Python logging |
| 7 | Alert Manager | Slack + Email alerts | smtplib, webhooks |
| 8 | Dashboard | Live visualization | React |
| 9 | Model Manager | Register, version, compare | SQLite |
| 10 | API Layer | REST endpoints | FastAPI |

---

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the API server

```bash
python main.py
# or
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Run with Docker

```bash
docker-compose up --build
```

### 4. Open the API docs

```
http://localhost:8000/docs
```

---

## API Endpoints

### Health
```
GET  /api/health/          Full health check
GET  /api/health/ping      Liveness probe
```

### Metrics
```
GET  /api/metrics/system           CPU, RAM, GPU, disk
GET  /api/metrics/application      Uptime, error rate, throughput
GET  /api/metrics/latency          P50, P95, P99 latency stats
GET  /api/metrics/latency/timeseries  Latency over time (charting)
GET  /api/metrics/anomalies        Anomaly summary
GET  /api/metrics/throughput       Requests per model
GET  /api/metrics/error-rate       Error rate per model
```

### Models
```
GET    /api/models/                List all models
GET    /api/models/{id}            Get model details
POST   /api/models/register        Register new model
PATCH  /api/models/{id}            Update model
DELETE /api/models/{id}            Deprecate model
GET    /api/models/{id}/health     Full model health report
GET    /api/models/{id}/compare/{id2}  Compare two models
```

### Inference
```
POST /api/inference/log          Log an inference event
GET  /api/inference/logs         Query inference logs
GET  /api/inference/logs/errors  Error-only logs
GET  /api/inference/summary      Per-model summary
```

### Drift
```
GET /api/drift/{id}/confidence   Confidence drift analysis
GET /api/drift/{id}/latency      Latency drift analysis
GET /api/drift/{id}/report       Full drift report
GET /api/drift/{id}/history      Historical drift checks
```

### Alerts
```
GET  /api/alerts/active          Active (unresolved) alerts
GET  /api/alerts/history         Alert history
GET  /api/alerts/stats           Alert statistics
POST /api/alerts/fire            Manually fire an alert
POST /api/alerts/{id}/resolve    Resolve an alert
```

---

## Configuration

| Environment Variable | Description | Default |
|---------------------|-------------|---------|
| `DB_PATH` | SQLite database path | `monitoring.db` |
| `SLACK_WEBHOOK_URL` | Slack incoming webhook | disabled |
| `SMTP_HOST` | Email SMTP host | `smtp.gmail.com` |
| `SMTP_PORT` | Email SMTP port | `587` |
| `SMTP_USER` | Email sender address | disabled |
| `SMTP_PASS` | Email sender password | disabled |
| `ALERT_EMAIL` | Alert recipient email | disabled |

---

## Running Tests

```bash
pytest tests/test_platform.py -v
```

**31 tests** covering all 10 modules:
- ✅ 7 Metrics Collector tests
- ✅ 4 Latency Monitor tests
- ✅ 4 Drift Detector tests
- ✅ 4 Anomaly Detector tests
- ✅ 4 Structured Logger tests
- ✅ 5 Alert Manager tests
- ✅ 3 Database tests

---

## Project Structure

```
ai-monitoring-platform/
│
├── main.py                       # FastAPI app entry point
│
├── api/
│   └── routes/
│       ├── metrics.py            # Metrics endpoints
│       ├── models.py             # Model management endpoints
│       ├── health.py             # Health check endpoints
│       ├── drift.py              # Drift detection endpoints
│       ├── alerts.py             # Alert endpoints
│       └── inference.py          # Inference logging endpoints
│
├── monitoring/
│   ├── collector.py              # MODULE 2: System metrics
│   ├── latency_and_drift.py     # MODULE 3 & 4: Latency + Drift
│   └── background_tasks.py       # Async background collectors
│
├── anomaly_detection/
│   └── detector.py               # MODULE 5: Anomaly detection
│
├── logging_system/
│   └── logger.py                 # MODULE 6 & 7: Logging + Alerts
│
├── database/
│   └── connection.py             # DB init, schema, seed data
│
├── tests/
│   └── test_platform.py          # 31-test full suite
│
├── docker/
│   └── Dockerfile
│
├── docker-compose.yml
├── requirements.txt
└── README.md
```

---

## Production Upgrade Path

1. **Replace SQLite → PostgreSQL** for multi-instance deployments
2. **Add Prometheus export** (`/metrics` endpoint for Grafana)
3. **Add Kafka** for real-time streaming metrics
4. **Deploy on Kubernetes** for horizontal scaling
5. **Enable GPU monitoring** (`pynvml`) on NVIDIA instances
6. **Add Evidently** for production-grade drift reports
7. **Enable auto model rollback** on drift threshold breach

---

## Resume Value

This project demonstrates:

- **Backend Engineering**: FastAPI, REST APIs, async patterns, middleware
- **AI Engineering**: inference tracking, model monitoring, drift detection
- **MLOps**: model lifecycle management, versioning, production evaluation
- **Observability**: structured logging, metrics, alerting, anomaly detection
- **Infrastructure**: Docker, modular architecture, config management
- **Testing**: 31 unit tests across all modules

Roles it targets: **AI Engineer · MLOps Engineer · Backend Engineer · AI Infrastructure Engineer · Platform Engineer · Production ML Engineer**
