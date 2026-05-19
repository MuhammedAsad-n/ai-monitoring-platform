"""
MODULE 9 — MULTI-MODEL MANAGEMENT API
Register, list, update, and compare AI models.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
from database.connection import get_connection
from anomaly_detection.detector import anomaly_detector
from logging_system.logger import platform_logger

router = APIRouter()


class RegisterModelRequest(BaseModel):
    model_id: str
    name: str
    version: str
    description: Optional[str] = None
    endpoint: Optional[str] = None


class UpdateModelRequest(BaseModel):
    status: Optional[str] = None
    description: Optional[str] = None
    endpoint: Optional[str] = None


@router.get("/")
async def list_models():
    """List all registered models with health summary."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM registered_models ORDER BY created_at DESC")
    models = [dict(r) for r in cursor.fetchall()]
    conn.close()

    # Enrich each model with basic stats
    for model in models:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                COUNT(*) as requests_1h,
                AVG(latency_ms) as avg_latency,
                SUM(CASE WHEN status='error' THEN 1.0 ELSE 0 END) / NULLIF(COUNT(*), 0) * 100 as error_rate
            FROM inference_logs
            WHERE model_id = ? AND timestamp > datetime('now', '-1 hour')
        """, (model["model_id"],))
        stats = dict(cursor.fetchone())
        conn.close()
        model["stats_1h"] = stats

    return {"models": models, "total": len(models)}


@router.get("/{model_id}")
async def get_model(model_id: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM registered_models WHERE model_id = ?", (model_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found")
    return dict(row)


@router.post("/register")
async def register_model(req: RegisterModelRequest):
    """Register a new AI model with the monitoring platform."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO registered_models (model_id, name, version, description, endpoint, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (req.model_id, req.name, req.version, req.description,
              req.endpoint, datetime.now(timezone.utc).isoformat()))
        conn.commit()
        platform_logger.log_model_event(req.model_id, "model_registered",
                                        {"version": req.version})
        return {"status": "registered", "model_id": req.model_id}
    except Exception as e:
        raise HTTPException(status_code=409, detail=f"Model already exists: {e}")
    finally:
        conn.close()


@router.patch("/{model_id}")
async def update_model(model_id: str, req: UpdateModelRequest):
    conn = get_connection()
    cursor = conn.cursor()
    updates = {k: v for k, v in req.dict().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    cursor.execute(
        f"UPDATE registered_models SET {set_clause}, updated_at = ? WHERE model_id = ?",
        [*updates.values(), datetime.now(timezone.utc).isoformat(), model_id]
    )
    conn.commit()
    conn.close()
    return {"status": "updated", "model_id": model_id}


@router.delete("/{model_id}")
async def deprecate_model(model_id: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE registered_models SET status = 'deprecated', updated_at = ? WHERE model_id = ?",
        (datetime.now(timezone.utc).isoformat(), model_id)
    )
    conn.commit()
    conn.close()
    platform_logger.log_model_event(model_id, "model_deprecated")
    return {"status": "deprecated", "model_id": model_id}


@router.get("/{model_id}/health")
async def get_model_health(model_id: str):
    """Full health report for a single model."""
    conn = get_connection()
    cursor = conn.cursor()

    # Recent performance
    cursor.execute("""
        SELECT
            COUNT(*) as total_requests,
            AVG(latency_ms) as avg_latency_ms,
            MAX(latency_ms) as max_latency_ms,
            SUM(CASE WHEN status='error' THEN 1.0 ELSE 0 END) / NULLIF(COUNT(*),0) * 100 as error_rate_pct,
            AVG(confidence) as avg_confidence
        FROM inference_logs
        WHERE model_id = ? AND timestamp > datetime('now', '-1 hour')
    """, (model_id,))
    stats = dict(cursor.fetchone())

    # Recent errors
    cursor.execute("""
        SELECT error_message, timestamp FROM inference_logs
        WHERE model_id = ? AND status = 'error'
        ORDER BY timestamp DESC LIMIT 5
    """, (model_id,))
    recent_errors = [dict(r) for r in cursor.fetchall()]
    conn.close()

    error_rate = stats.get("error_rate_pct") or 0
    avg_latency = stats.get("avg_latency_ms") or 0

    if error_rate > 20 or avg_latency > 1000:
        health_status = "critical"
    elif error_rate > 10 or avg_latency > 500:
        health_status = "degraded"
    elif stats["total_requests"] == 0:
        health_status = "no_traffic"
    else:
        health_status = "healthy"

    return {
        "model_id": model_id,
        "health_status": health_status,
        "stats_1h": stats,
        "recent_errors": recent_errors,
        "isolation_forest": anomaly_detector.run_isolation_forest_simulation(model_id),
    }


@router.get("/{model_id}/compare/{other_model_id}")
async def compare_models(model_id: str, other_model_id: str):
    """Compare two model versions side by side."""
    def get_stats(mid):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                AVG(latency_ms) as avg_latency,
                SUM(CASE WHEN status='error' THEN 1.0 ELSE 0 END) / NULLIF(COUNT(*), 0) * 100 as error_rate,
                AVG(confidence) as avg_confidence,
                COUNT(*) as total_requests
            FROM inference_logs
            WHERE model_id = ? AND timestamp > datetime('now', '-1 hour')
        """, (mid,))
        result = dict(cursor.fetchone())
        conn.close()
        return result

    return {
        "comparison": {
            model_id: get_stats(model_id),
            other_model_id: get_stats(other_model_id),
        }
    }
