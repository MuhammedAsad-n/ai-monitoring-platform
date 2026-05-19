"""
Test suite for AI Monitoring Platform.
Covers all 10 modules end-to-end.

Environment is configured in conftest.py (project root) — do NOT
set os.environ["DB_PATH"] here; conftest.py runs first and owns that.
"""

import os
import sys
import tempfile
import pytest

# Ensure project root is on the path when running from tests/ subdirectory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── Expected test DB path (must match conftest.py) ───────────────────────────
TEST_DB_PATH = os.path.join(tempfile.gettempdir(), "test_monitoring.db")


# ─────────────────────────────────────────────
#  MODULE 2 — METRICS COLLECTOR TESTS
# ─────────────────────────────────────────────

class TestMetricsCollector:
    def test_cpu_metrics(self):
        from monitoring.collector import collector
        result = collector.get_cpu_metrics()
        assert "cpu_percent" in result
        assert 0 <= result["cpu_percent"] <= 100

    def test_ram_metrics(self):
        from monitoring.collector import collector
        result = collector.get_ram_metrics()
        assert "ram_percent" in result
        assert result["ram_total_gb"] > 0

    def test_disk_metrics(self):
        from monitoring.collector import collector
        result = collector.get_disk_metrics()
        assert "disk_percent" in result
        assert 0 <= result["disk_percent"] <= 100

    def test_collect_all(self):
        from monitoring.collector import collector
        result = collector.collect_all()
        assert "timestamp" in result
        assert "cpu_percent" in result
        assert "ram_percent" in result

    def test_record_inference(self):
        from monitoring.collector import collector
        before = collector._request_count
        collector.record_inference(45.2, True)
        assert collector._request_count == before + 1

    def test_error_tracking(self):
        from monitoring.collector import collector
        before = collector._error_count
        collector.record_inference(100.0, False)
        assert collector._error_count == before + 1

    def test_application_metrics(self):
        from monitoring.collector import collector
        result = collector.get_application_metrics()
        assert "total_requests" in result
        assert "error_rate_percent" in result
        assert "avg_latency_ms" in result


# ─────────────────────────────────────────────
#  MODULE 3 — LATENCY MONITOR TESTS
# ─────────────────────────────────────────────

class TestLatencyMonitor:
    def test_latency_stats_empty(self):
        from monitoring.latency_and_drift import latency_monitor
        result = latency_monitor.get_latency_stats(model_id="nonexistent_model_xyz")
        # Either returns an error key (no data) or a valid stats dict
        assert "error" in result or "sample_count" in result

    def test_health_assessment_excellent(self):
        from monitoring.latency_and_drift import LatencyMonitor
        m = LatencyMonitor()
        assert m._assess_latency_health([20.0, 25.0, 30.0, 22.0, 28.0]) == "excellent"

    def test_health_assessment_critical(self):
        from monitoring.latency_and_drift import LatencyMonitor
        m = LatencyMonitor()
        assert m._assess_latency_health([600.0, 700.0, 800.0, 900.0, 1000.0]) == "critical"

    def test_health_assessment_empty(self):
        from monitoring.latency_and_drift import LatencyMonitor
        m = LatencyMonitor()
        assert m._assess_latency_health([]) == "unknown"


# ─────────────────────────────────────────────
#  MODULE 4 — DRIFT DETECTOR TESTS
# ─────────────────────────────────────────────

class TestDriftDetector:
    def test_confidence_drift_returns_report(self):
        from monitoring.latency_and_drift import drift_detector
        result = drift_detector.detect_confidence_drift("fraud_detector_v1")
        assert "drift_score" in result
        assert "is_drifted" in result
        assert "drift_type" in result

    def test_latency_drift_returns_report(self):
        from monitoring.latency_and_drift import drift_detector
        result = drift_detector.detect_latency_drift("fraud_detector_v1")
        assert "psi_score" in result or "drift_score" in result

    def test_drift_score_range(self):
        from monitoring.latency_and_drift import drift_detector
        result = drift_detector.detect_confidence_drift("fraud_detector_v1")
        assert result["drift_score"] >= 0

    def test_drift_history(self):
        from monitoring.latency_and_drift import drift_detector
        drift_detector.detect_confidence_drift("fraud_detector_v1")
        history = drift_detector.get_drift_history("fraud_detector_v1")
        assert isinstance(history, list)


# ─────────────────────────────────────────────
#  MODULE 5 — ANOMALY DETECTOR TESTS
# ─────────────────────────────────────────────

class TestAnomalyDetector:
    def test_latency_anomalies(self):
        from anomaly_detection.detector import anomaly_detector
        result = anomaly_detector.detect_latency_anomalies()
        assert "anomalies" in result or "status" in result

    def test_traffic_anomalies(self):
        from anomaly_detection.detector import anomaly_detector
        result = anomaly_detector.detect_traffic_anomalies()
        assert isinstance(result, dict)

    def test_anomaly_summary(self):
        from anomaly_detection.detector import anomaly_detector
        result = anomaly_detector.get_anomaly_summary()
        assert "total_last_24h" in result
        assert "by_type" in result
        assert "recent" in result

    def test_isolation_forest_simulation(self):
        from anomaly_detection.detector import anomaly_detector
        result = anomaly_detector.run_isolation_forest_simulation("fraud_detector_v1")
        assert isinstance(result, dict)
        assert "status" in result or "algorithm" in result


# ─────────────────────────────────────────────
#  MODULE 6 — LOGGING TESTS
# ─────────────────────────────────────────────

class TestStructuredLogger:
    def test_logger_init(self):
        from logging_system.logger import StructuredLogger
        log = StructuredLogger("test")
        assert log is not None

    def test_log_inference(self):
        from logging_system.logger import StructuredLogger
        log = StructuredLogger("test_inference")
        log.log_inference("fraud_detector_v1", 45.2, "success", 0.92)

    def test_log_drift(self):
        from logging_system.logger import StructuredLogger
        log = StructuredLogger("test_drift")
        log.log_drift("fraud_detector_v1", "confidence_drift", 0.15, True)

    def test_log_anomaly(self):
        from logging_system.logger import StructuredLogger
        log = StructuredLogger("test_anomaly")
        log.log_anomaly("high_latency", 2.3, "Latency spike detected")


# ─────────────────────────────────────────────
#  MODULE 7 — ALERT MANAGER TESTS
# ─────────────────────────────────────────────

class TestAlertManager:
    def test_fire_alert(self):
        from logging_system.logger import AlertManager
        mgr = AlertManager()
        alert = mgr.fire_alert("test_alert", "warning", "Test alert message")
        assert "id" in alert
        assert alert["alert_type"] == "test_alert"

    def test_get_active_alerts(self):
        from logging_system.logger import AlertManager
        mgr = AlertManager()
        alerts = mgr.get_active_alerts()
        assert isinstance(alerts, list)

    def test_get_alert_stats(self):
        from logging_system.logger import AlertManager
        mgr = AlertManager()
        stats = mgr.get_alert_stats()
        assert isinstance(stats, dict)

    def test_resolve_alert(self):
        from logging_system.logger import AlertManager
        mgr = AlertManager()
        alert = mgr.fire_alert("resolve_test", "low", "Resolve me")
        resolved = mgr.resolve_alert(alert["id"])
        assert resolved is True

    def test_resolve_nonexistent_alert(self):
        from logging_system.logger import AlertManager
        mgr = AlertManager()
        resolved = mgr.resolve_alert(999999)
        assert resolved is False


# ─────────────────────────────────────────────
#  DATABASE TESTS
# ─────────────────────────────────────────────

class TestDatabase:
    def test_db_has_models(self):
        from database.connection import get_connection
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as c FROM registered_models")
        count = cursor.fetchone()["c"]
        conn.close()
        assert count >= 5  # seeded demo models

    def test_inference_log_insert(self):
        from database.connection import get_connection
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO inference_logs
            (model_id, latency_ms, status, timestamp)
            VALUES (?, ?, ?, ?)
        """, ("test_model", 42.5, "success", "2026-01-01T00:00:00"))
        conn.commit()
        log_id = cursor.lastrowid
        conn.close()
        assert log_id > 0

    def test_alert_insert_and_fetch(self):
        from database.connection import get_connection
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO alerts (alert_type, severity, message, timestamp)
            VALUES (?, ?, ?, ?)
        """, ("db_test", "low", "DB test alert", "2026-01-01T00:00:00"))
        conn.commit()
        cursor.execute("SELECT * FROM alerts WHERE alert_type = 'db_test'")
        row = cursor.fetchone()
        conn.close()
        assert row is not None
        assert row["message"] == "DB test alert"


# ─────────────────────────────────────────────
#  ADVANCED FEATURES TESTS
# ─────────────────────────────────────────────

class TestAdvancedFeatures:
    def test_failure_predictor_returns_report(self):
        from monitoring.advanced_features import failure_predictor
        result = failure_predictor.predict_failure("fraud_detector_v1")
        assert "model_id" in result
        assert "risk_level" in result or "status" in result

    def test_failure_predictor_risk_score_range(self):
        from monitoring.advanced_features import failure_predictor
        result = failure_predictor.predict_failure("fraud_detector_v2")
        score = result.get("risk_score")
        if score is not None:
            assert 0.0 <= score <= 1.0

    def test_predict_all_models(self):
        from monitoring.advanced_features import failure_predictor
        results = failure_predictor.predict_all_models()
        assert isinstance(results, list)
        assert len(results) >= 1

    def test_rollback_evaluate(self):
        from monitoring.advanced_features import auto_rollback
        result = auto_rollback.evaluate_model_for_rollback("fraud_detector_v1")
        assert "model_id" in result
        assert "decision" in result
        assert isinstance(result["rollback"], bool)

    def test_rollback_execute_no_prev_version(self):
        from monitoring.advanced_features import auto_rollback
        result = auto_rollback.execute_rollback("nlp_sentiment", target_version=None)
        assert "success" in result

    def test_slope_calculation(self):
        from monitoring.advanced_features import FailurePredictor
        fp = FailurePredictor()
        assert abs(fp._slope([5.0, 5.0, 5.0, 5.0])) < 0.01
        assert fp._slope([1.0, 2.0, 3.0, 4.0]) > 0
        assert fp._slope([4.0, 3.0, 2.0, 1.0]) < 0

    def test_config_loads(self):
        from config import settings
        assert settings.environment == "test"
        # Verify DB path matches what conftest.py set — cross-platform safe
        assert settings.database.path == TEST_DB_PATH
        assert settings.thresholds.latency_critical_ms > 0
        assert settings.thresholds.error_rate_critical_pct > 0

    def test_config_summary(self):
        from config import settings
        summary = settings.summary()
        assert "environment" in summary
        assert "db_path" in summary
        assert "simulate_traffic" in summary


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
