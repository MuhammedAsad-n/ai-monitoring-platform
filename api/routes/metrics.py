"""
MODULE 10 — API MANAGEMENT LAYER
All REST API routes for the monitoring platform.
"""

# ── metrics.py ────────────────────────────────────────────────

from fastapi import APIRouter, Query
from typing import Optional
from monitoring.collector import collector
from monitoring.latency_and_drift import latency_monitor
from anomaly_detection.detector import anomaly_detector
from database.connection import get_connection

router = APIRouter()


@router.get("/system")
async def get_system_metrics():
    """Real-time system metrics — CPU, RAM, GPU, disk."""
    return collector.collect_all()


@router.get("/application")
async def get_application_metrics():
    return collector.get_application_metrics()


@router.get("/latency")
async def get_latency_metrics(
    model_id: Optional[str] = None,
    minutes: int = Query(60, ge=5, le=1440)
):
    return latency_monitor.get_latency_stats(model_id=model_id, minutes=minutes)


@router.get("/latency/timeseries")
async def get_latency_timeseries(
    model_id: Optional[str] = None,
    minutes: int = Query(60, ge=5, le=1440)
):
    return latency_monitor.get_latency_over_time(model_id=model_id, minutes=minutes)


@router.get("/anomalies")
async def get_anomalies():
    return anomaly_detector.get_anomaly_summary()


@router.get("/anomalies/latency")
async def get_latency_anomalies(model_id: Optional[str] = None):
    return anomaly_detector.detect_latency_anomalies(model_id=model_id)


@router.get("/anomalies/traffic")
async def get_traffic_anomalies():
    return anomaly_detector.detect_traffic_anomalies()


@router.get("/throughput")
async def get_throughput(minutes: int = Query(60, ge=5, le=1440)):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            model_id,
            COUNT(*) as total_requests,
            SUM(CASE WHEN status='success' THEN 1 ELSE 0 END) as successes,
            SUM(CASE WHEN status='error' THEN 1 ELSE 0 END) as errors,
            AVG(latency_ms) as avg_latency_ms,
            MIN(latency_ms) as min_latency_ms,
            MAX(latency_ms) as max_latency_ms
        FROM inference_logs
        WHERE timestamp > datetime('now', ?)
        GROUP BY model_id
        ORDER BY total_requests DESC
    """, (f"-{minutes} minutes",))
    rows = cursor.fetchall()
    conn.close()
    return {
        "window_minutes": minutes,
        "models": [dict(r) for r in rows]
    }


@router.get("/error-rate")
async def get_error_rate(minutes: int = Query(60, ge=5)):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            model_id,
            COUNT(*) as total,
            SUM(CASE WHEN status='error' THEN 1.0 ELSE 0 END) / COUNT(*) * 100 as error_rate
        FROM inference_logs
        WHERE timestamp > datetime('now', ?)
        GROUP BY model_id
    """, (f"-{minutes} minutes",))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]
