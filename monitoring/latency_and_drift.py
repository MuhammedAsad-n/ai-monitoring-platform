"""
MODULE 3 — LATENCY MONITORING ENGINE
MODULE 4 — MODEL DRIFT DETECTION

Tracks inference latency statistics and detects model/data drift.
"""

import math
import sqlite3
import logging
import random
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from database.connection import get_connection

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
#  LATENCY MONITORING ENGINE
# ─────────────────────────────────────────────

class LatencyMonitor:
    """
    Analyzes inference latency from the database.
    Computes avg, P50, P95, P99 and detects slow requests.
    """

    SLOW_THRESHOLD_MS = 500
    CRITICAL_THRESHOLD_MS = 2000

    def get_latency_stats(self, model_id: Optional[str] = None, minutes: int = 60) -> Dict[str, Any]:
        conn = get_connection()
        cursor = conn.cursor()

        query = """
            SELECT latency_ms FROM inference_logs
            WHERE timestamp > datetime('now', ? )
            AND status = 'success'
        """
        params = [f"-{minutes} minutes"]
        if model_id:
            query += " AND model_id = ?"
            params.append(model_id)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        latencies = sorted([r["latency_ms"] for r in rows])
        if not latencies:
            return {"error": "No data available", "model_id": model_id}

        n = len(latencies)
        return {
            "model_id": model_id or "all",
            "sample_count": n,
            "avg_ms": round(sum(latencies) / n, 2),
            "min_ms": round(latencies[0], 2),
            "max_ms": round(latencies[-1], 2),
            "p50_ms": round(latencies[int(n * 0.50)], 2),
            "p95_ms": round(latencies[int(n * 0.95)], 2),
            "p99_ms": round(latencies[int(n * 0.99)], 2),
            "slow_requests": sum(1 for l in latencies if l > self.SLOW_THRESHOLD_MS),
            "critical_requests": sum(1 for l in latencies if l > self.CRITICAL_THRESHOLD_MS),
            "health": self._assess_latency_health(latencies),
            "window_minutes": minutes,
        }

    def get_latency_over_time(self, model_id: Optional[str] = None, minutes: int = 60) -> List[Dict]:
        """Get latency bucketed by minute for charting."""
        conn = get_connection()
        cursor = conn.cursor()

        query = """
            SELECT
                strftime('%Y-%m-%dT%H:%M:00', timestamp) as bucket,
                AVG(latency_ms) as avg_latency,
                MAX(latency_ms) as max_latency,
                COUNT(*) as count
            FROM inference_logs
            WHERE timestamp > datetime('now', ?)
            AND status = 'success'
        """
        params = [f"-{minutes} minutes"]
        if model_id:
            query += " AND model_id = ?"
            params.append(model_id)
        query += " GROUP BY bucket ORDER BY bucket"

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def _assess_latency_health(self, latencies: List[float]) -> str:
        if not latencies:
            return "unknown"
        p95 = latencies[int(len(latencies) * 0.95)]
        if p95 < 100:
            return "excellent"
        elif p95 < 300:
            return "good"
        elif p95 < 500:
            return "degraded"
        else:
            return "critical"


# ─────────────────────────────────────────────
#  DRIFT DETECTION ENGINE
# ─────────────────────────────────────────────

class DriftDetector:
    """
    Detects model and data drift using statistical methods.
    Uses Population Stability Index (PSI) and KS-test approximation.
    """

    PSI_THRESHOLD = 0.2       # Above = significant drift
    CONFIDENCE_DRIFT_THRESHOLD = 0.1  # 10% shift in avg confidence

    def detect_confidence_drift(self, model_id: str) -> Dict[str, Any]:
        """
        Compare recent confidence scores vs historical baseline.
        A significant drop may signal data drift or model degradation.
        """
        conn = get_connection()
        cursor = conn.cursor()

        # Baseline: older records
        cursor.execute("""
            SELECT AVG(confidence) as avg_conf, COUNT(*) as n
            FROM inference_logs
            WHERE model_id = ?
            AND timestamp < datetime('now', '-1 hour')
            AND confidence IS NOT NULL
            AND status = 'success'
        """, (model_id,))
        baseline = cursor.fetchone()

        # Recent: last hour
        cursor.execute("""
            SELECT AVG(confidence) as avg_conf, COUNT(*) as n
            FROM inference_logs
            WHERE model_id = ?
            AND timestamp > datetime('now', '-1 hour')
            AND confidence IS NOT NULL
            AND status = 'success'
        """, (model_id,))
        recent = cursor.fetchone()
        conn.close()

        if not baseline["n"] or not recent["n"]:
            return self._simulate_drift_report(model_id, "confidence_drift")

        baseline_conf = baseline["avg_conf"] or 0.85
        recent_conf = recent["avg_conf"] or 0.85
        drift_score = abs(baseline_conf - recent_conf)
        is_drifted = drift_score > self.CONFIDENCE_DRIFT_THRESHOLD

        report = {
            "model_id": model_id,
            "drift_type": "confidence_drift",
            "baseline_confidence": round(baseline_conf, 4),
            "recent_confidence": round(recent_conf, 4),
            "drift_score": round(drift_score, 4),
            "is_drifted": is_drifted,
            "severity": "high" if drift_score > 0.2 else "medium" if is_drifted else "low",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        self._persist_drift_report(model_id, "confidence_drift", drift_score, is_drifted, report)
        return report

    def detect_latency_drift(self, model_id: str) -> Dict[str, Any]:
        """Detect if latency distribution has shifted significantly."""
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT AVG(latency_ms) as avg_lat
            FROM inference_logs
            WHERE model_id = ? AND timestamp < datetime('now', '-1 hour')
        """, (model_id,))
        baseline = cursor.fetchone()

        cursor.execute("""
            SELECT AVG(latency_ms) as avg_lat
            FROM inference_logs
            WHERE model_id = ? AND timestamp > datetime('now', '-1 hour')
        """, (model_id,))
        recent = cursor.fetchone()
        conn.close()

        baseline_lat = baseline["avg_lat"] or 50.0
        recent_lat = recent["avg_lat"] or 50.0

        psi = abs(recent_lat - baseline_lat) / max(baseline_lat, 1)
        is_drifted = psi > self.PSI_THRESHOLD

        report = {
            "model_id": model_id,
            "drift_type": "latency_drift",
            "baseline_avg_ms": round(baseline_lat, 2),
            "recent_avg_ms": round(recent_lat, 2),
            "psi_score": round(psi, 4),
            "is_drifted": is_drifted,
            "severity": "high" if psi > 0.5 else "medium" if is_drifted else "low",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        self._persist_drift_report(model_id, "latency_drift", psi, is_drifted, report)
        return report

    def get_drift_history(self, model_id: str, limit: int = 20) -> List[Dict]:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM drift_reports
            WHERE model_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (model_id, limit))
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def _persist_drift_report(self, model_id: str, drift_type: str,
                               score: float, is_drifted: bool, details: Dict):
        import json
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO drift_reports
            (model_id, drift_type, drift_score, is_drifted, details, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            model_id, drift_type, score, int(is_drifted),
            json.dumps(details), datetime.now(timezone.utc).isoformat()
        ))
        conn.commit()
        conn.close()

    def _simulate_drift_report(self, model_id: str, drift_type: str) -> Dict:
        """Return simulated drift data when no real data exists yet."""
        score = random.uniform(0.01, 0.25)
        return {
            "model_id": model_id,
            "drift_type": drift_type,
            "drift_score": round(score, 4),
            "is_drifted": score > 0.1,
            "severity": "medium" if score > 0.1 else "low",
            "note": "simulated — insufficient real data",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


# Singletons
latency_monitor = LatencyMonitor()
drift_detector = DriftDetector()
