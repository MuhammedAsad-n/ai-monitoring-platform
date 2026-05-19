"""
AI System Monitoring Platform
Production-grade monitoring for AI models in real-time.
"""

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from api.routes import metrics, models, health, drift, alerts, inference, advanced, prometheus
from monitoring.collector import MetricsCollector
from database.connection import init_db
from monitoring.background_tasks import start_background_tasks
from config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Starting AI Monitoring Platform...")
    logger.info(f"   Environment : {settings.environment}")
    logger.info(f"   DB path     : {settings.database.path}")
    logger.info(f"   Sim traffic : {settings.monitoring.simulate_traffic}")
    await init_db()
    await start_background_tasks()
    logger.info("✅ Platform ready — docs at /docs")
    yield
    logger.info("🛑 Shutting down AI Monitoring Platform...")


app = FastAPI(
    title="AI System Monitoring Platform",
    description=(
        "Production-grade monitoring for AI models — "
        "latency, drift, anomalies, auto-rollback, failure prediction, and alerts."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Core modules
app.include_router(health.router,     prefix="/api/health",      tags=["Health"])
app.include_router(metrics.router,    prefix="/api/metrics",     tags=["Metrics"])
app.include_router(models.router,     prefix="/api/models",      tags=["Models"])
app.include_router(inference.router,  prefix="/api/inference",   tags=["Inference"])
app.include_router(drift.router,      prefix="/api/drift",       tags=["Drift"])
app.include_router(alerts.router,     prefix="/api/alerts",      tags=["Alerts"])

# Advanced modules
app.include_router(advanced.router,   prefix="/api/advanced",    tags=["Advanced"])
app.include_router(prometheus.router, prefix="/api",             tags=["Prometheus"])


@app.get("/", tags=["Root"])
async def root():
    return {
        "platform": "AI System Monitoring Platform",
        "version": "1.0.0",
        "status": "running",
        "environment": settings.environment,
        "docs": "/docs",
        "health": "/api/health",
        "prometheus_metrics": "/api/metrics",
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.server.host,
        port=settings.server.port,
        reload=settings.server.reload,
        log_level=settings.server.log_level,
        workers=settings.server.workers,
    )
