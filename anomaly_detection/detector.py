"""
MODULE 5 — ANOMALY DETECTION SYSTEM
Uses statistical z-score analysis and Isolation Forest principles
to detect traffic spikes, latency anomalies, and unusual predictions.
"""

import math
import logging
import random
from datetime import datetime
from typing import Dict, Any, List
from database.connection import get_connection

logger = logging.getLogger(__name__)


class AnomalyDetector:
    """
    Statistical anomaly detection for AI system monitoring.
    Detects: latency spikes, error rate surges, traffic anomalies.
    """

    ZSCORE_THRESHOLD = 2.5

    def detect_latency_anomalies(self, model_id: str = None) -> Dict[str, Any]:
        """Z-score based latency anomaly detection."""
        conn = get_connection()
        cursor = conn.cursor()

        query = """
            SELECT latency_ms, timestamp FROM inference_logs
            WHERE timestamp > datetime('now', '-30 minutes')
        """
        params = []
        if model_id:
            query += " AND model_id = ?"
            params.append(model_id)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        latencies = [r["latency_ms"] for r in rows]
        if len(latencies) < 5:
            return {"status": "insufficient_data", "anomalies": []}

        mean = sum(latencies) / len(latencies)
        variance = sum((x - mean) ** 2 for x in latencies) / len(latencies)
        std = math.sqrt(variance) if variance > 0 else 1

        anomalies = []
        for i, (row, lat) in enumerate(zip(rows, latencies)):
            z_score = (lat - mean) / std
            if abs(z_score) > self.ZSCORE_THRESHOLD:
                anomalies.append({
                    "timestamp": row["timestamp"],
                    "latency_ms": round(lat, 2),
                    "z_score": round(z_score, 2),
                    "severity": "critical" if z_score > 4 else "warning",
                })

        return {
            "model_id": model_id or "all",
            "window": "30 minutes",
            "samples_analyzed": len(latencies),
            "mean_ms": round(mean, 2),
            "std_ms": round(std, 2),
            "anomaly_count": len(anomalies),
            "anomalies": anomalies[-10:],  # last 10
            "anomaly_rate_percent": round(len(anomalies) / len(latencies) * 100, 2),
        }

    def detect_traffic_anomalies(self) -> Dict[str, Any]:
        """Detect unusual spikes or drops in request traffic."""
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                strftime('%Y-%m-%dT%H:%M:00', timestamp) as minute,
                COUNT(*) as count
            FROM inference_logs
            WHERE timestamp > datetime('now', '-60 minutes')
            GROUP BY minute
            ORDER BY minute
        """)
        rows = cursor.fetchall()
        conn.close()

        if len(rows) < 5:
            return {"status": "insufficient_data"}

        counts = [r["count"] for r in rows]
        mean = sum(counts) / len(counts)
        variance = sum((x - mean) ** 2 for x in counts) / len(counts)
        std = math.sqrt(variance) if variance > 0 else 1

        spikes = []
        drops = []
        for row, count in zip(rows, counts):
            z = (count - mean) / std
            if z > self.ZSCORE_THRESHOLD:
                spikes.append({"minute": row["minute"], "count": count, "z_score": round(z, 2)})
            elif z < -self.ZSCORE_THRESHOLD:
                drops.append({"minute": row["minute"], "count": count, "z_score": round(z, 2)})

        return {
            "window": "60 minutes",
            "avg_rpm": round(mean, 2),
            "traffic_spikes": spikes,
            "traffic_drops": drops,
            "anomaly_count": len(spikes) + len(drops),
        }

    def get_anomaly_summary(self) -> Dict[str, Any]:
        """Get recent anomaly summary from the database."""
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT anomaly_type, COUNT(*) as count, MAX(timestamp) as last_seen
            FROM anomaly_detections
            WHERE timestamp > datetime('now', '-24 hours')
            GROUP BY anomaly_type
        """)
        rows = cursor.fetchall()

        cursor.execute("""
            SELECT COUNT(*) as total FROM anomaly_detections
            WHERE timestamp > datetime('now', '-24 hours')
        """)
        total = cursor.fetchone()["total"]

        cursor.execute("""
            SELECT * FROM anomaly_detections
            ORDER BY timestamp DESC LIMIT 20
        """)
        recent = cursor.fetchall()
        conn.close()

        return {
            "total_last_24h": total,
            "by_type": [dict(r) for r in rows],
            "recent": [dict(r) for r in recent],
        }

    def run_isolation_forest_simulation(self, model_id: str) -> Dict[str, Any]:
        """
        Simulate Isolation Forest scoring on recent inference data.
        In production: use sklearn.ensemble.IsolationForest on real feature vectors.
        """
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT latency_ms, confidence FROM inference_logs
            WHERE model_id = ?
            AND timestamp > datetime('now', '-1 hour')
            AND confidence IS NOT NULL
            LIMIT 200
        """, (model_id,))
        rows = cursor.fetchall()
        conn.close()

        if len(rows) < 10:
            return {"status": "insufficient_data", "model_id": model_id}

        # Simulate anomaly scores (real impl would use IsolationForest.fit_predict)
        scores = []
        for row in rows:
            lat = row["latency_ms"]
            conf = row["confidence"]
            # Higher score = more anomalous (simplified simulation)
            score = (lat / 1000) * (1 - conf)
            scores.append(score)

        threshold = sorted(scores)[int(len(scores) * 0.95)]
        anomalous = sum(1 for s in scores if s > threshold)

        return {
            "model_id": model_id,
            "algorithm": "Isolation Forest (simulated)",
            "samples_analyzed": len(scores),
            "anomaly_threshold": round(threshold, 4),
            "anomalous_samples": anomalous,
            "anomaly_rate_percent": round(anomalous / len(scores) * 100, 2),
            "status": "alert" if anomalous > len(scores) * 0.1 else "normal",
        }


# Singleton
anomaly_detector = AnomalyDetector()
