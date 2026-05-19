"""
MODULE 1 — MODEL INFERENCE TRACKER
Log and query inference requests, responses, and performance.
"""

from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime, timezone
import time
from database.connection import get_connection
from monitoring.collector import collector
from logging_system.logger import platform_logger

router = APIRouter()


class InferenceLogRequest(BaseModel):
    model_id: str
    request_id: Optional[str] = None
    input_data: Optional[Any] = None
    output_data: Optional[Any] = None
    confidence: Optional[float] = None
    latency_ms: float
    status: str = "success"
    error_message: Optional[str] = None


@router.post("/log")
async def log_inference(req: InferenceLogRequest):
    """Log a single inference event."""
    import json
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO inference_logs
        (model_id, request_id, input_data, output_data, confidence,
         latency_ms, status, error_message, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        req.model_id,
        req.request_id,
        json.dumps(req.input_data) if req.input_data else None,
        json.dumps(req.output_data) if req.output_data else None,
        req.confidence,
        req.latency_ms,
        req.status,
        req.error_message,
        datetime.now(timezone.utc).isoformat(),
    ))
    conn.commit()
    inference_id = cursor.lastrowid
    conn.close()

    collector.record_inference(req.latency_ms, req.status == "success")
    platform_logger.log_inference(
        req.model_id, req.latency_ms, req.status, req.confidence, req.error_message
    )
    return {"status": "logged", "inference_id": inference_id}


@router.get("/logs")
async def get_inference_logs(
    model_id: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500),
    status: Optional[str] = None,
):
    conn = get_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM inference_logs WHERE 1=1"
    params = []
    if model_id:
        query += " AND model_id = ?"
        params.append(model_id)
    if status:
        query += " AND status = ?"
        params.append(status)
    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return {"logs": [dict(r) for r in rows], "count": len(rows)}


@router.get("/logs/errors")
async def get_error_logs(
    model_id: Optional[str] = None,
    limit: int = Query(20, ge=1, le=200)
):
    conn = get_connection()
    cursor = conn.cursor()
    query = """
        SELECT * FROM inference_logs
        WHERE status = 'error'
    """
    params = []
    if model_id:
        query += " AND model_id = ?"
        params.append(model_id)
    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return {"errors": [dict(r) for r in rows], "count": len(rows)}


@router.get("/summary")
async def get_inference_summary(minutes: int = Query(60, ge=5, le=1440)):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            model_id,
            COUNT(*) as total,
            SUM(CASE WHEN status='success' THEN 1 ELSE 0 END) as successes,
            SUM(CASE WHEN status='error' THEN 1 ELSE 0 END) as errors,
            AVG(latency_ms) as avg_latency_ms,
            AVG(confidence) as avg_confidence,
            MIN(timestamp) as first_request,
            MAX(timestamp) as last_request
        FROM inference_logs
        WHERE timestamp > datetime('now', ?)
        GROUP BY model_id
        ORDER BY total DESC
    """, (f"-{minutes} minutes",))
    rows = cursor.fetchall()
    conn.close()
    return {
        "window_minutes": minutes,
        "summary": [dict(r) for r in rows]
    }
