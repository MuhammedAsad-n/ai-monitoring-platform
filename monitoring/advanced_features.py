"""
ADVANCED FEATURES
=================
1. Auto Model Rollback   — automatically revert a failing model to its last stable version
2. AI Failure Prediction — predict model degradation before it causes outages

These are production-grade patterns used at companies like Uber, Airbnb, and Netflix
for managing ML model reliability at scale.
"""

import logging
import math
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from database.connection import get_connection
from config import settings

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
#  1. AUTO MODEL ROLLBACK
# ─────────────────────────────────────────────────────────────────────────────

class AutoRollbackManager:
    """
    Monitors model health and automatically triggers rollback when a model
    exceeds configured degradation thresholds.

    Rollback workflow:
    1. Detect sustained degradation (error rate or latency threshold breach)
    2. Find the last stable version of the model
    3. Switch traffic to the stable version
    4. Fire a critical alert with rollback details
    5. Log the rollback event for audit trail

    In production: integrate with your deployment system (K8s, SageMaker,
    Vertex AI) to actually swap the serving endpoint.
    """

    def __init__(self):
        self.rollback_cooldown_minutes = 30  # prevent rollback storms
        self._last_rollback: Dict[str, datetime] = {}

    def evaluate_model_for_rollback(self, model_id: str) -> Dict[str, Any]:
        """
        Evaluate whether a model should be rolled back based on recent metrics.
        Returns a rollback decision with reasoning.
        """
        conn = get_connection()
        cursor = conn.cursor()

        # Get recent performance (last 10 minutes)
        cursor.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN status='error' THEN 1.0 ELSE 0 END) / NULLIF(COUNT(*), 0) * 100 as error_rate,
                AVG(latency_ms) as avg_latency,
                AVG(confidence) as avg_confidence
            FROM inference_logs
            WHERE model_id = ?
            AND timestamp > datetime('now', '-10 minutes')
        """, (model_id,))
        recent = dict(cursor.fetchone())
        conn.close()

        if not recent["total"] or recent["total"] < 10:
            return {"model_id": model_id, "decision": "insufficient_data", "rollback": False}

        error_rate = recent["error_rate"] or 0
        avg_latency = recent["avg_latency"] or 0

        # Check thresholds
        triggers = []
        if error_rate > settings.thresholds.error_rate_critical_pct:
            triggers.append(f"error_rate={error_rate:.1f}% > {settings.thresholds.error_rate_critical_pct}%")
        if avg_latency > settings.thresholds.latency_critical_ms:
            triggers.append(f"avg_latency={avg_latency:.0f}ms > {settings.thresholds.latency_critical_ms}ms")
        if recent["avg_confidence"] and recent["avg_confidence"] < 0.5:
            triggers.append(f"confidence={recent['avg_confidence']:.2f} < 0.5")

        should_rollback = len(triggers) >= 1

        # Respect cooldown
        if should_rollback and model_id in self._last_rollback:
            elapsed = (datetime.now(timezone.utc) - self._last_rollback[model_id]).total_seconds() / 60
            if elapsed < self.rollback_cooldown_minutes:
                return {
                    "model_id": model_id,
                    "decision": "cooldown",
                    "rollback": False,
                    "cooldown_remaining_minutes": round(self.rollback_cooldown_minutes - elapsed, 1),
                }

        return {
            "model_id": model_id,
            "decision": "rollback" if should_rollback else "stable",
            "rollback": should_rollback,
            "triggers": triggers,
            "recent_metrics": recent,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def execute_rollback(self, model_id: str, target_version: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute rollback for a model.
        In production: calls your deployment API (K8s rollout undo, SageMaker update-endpoint, etc.)
        """
        conn = get_connection()
        cursor = conn.cursor()

        # Find the previous stable version
        cursor.execute("""
            SELECT version FROM registered_models
            WHERE name = (SELECT name FROM registered_models WHERE model_id = ?)
            AND model_id != ?
            AND status = 'active'
            ORDER BY created_at DESC
            LIMIT 1
        """, (model_id, model_id))
        prev = cursor.fetchone()
        rollback_target = target_version or (prev["version"] if prev else None)

        if not rollback_target:
            conn.close()
            return {"success": False, "reason": "No stable previous version found", "model_id": model_id}

        # Mark current as degraded
        cursor.execute("""
            UPDATE registered_models
            SET status = 'degraded', updated_at = ?
            WHERE model_id = ?
        """, (datetime.now(timezone.utc).isoformat(), model_id))

        # Log rollback event
        cursor.execute("""
            INSERT INTO alerts (alert_type, severity, model_id, message, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, (
            "auto_rollback",
            "critical",
            model_id,
            f"Auto-rollback triggered for {model_id} → reverted to {rollback_target}",
            datetime.now(timezone.utc).isoformat(),
        ))
        conn.commit()
        conn.close()

        self._last_rollback[model_id] = datetime.now(timezone.utc)

        result = {
            "success": True,
            "model_id": model_id,
            "rolled_back_to": rollback_target,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "note": "In production: integrate with your deployment API to swap serving endpoint.",
        }
        logger.warning(f"🔄 AUTO ROLLBACK: {model_id} → {rollback_target}")
        return result

    def check_all_models(self) -> List[Dict[str, Any]]:
        """Run rollback evaluation across all active models."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT model_id FROM registered_models WHERE status = 'active'")
        models = [r["model_id"] for r in cursor.fetchall()]
        conn.close()

        results = []
        for model_id in models:
            eval_result = self.evaluate_model_for_rollback(model_id)
            if eval_result.get("rollback"):
                rollback_result = self.execute_rollback(model_id)
                eval_result["rollback_result"] = rollback_result
            results.append(eval_result)
        return results


# ─────────────────────────────────────────────────────────────────────────────
#  2. AI FAILURE PREDICTION
# ─────────────────────────────────────────────────────────────────────────────

class FailurePredictor:
    """
    Predicts model failures BEFORE they happen using trend analysis.

    Technique: Linear regression on recent error rate and latency trends.
    If the slope is positive and the projected value will breach the threshold
    within N minutes, a predictive alert is fired.

    In production: replace with a trained time-series forecasting model
    (ARIMA, Prophet, LSTM) trained on your historical incident data.
    """

    def __init__(self):
        self.prediction_horizon_minutes = 15  # predict N minutes ahead

    def predict_failure(self, model_id: str) -> Dict[str, Any]:
        """Predict whether a model will fail in the next 15 minutes."""
        conn = get_connection()
        cursor = conn.cursor()

        # Get per-minute error rates and latencies for the last 30 minutes
        cursor.execute("""
            SELECT
                strftime('%Y-%m-%dT%H:%M:00', timestamp) as minute,
                SUM(CASE WHEN status='error' THEN 1.0 ELSE 0 END) / NULLIF(COUNT(*), 0) * 100 as error_rate,
                AVG(latency_ms) as avg_latency
            FROM inference_logs
            WHERE model_id = ?
            AND timestamp > datetime('now', '-30 minutes')
            GROUP BY minute
            ORDER BY minute
        """, (model_id,))
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()

        if len(rows) < 5:
            return {"model_id": model_id, "status": "insufficient_data"}

        error_rates = [r["error_rate"] or 0 for r in rows]
        latencies = [r["avg_latency"] or 0 for r in rows]

        # Linear regression slope
        err_slope = self._slope(error_rates)
        lat_slope = self._slope(latencies)

        # Project forward
        projected_error = error_rates[-1] + err_slope * self.prediction_horizon_minutes
        projected_latency = latencies[-1] + lat_slope * self.prediction_horizon_minutes

        predictions = []
        risk_score = 0.0

        if err_slope > 0.2 and projected_error > settings.thresholds.error_rate_warning_pct:
            predictions.append({
                "metric": "error_rate",
                "current": round(error_rates[-1], 2),
                "projected": round(projected_error, 2),
                "threshold": settings.thresholds.error_rate_warning_pct,
                "will_breach": projected_error > settings.thresholds.error_rate_warning_pct,
            })
            risk_score += min(1.0, projected_error / settings.thresholds.error_rate_critical_pct)

        if lat_slope > 5 and projected_latency > settings.thresholds.latency_warning_ms:
            predictions.append({
                "metric": "latency_ms",
                "current": round(latencies[-1], 1),
                "projected": round(projected_latency, 1),
                "threshold": settings.thresholds.latency_warning_ms,
                "will_breach": projected_latency > settings.thresholds.latency_warning_ms,
            })
            risk_score += min(1.0, projected_latency / settings.thresholds.latency_critical_ms)

        risk_score = round(min(1.0, risk_score / max(len(predictions), 1)), 3)
        risk_level = "high" if risk_score > 0.7 else "medium" if risk_score > 0.3 else "low"

        return {
            "model_id": model_id,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "prediction_horizon_minutes": self.prediction_horizon_minutes,
            "error_rate_slope": round(err_slope, 4),
            "latency_slope": round(lat_slope, 4),
            "predictions": predictions,
            "recommendation": self._recommendation(risk_level, predictions),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def predict_all_models(self) -> List[Dict[str, Any]]:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT model_id FROM registered_models WHERE status = 'active'")
        models = [r["model_id"] for r in cursor.fetchall()]
        conn.close()
        return [self.predict_failure(mid) for mid in models]

    def _slope(self, values: List[float]) -> float:
        """Simple linear regression slope (change per step)."""
        n = len(values)
        if n < 2:
            return 0.0
        xs = list(range(n))
        x_mean = sum(xs) / n
        y_mean = sum(values) / n
        numerator = sum((xs[i] - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((x - x_mean) ** 2 for x in xs)
        return numerator / denominator if denominator != 0 else 0.0

    def _recommendation(self, risk_level: str, predictions: List[Dict]) -> str:
        if risk_level == "low":
            return "No action needed — model trending normally."
        metrics = [p["metric"] for p in predictions]
        if risk_level == "high":
            return (
                f"⚠️ High failure risk detected. Metrics trending toward threshold: "
                f"{', '.join(metrics)}. Consider scaling resources or preparing rollback."
            )
        return (
            f"Monitor closely — {', '.join(metrics)} trending upward. "
            f"Consider pre-emptive investigation."
        )


# Singletons
auto_rollback = AutoRollbackManager()
failure_predictor = FailurePredictor()
