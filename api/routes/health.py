"""Health check API route."""
from fastapi import APIRouter
from monitoring.collector import collector
from logging_system.logger import alert_manager
from database.connection import get_connection
from datetime import datetime, timezone

router = APIRouter()

@router.get("/")
async def health_check():
    metrics = collector.collect_all()
    app_metrics = collector.get_application_metrics()
    alert_stats = alert_manager.get_alert_stats()

    issues = []
    if metrics.get("cpu_percent", 0) > 90:
        issues.append("High CPU usage")
    if metrics.get("ram_percent", 0) > 90:
        issues.append("High RAM usage")
    if app_metrics.get("error_rate_percent", 0) > 10:
        issues.append("Elevated error rate")

    return {
        "status": "degraded" if issues else "healthy",
        "issues": issues,
        "cpu_percent": metrics.get("cpu_percent"),
        "ram_percent": metrics.get("ram_percent"),
        "uptime_seconds": app_metrics.get("uptime_seconds"),
        "active_alerts": alert_stats.get("active", 0),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

@router.get("/ping")
async def ping():
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}
