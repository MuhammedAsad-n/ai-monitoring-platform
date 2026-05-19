"""
Background task runner — collects metrics, checks anomalies, fires alerts.
Runs continuously alongside the FastAPI app.
"""

import asyncio
import logging
import random
import time
from datetime import datetime, timezone
from monitoring.collector import collector
from database.connection import get_connection

logger = logging.getLogger(__name__)


async def collect_metrics_loop():
    """Collect system metrics every 5 seconds."""
    while True:
        try:
            collector.collect_all()
        except Exception as e:
            logger.error(f"Metrics collection error: {e}")
        await asyncio.sleep(5)


async def simulate_inference_loop():
    """
    Simulate live inference traffic for demo purposes.
    In production, real model endpoints replace this.
    """
    model_ids = [
        "fraud_detector_v1",
        "fraud_detector_v2",
        "recommendation_model",
        "vision_model",
        "nlp_sentiment",
    ]

    while True:
        try:
            conn = get_connection()
            cursor = conn.cursor()

            # Simulate 1–5 inference requests per cycle
            for _ in range(random.randint(1, 5)):
                model_id = random.choice(model_ids)
                latency_ms = random.gauss(
                    50 if "v2" not in model_id else 35,
                    15
                )
                latency_ms = max(5, latency_ms)

                # Occasionally spike latency
                if random.random() < 0.03:
                    latency_ms *= random.uniform(5, 15)

                confidence = random.uniform(0.6, 0.99)
                success = random.random() > 0.04  # 4% error rate

                cursor.execute("""
                    INSERT INTO inference_logs
                    (model_id, request_id, confidence, latency_ms, status, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    model_id,
                    f"req_{int(time.time() * 1000)}_{random.randint(100,999)}",
                    confidence,
                    round(latency_ms, 2),
                    "success" if success else "error",
                    datetime.now(timezone.utc).isoformat(),
                ))
                collector.record_inference(latency_ms, success)

            conn.commit()
            conn.close()

        except Exception as e:
            logger.error(f"Inference simulation error: {e}")

        await asyncio.sleep(2)


async def anomaly_detection_loop():
    """Check for anomalies every 30 seconds."""
    while True:
        try:
            await _check_latency_anomalies()
            await _check_error_rate_anomalies()
        except Exception as e:
            logger.error(f"Anomaly detection error: {e}")
        await asyncio.sleep(30)


async def _check_latency_anomalies():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT model_id, AVG(latency_ms) as avg_lat, MAX(latency_ms) as max_lat
        FROM inference_logs
        WHERE timestamp > datetime('now', '-5 minutes')
        GROUP BY model_id
    """)
    rows = cursor.fetchall()

    for row in rows:
        if row["avg_lat"] and row["avg_lat"] > 500:
            cursor.execute("""
                INSERT INTO anomaly_detections
                (model_id, anomaly_type, score, description, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (
                row["model_id"],
                "high_latency",
                round(row["avg_lat"] / 500, 2),
                f"Avg latency {row['avg_lat']:.1f}ms exceeds threshold 500ms",
                datetime.now(timezone.utc).isoformat(),
            ))
            # Create alert
            cursor.execute("""
                INSERT INTO alerts
                (alert_type, severity, model_id, message, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (
                "latency_spike",
                "warning",
                row["model_id"],
                f"High latency detected for {row['model_id']}: avg {row['avg_lat']:.1f}ms",
                datetime.now(timezone.utc).isoformat(),
            ))

    conn.commit()
    conn.close()


async def _check_error_rate_anomalies():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT model_id,
               SUM(CASE WHEN status='error' THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as error_rate
        FROM inference_logs
        WHERE timestamp > datetime('now', '-5 minutes')
        GROUP BY model_id
        HAVING error_rate > 10
    """)
    rows = cursor.fetchall()

    for row in rows:
        cursor.execute("""
            INSERT INTO anomaly_detections
            (model_id, anomaly_type, score, description, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, (
            row["model_id"],
            "high_error_rate",
            round(row["error_rate"] / 100, 2),
            f"Error rate {row['error_rate']:.1f}% exceeds threshold 10%",
            datetime.now(timezone.utc).isoformat(),
        ))

    conn.commit()
    conn.close()


async def start_background_tasks():
    """Launch all background tasks."""
    asyncio.create_task(collect_metrics_loop())
    asyncio.create_task(simulate_inference_loop())
    asyncio.create_task(anomaly_detection_loop())
    logger.info("✅ Background tasks started.")
