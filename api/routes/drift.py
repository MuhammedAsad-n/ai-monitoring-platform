"""Drift detection API routes."""
from fastapi import APIRouter, HTTPException
from monitoring.latency_and_drift import drift_detector

router = APIRouter()

@router.get("/{model_id}/confidence")
async def check_confidence_drift(model_id: str):
    return drift_detector.detect_confidence_drift(model_id)

@router.get("/{model_id}/latency")
async def check_latency_drift(model_id: str):
    return drift_detector.detect_latency_drift(model_id)

@router.get("/{model_id}/report")
async def get_full_drift_report(model_id: str):
    conf_drift = drift_detector.detect_confidence_drift(model_id)
    lat_drift = drift_detector.detect_latency_drift(model_id)
    history = drift_detector.get_drift_history(model_id)
    any_drifted = conf_drift.get("is_drifted") or lat_drift.get("is_drifted")
    return {
        "model_id": model_id,
        "overall_status": "drifted" if any_drifted else "stable",
        "confidence_drift": conf_drift,
        "latency_drift": lat_drift,
        "history": history,
    }

@router.get("/{model_id}/history")
async def get_drift_history(model_id: str, limit: int = 20):
    return drift_detector.get_drift_history(model_id, limit=limit)
