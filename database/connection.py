"""
Database layer — SQLite for dev, PostgreSQL for production.
Manages all persistent storage for the monitoring platform.
"""

import sqlite3
import json
import os
from datetime import datetime
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)


def get_db_path() -> str:
    """
    Always read DB_PATH fresh from environment at call time.
    This ensures tests that set os.environ["DB_PATH"] before
    importing this module get the correct path — not a stale
    module-level constant that was captured at import time.
    """
    return os.environ.get("DB_PATH", "monitoring.db")


def get_connection():
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    return conn


async def init_db():
    """Initialize all database tables."""
    conn = get_connection()
    cursor = conn.cursor()

    # Registered models table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS registered_models (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            model_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            version TEXT NOT NULL,
            status TEXT DEFAULT 'active',
            description TEXT,
            endpoint TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Inference logs table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inference_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            model_id TEXT NOT NULL,
            request_id TEXT,
            input_data TEXT,
            output_data TEXT,
            confidence REAL,
            latency_ms REAL NOT NULL,
            status TEXT NOT NULL,
            error_message TEXT,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # System metrics table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS system_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cpu_percent REAL,
            ram_percent REAL,
            ram_used_gb REAL,
            ram_total_gb REAL,
            gpu_percent REAL,
            gpu_memory_percent REAL,
            disk_percent REAL,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Drift reports table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS drift_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            model_id TEXT NOT NULL,
            drift_type TEXT NOT NULL,
            drift_score REAL NOT NULL,
            is_drifted INTEGER DEFAULT 0,
            details TEXT,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Alerts table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            alert_type TEXT NOT NULL,
            severity TEXT NOT NULL,
            model_id TEXT,
            message TEXT NOT NULL,
            details TEXT,
            resolved INTEGER DEFAULT 0,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
            resolved_at TEXT
        )
    """)

    # Anomaly detections table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS anomaly_detections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            model_id TEXT,
            anomaly_type TEXT NOT NULL,
            score REAL NOT NULL,
            description TEXT,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()

    # Seed demo models if empty
    await seed_demo_data()
    logger.info("✅ Database initialized.")


async def seed_demo_data():
    """Seed demo models for showcase."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM registered_models")
    count = cursor.fetchone()[0]

    if count == 0:
        demo_models = [
            ("fraud_detector_v1", "Fraud Detector", "1.0.0", "active",
             "Real-time fraud detection model", "/predict/fraud"),
            ("fraud_detector_v2", "Fraud Detector", "2.0.0", "active",
             "Improved fraud detection with XGBoost", "/predict/fraud/v2"),
            ("recommendation_model", "Recommendation Engine", "1.2.0", "active",
             "Collaborative filtering recommender", "/predict/recommend"),
            ("vision_model", "Vision Classifier", "3.1.0", "active",
             "CNN-based image classifier", "/predict/vision"),
            ("nlp_sentiment", "Sentiment Analyzer", "2.0.1", "deprecated",
             "BERT-based sentiment analysis", "/predict/sentiment"),
        ]
        cursor.executemany(
            "INSERT OR IGNORE INTO registered_models "
            "(model_id, name, version, status, description, endpoint) "
            "VALUES (?,?,?,?,?,?)",
            demo_models
        )
        conn.commit()
    conn.close()
