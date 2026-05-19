"""
MODULE 2 — METRICS COLLECTION SYSTEM
Collects real-time CPU, RAM, GPU, and application metrics.
"""

import psutil
import time
import sqlite3
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from database.connection import get_connection

logger = logging.getLogger(__name__)

# Try GPU monitoring (optional — requires nvidia GPU)
try:
    import pynvml
    pynvml.nvmlInit()
    GPU_AVAILABLE = True
    logger.info("✅ GPU monitoring enabled (pynvml)")
except Exception:
    GPU_AVAILABLE = False
    logger.info("ℹ️ GPU monitoring unavailable — no NVIDIA GPU detected")


class MetricsCollector:
    """Collects and stores system metrics continuously."""

    def __init__(self):
        self.collection_interval = 5  # seconds
        self._latency_buffer: list = []
        self._request_count = 0
        self._error_count = 0
        self._start_time = time.time()

    def get_cpu_metrics(self) -> Dict[str, Any]:
        return {
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "cpu_count": psutil.cpu_count(),
            "cpu_freq_mhz": psutil.cpu_freq().current if psutil.cpu_freq() else None,
        }

    def get_ram_metrics(self) -> Dict[str, Any]:
        mem = psutil.virtual_memory()
        return {
            "ram_percent": mem.percent,
            "ram_used_gb": round(mem.used / 1e9, 2),
            "ram_total_gb": round(mem.total / 1e9, 2),
            "ram_available_gb": round(mem.available / 1e9, 2),
        }

    def get_gpu_metrics(self) -> Dict[str, Any]:
        if not GPU_AVAILABLE:
            return {
                "gpu_available": False,
                "gpu_percent": None,
                "gpu_memory_percent": None,
                "gpu_memory_used_mb": None,
            }
        try:
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            util = pynvml.nvmlDeviceGetUtilizationRates(handle)
            mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
            return {
                "gpu_available": True,
                "gpu_percent": util.gpu,
                "gpu_memory_percent": round(mem_info.used / mem_info.total * 100, 1),
                "gpu_memory_used_mb": round(mem_info.used / 1e6, 1),
            }
        except Exception as e:
            return {"gpu_available": False, "error": str(e)}

    def get_disk_metrics(self) -> Dict[str, Any]:
        disk = psutil.disk_usage("/")
        return {
            "disk_percent": disk.percent,
            "disk_used_gb": round(disk.used / 1e9, 2),
            "disk_total_gb": round(disk.total / 1e9, 2),
        }

    def get_network_metrics(self) -> Dict[str, Any]:
        net = psutil.net_io_counters()
        return {
            "bytes_sent_mb": round(net.bytes_sent / 1e6, 2),
            "bytes_recv_mb": round(net.bytes_recv / 1e6, 2),
        }

    def get_application_metrics(self) -> Dict[str, Any]:
        uptime = time.time() - self._start_time
        avg_latency = (
            sum(self._latency_buffer) / len(self._latency_buffer)
            if self._latency_buffer else 0
        )
        error_rate = (
            self._error_count / self._request_count * 100
            if self._request_count > 0 else 0
        )
        throughput = self._request_count / max(uptime, 1) * 60  # req/min

        return {
            "uptime_seconds": round(uptime, 1),
            "total_requests": self._request_count,
            "total_errors": self._error_count,
            "error_rate_percent": round(error_rate, 2),
            "avg_latency_ms": round(avg_latency, 2),
            "throughput_rpm": round(throughput, 2),
        }

    def record_inference(self, latency_ms: float, success: bool):
        """Called after each inference to update metrics."""
        self._latency_buffer.append(latency_ms)
        self._request_count += 1
        if not success:
            self._error_count += 1
        # Keep buffer bounded
        if len(self._latency_buffer) > 1000:
            self._latency_buffer = self._latency_buffer[-500:]

    def collect_all(self) -> Dict[str, Any]:
        """Collect all system metrics in one shot."""
        metrics = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **self.get_cpu_metrics(),
            **self.get_ram_metrics(),
            **self.get_gpu_metrics(),
            **self.get_disk_metrics(),
            **self.get_network_metrics(),
            "application": self.get_application_metrics(),
        }
        self._persist_metrics(metrics)
        return metrics

    def _persist_metrics(self, metrics: Dict[str, Any]):
        """Persist system metrics snapshot to database."""
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO system_metrics
                (cpu_percent, ram_percent, ram_used_gb, ram_total_gb,
                 gpu_percent, gpu_memory_percent, disk_percent, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                metrics.get("cpu_percent"),
                metrics.get("ram_percent"),
                metrics.get("ram_used_gb"),
                metrics.get("ram_total_gb"),
                metrics.get("gpu_percent"),
                metrics.get("gpu_memory_percent"),
                metrics.get("disk_percent"),
                metrics["timestamp"],
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to persist metrics: {e}")


# Global singleton
collector = MetricsCollector()
