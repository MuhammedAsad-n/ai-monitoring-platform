"""
Configuration system for AI Monitoring Platform.
All settings are read from environment variables with sensible defaults.
Use a .env file for local development (see .env.example).
"""

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class DatabaseConfig:
    path: str = field(default_factory=lambda: os.environ.get("DB_PATH", "monitoring.db"))
    pool_size: int = field(default_factory=lambda: int(os.environ.get("DB_POOL_SIZE", "5")))


@dataclass
class ServerConfig:
    host: str = field(default_factory=lambda: os.environ.get("HOST", "0.0.0.0"))
    port: int = field(default_factory=lambda: int(os.environ.get("PORT", "8000")))
    reload: bool = field(default_factory=lambda: os.environ.get("RELOAD", "false").lower() == "true")
    log_level: str = field(default_factory=lambda: os.environ.get("LOG_LEVEL", "info"))
    workers: int = field(default_factory=lambda: int(os.environ.get("WORKERS", "1")))


@dataclass
class AlertConfig:
    # Slack
    slack_webhook_url: Optional[str] = field(
        default_factory=lambda: os.environ.get("SLACK_WEBHOOK_URL")
    )
    # Email (SMTP)
    smtp_host: str = field(default_factory=lambda: os.environ.get("SMTP_HOST", "smtp.gmail.com"))
    smtp_port: int = field(default_factory=lambda: int(os.environ.get("SMTP_PORT", "587")))
    smtp_user: Optional[str] = field(default_factory=lambda: os.environ.get("SMTP_USER"))
    smtp_pass: Optional[str] = field(default_factory=lambda: os.environ.get("SMTP_PASS"))
    alert_email: Optional[str] = field(default_factory=lambda: os.environ.get("ALERT_EMAIL"))
    # Telegram
    telegram_bot_token: Optional[str] = field(
        default_factory=lambda: os.environ.get("TELEGRAM_BOT_TOKEN")
    )
    telegram_chat_id: Optional[str] = field(
        default_factory=lambda: os.environ.get("TELEGRAM_CHAT_ID")
    )


@dataclass
class MonitoringConfig:
    # Background collection interval in seconds
    metrics_interval_seconds: int = field(
        default_factory=lambda: int(os.environ.get("METRICS_INTERVAL", "5"))
    )
    # Inference simulation interval (dev/demo mode)
    simulation_interval_seconds: int = field(
        default_factory=lambda: int(os.environ.get("SIMULATION_INTERVAL", "2"))
    )
    # Anomaly detection interval
    anomaly_check_interval_seconds: int = field(
        default_factory=lambda: int(os.environ.get("ANOMALY_INTERVAL", "30"))
    )
    # Enable simulated traffic (set to "false" in production with real models)
    simulate_traffic: bool = field(
        default_factory=lambda: os.environ.get("SIMULATE_TRAFFIC", "true").lower() == "true"
    )


@dataclass
class ThresholdConfig:
    """Alert and anomaly thresholds — all overridable via env vars."""
    latency_warning_ms: float = field(
        default_factory=lambda: float(os.environ.get("THRESHOLD_LATENCY_WARNING_MS", "300"))
    )
    latency_critical_ms: float = field(
        default_factory=lambda: float(os.environ.get("THRESHOLD_LATENCY_CRITICAL_MS", "500"))
    )
    error_rate_warning_pct: float = field(
        default_factory=lambda: float(os.environ.get("THRESHOLD_ERROR_RATE_WARNING", "5.0"))
    )
    error_rate_critical_pct: float = field(
        default_factory=lambda: float(os.environ.get("THRESHOLD_ERROR_RATE_CRITICAL", "10.0"))
    )
    cpu_warning_pct: float = field(
        default_factory=lambda: float(os.environ.get("THRESHOLD_CPU_WARNING", "75.0"))
    )
    cpu_critical_pct: float = field(
        default_factory=lambda: float(os.environ.get("THRESHOLD_CPU_CRITICAL", "90.0"))
    )
    ram_warning_pct: float = field(
        default_factory=lambda: float(os.environ.get("THRESHOLD_RAM_WARNING", "80.0"))
    )
    ram_critical_pct: float = field(
        default_factory=lambda: float(os.environ.get("THRESHOLD_RAM_CRITICAL", "90.0"))
    )
    drift_warning_score: float = field(
        default_factory=lambda: float(os.environ.get("THRESHOLD_DRIFT_WARNING", "0.1"))
    )
    drift_critical_score: float = field(
        default_factory=lambda: float(os.environ.get("THRESHOLD_DRIFT_CRITICAL", "0.2"))
    )
    zscore_anomaly_threshold: float = field(
        default_factory=lambda: float(os.environ.get("THRESHOLD_ZSCORE", "2.5"))
    )


@dataclass
class AppConfig:
    """Master config — single source of truth for the entire platform."""
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    server: ServerConfig = field(default_factory=ServerConfig)
    alerts: AlertConfig = field(default_factory=AlertConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    thresholds: ThresholdConfig = field(default_factory=ThresholdConfig)
    environment: str = field(
        default_factory=lambda: os.environ.get("ENVIRONMENT", "development")
    )
    debug: bool = field(
        default_factory=lambda: os.environ.get("DEBUG", "false").lower() == "true"
    )

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    def summary(self) -> dict:
        return {
            "environment": self.environment,
            "debug": self.debug,
            "db_path": self.database.path,
            "server": f"{self.server.host}:{self.server.port}",
            "simulate_traffic": self.monitoring.simulate_traffic,
            "slack_alerts": bool(self.alerts.slack_webhook_url),
            "email_alerts": bool(self.alerts.smtp_user),
            "telegram_alerts": bool(self.alerts.telegram_bot_token),
        }


# Global singleton — import this everywhere
settings = AppConfig()
