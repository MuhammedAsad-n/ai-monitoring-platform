"""
MODULE 6 — CENTRALIZED LOGGING SYSTEM
MODULE 7 — ALERTING SYSTEM

Structured JSON logging and multi-channel alert dispatch.
"""

import logging
import json
import sqlite3
import smtplib
import os
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from database.connection import get_connection

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
#  CENTRALIZED LOGGING
# ─────────────────────────────────────────────

class StructuredLogger:
    """
    Emits structured JSON logs for inference, errors, and audit events.
    In production: ship to ELK Stack / Datadog / CloudWatch.
    """

    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        handler = logging.StreamHandler()
        handler.setFormatter(JSONFormatter())
        if not self.logger.handlers:
            self.logger.addHandler(handler)

    def log_inference(self, model_id: str, latency_ms: float,
                      status: str, confidence: float = None, error: str = None):
        self.logger.info("inference", extra={
            "event": "inference",
            "model_id": model_id,
            "latency_ms": round(latency_ms, 2),
            "status": status,
            "confidence": confidence,
            "error": error,
        })

    def log_drift(self, model_id: str, drift_type: str,
                  score: float, is_drifted: bool):
        level = logging.WARNING if is_drifted else logging.INFO
        self.logger.log(level, "drift_check", extra={
            "event": "drift_detection",
            "model_id": model_id,
            "drift_type": drift_type,
            "drift_score": score,
            "is_drifted": is_drifted,
        })

    def log_anomaly(self, anomaly_type: str, score: float,
                    description: str, model_id: str = None):
        self.logger.warning("anomaly", extra={
            "event": "anomaly_detected",
            "anomaly_type": anomaly_type,
            "score": score,
            "model_id": model_id,
            "description": description,
        })

    def log_alert(self, alert_type: str, severity: str, message: str):
        level = logging.CRITICAL if severity == "critical" else logging.WARNING
        self.logger.log(level, "alert", extra={
            "event": "alert_fired",
            "alert_type": alert_type,
            "severity": severity,
            "alert_message": message,
        })

    def log_model_event(self, model_id: str, event: str, details: Dict = None):
        self.logger.info("model_event", extra={
            "event": event,
            "model_id": model_id,
            "details": details or {},
        })


class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Add structured fields if present
        for key in ["event", "model_id", "latency_ms", "status", "confidence",
                    "drift_type", "drift_score", "is_drifted", "anomaly_type",
                    "score", "description", "alert_type", "severity", "details",
                    "error", "alert_message"]:
            if hasattr(record, key):
                log_data[key] = getattr(record, key)
        return json.dumps(log_data)


# ─────────────────────────────────────────────
#  ALERTING SYSTEM
# ─────────────────────────────────────────────

ALERT_THRESHOLDS = {
    "latency_p95_ms": 500,
    "error_rate_percent": 10.0,
    "cpu_percent": 85.0,
    "ram_percent": 90.0,
    "drift_score": 0.2,
}


class AlertManager:
    """
    Routes alerts to configured channels.
    Supports: database persistence, email (SMTP), Slack webhooks.
    """

    def __init__(self):
        self.structured_log = StructuredLogger("alerts")
        self.slack_webhook = os.environ.get("SLACK_WEBHOOK_URL")
        self.email_config = {
            "host": os.environ.get("SMTP_HOST", "smtp.gmail.com"),
            "port": int(os.environ.get("SMTP_PORT", 587)),
            "user": os.environ.get("SMTP_USER"),
            "password": os.environ.get("SMTP_PASS"),
            "recipient": os.environ.get("ALERT_EMAIL"),
        }

    def fire_alert(self, alert_type: str, severity: str, message: str,
                   model_id: str = None, details: Dict = None) -> Dict[str, Any]:
        """Create and dispatch an alert."""
        alert = {
            "alert_type": alert_type,
            "severity": severity,
            "model_id": model_id,
            "message": message,
            "details": json.dumps(details or {}),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Persist to DB
        alert_id = self._persist_alert(alert)
        alert["id"] = alert_id

        # Log it
        self.structured_log.log_alert(alert_type, severity, message)

        # Dispatch channels
        if severity in ("critical", "high"):
            self._send_slack(alert)
            self._send_email(alert)

        return alert

    def get_active_alerts(self, limit: int = 50) -> List[Dict]:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM alerts
            WHERE resolved = 0
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_alert_history(self, limit: int = 100) -> List[Dict]:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM alerts ORDER BY timestamp DESC LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def resolve_alert(self, alert_id: int) -> bool:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE alerts SET resolved = 1, resolved_at = ?
            WHERE id = ?
        """, (datetime.now(timezone.utc).isoformat(), alert_id))
        conn.commit()
        affected = cursor.rowcount
        conn.close()
        return affected > 0

    def get_alert_stats(self) -> Dict[str, Any]:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN resolved = 0 THEN 1 ELSE 0 END) as active,
                SUM(CASE WHEN severity = 'critical' AND resolved = 0 THEN 1 ELSE 0 END) as critical,
                SUM(CASE WHEN severity = 'warning' AND resolved = 0 THEN 1 ELSE 0 END) as warnings
            FROM alerts
            WHERE timestamp > datetime('now', '-24 hours')
        """)
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else {}

    def _persist_alert(self, alert: Dict) -> int:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO alerts (alert_type, severity, model_id, message, details, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            alert["alert_type"], alert["severity"], alert.get("model_id"),
            alert["message"], alert.get("details"), alert["timestamp"]
        ))
        conn.commit()
        alert_id = cursor.lastrowid
        conn.close()
        return alert_id

    def _send_slack(self, alert: Dict):
        """Send Slack webhook alert."""
        if not self.slack_webhook:
            return
        try:
            import urllib.request
            payload = json.dumps({
                "text": f"🚨 *{alert['severity'].upper()}* — {alert['message']}\n"
                        f"Type: `{alert['alert_type']}` | Model: `{alert.get('model_id', 'N/A')}`"
            }).encode()
            req = urllib.request.Request(
                self.slack_webhook,
                data=payload,
                headers={"Content-Type": "application/json"}
            )
            urllib.request.urlopen(req, timeout=5)
            logger.info(f"Slack alert sent: {alert['alert_type']}")
        except Exception as e:
            logger.error(f"Slack alert failed: {e}")

    def _send_email(self, alert: Dict):
        """Send email alert via SMTP."""
        cfg = self.email_config
        if not all([cfg["user"], cfg["password"], cfg["recipient"]]):
            return
        try:
            with smtplib.SMTP(cfg["host"], cfg["port"]) as smtp:
                smtp.starttls()
                smtp.login(cfg["user"], cfg["password"])
                subject = f"[AI Monitor] {alert['severity'].upper()}: {alert['alert_type']}"
                body = f"Subject: {subject}\n\n{alert['message']}\n\nTimestamp: {alert['timestamp']}"
                smtp.sendmail(cfg["user"], cfg["recipient"], body)
            logger.info(f"Email alert sent: {subject}")
        except Exception as e:
            logger.error(f"Email alert failed: {e}")


# Singletons
platform_logger = StructuredLogger("platform")
alert_manager = AlertManager()
