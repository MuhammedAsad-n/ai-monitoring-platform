"""Prometheus metrics export endpoint."""

from fastapi import APIRouter
from fastapi.responses import Response
from metrics.prometheus_exporter import prometheus_exporter

router = APIRouter()


@router.get("/metrics")
async def prometheus_metrics():
    """
    Prometheus-compatible metrics endpoint.
    Point your Prometheus scraper at: GET /api/prometheus/metrics
    """
    content, content_type = prometheus_exporter.get_metrics_output()
    return Response(content=content, media_type=content_type)
