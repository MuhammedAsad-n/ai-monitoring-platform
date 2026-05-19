"""
Prometheus metrics exporter.
Exposes /metrics endpoint for Grafana scraping.

In production: point Prometheus at http://your-host:8000/metrics
Then visualize in Grafana with pre-built dashboards.

Install: pip install prometheus-client
"""

import time
import logging
from typing import Optional

logger = logging.getLogger(__name__)

try:
    from prometheus_client import (
        Counter, Histogram, Gauge, Summary,
        generate_latest, CONTENT_TYPE_LATEST, CollectorRegistry
    )
    PROMETHEUS_AVAILABLE = True
    logger.info("✅ Prometheus client available")
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logger.info("ℹ️  prometheus-client not installed — /metrics endpoint disabled. Run: pip install prometheus-client")


# ── Define metrics (only if prometheus_client is available) ──────────────────

if PROMETHEUS_AVAILABLE:
    registry = CollectorRegistry()

    # Inference counters
    INFERENCE_TOTAL = Counter(
        "ai_inference_total",
        "Total inference requests",
        ["model_id", "status"],
        registry=registry,
    )
    INFERENCE_LATENCY = Histogram(
        "ai_inference_latency_ms",
        "Inference latency in milliseconds",
        ["model_id"],
        buckets=[10, 25, 50, 100, 200, 500, 1000, 2000, 5000],
        registry=registry,
    )
    INFERENCE_CONFIDENCE = Summary(
        "ai_inference_confidence",
        "Model prediction confidence score",
        ["model_id"],
        registry=registry,
    )

    # System metrics
    CPU_USAGE = Gauge("system_cpu_percent", "CPU usage percent", registry=registry)
    RAM_USAGE = Gauge("system_ram_percent", "RAM usage percent", registry=registry)
    RAM_USED_GB = Gauge("system_ram_used_gb", "RAM used in GB", registry=registry)
    DISK_USAGE = Gauge("system_disk_percent", "Disk usage percent", registry=registry)
    GPU_USAGE = Gauge("system_gpu_percent", "GPU usage percent", registry=registry)
    GPU_MEM = Gauge("system_gpu_memory_percent", "GPU memory usage percent", registry=registry)

    # Drift metrics
    DRIFT_SCORE = Gauge(
        "ai_drift_score",
        "Model drift score (PSI)",
        ["model_id", "drift_type"],
        registry=registry,
    )
    DRIFT_DETECTED = Gauge(
        "ai_drift_detected",
        "1 if drift detected, 0 otherwise",
        ["model_id"],
        registry=registry,
    )

    # Alert metrics
    ALERTS_TOTAL = Counter(
        "ai_alerts_total",
        "Total alerts fired",
        ["alert_type", "severity"],
        registry=registry,
    )
    ALERTS_ACTIVE = Gauge(
        "ai_alerts_active",
        "Currently active (unresolved) alerts",
        registry=registry,
    )

    # Anomaly metrics
    ANOMALIES_TOTAL = Counter(
        "ai_anomalies_total",
        "Total anomalies detected",
        ["anomaly_type"],
        registry=registry,
    )

    # Error rate gauge
    ERROR_RATE = Gauge(
        "ai_error_rate_percent",
        "Current error rate percent",
        ["model_id"],
        registry=registry,
    )


class PrometheusExporter:
    """
    Records events into Prometheus metrics.
    Call these methods from your inference path and background tasks.
    """

    def record_inference(self, model_id: str, latency_ms: float,
                          status: str, confidence: Optional[float] = None):
        if not PROMETHEUS_AVAILABLE:
            return
        INFERENCE_TOTAL.labels(model_id=model_id, status=status).inc()
        INFERENCE_LATENCY.labels(model_id=model_id).observe(latency_ms)
        if confidence is not None:
            INFERENCE_CONFIDENCE.labels(model_id=model_id).observe(confidence)

    def update_system_metrics(self, metrics: dict):
        if not PROMETHEUS_AVAILABLE:
            return
        CPU_USAGE.set(metrics.get("cpu_percent") or 0)
        RAM_USAGE.set(metrics.get("ram_percent") or 0)
        RAM_USED_GB.set(metrics.get("ram_used_gb") or 0)
        DISK_USAGE.set(metrics.get("disk_percent") or 0)
        if metrics.get("gpu_available"):
            GPU_USAGE.set(metrics.get("gpu_percent") or 0)
            GPU_MEM.set(metrics.get("gpu_memory_percent") or 0)

    def record_drift(self, model_id: str, drift_type: str,
                      score: float, is_drifted: bool):
        if not PROMETHEUS_AVAILABLE:
            return
        DRIFT_SCORE.labels(model_id=model_id, drift_type=drift_type).set(score)
        DRIFT_DETECTED.labels(model_id=model_id).set(1 if is_drifted else 0)

    def record_alert(self, alert_type: str, severity: str):
        if not PROMETHEUS_AVAILABLE:
            return
        ALERTS_TOTAL.labels(alert_type=alert_type, severity=severity).inc()

    def set_active_alerts(self, count: int):
        if not PROMETHEUS_AVAILABLE:
            return
        ALERTS_ACTIVE.set(count)

    def record_anomaly(self, anomaly_type: str):
        if not PROMETHEUS_AVAILABLE:
            return
        ANOMALIES_TOTAL.labels(anomaly_type=anomaly_type).inc()

    def set_error_rate(self, model_id: str, rate: float):
        if not PROMETHEUS_AVAILABLE:
            return
        ERROR_RATE.labels(model_id=model_id).set(rate)

    def get_metrics_output(self) -> tuple:
        """Returns (content, content_type) for the /metrics endpoint."""
        if not PROMETHEUS_AVAILABLE:
            return (
                b"# prometheus-client not installed\n# Run: pip install prometheus-client\n",
                "text/plain"
            )
        return generate_latest(registry), CONTENT_TYPE_LATEST


# Global singleton
prometheus_exporter = PrometheusExporter()
