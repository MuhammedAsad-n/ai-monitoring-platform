"""Alerts API routes."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from logging_system.logger import alert_manager

router = APIRouter()

class FireAlertRequest(BaseModel):
    alert_type: str
    severity: str
    message: str
    model_id: Optional[str] = None
    details: Optional[dict] = None

@router.get("/active")
async def get_active_alerts():
    return {"alerts": alert_manager.get_active_alerts()}

@router.get("/history")
async def get_alert_history(limit: int = 100):
    return {"alerts": alert_manager.get_alert_history(limit=limit)}

@router.get("/stats")
async def get_alert_stats():
    return alert_manager.get_alert_stats()

@router.post("/fire")
async def fire_alert(req: FireAlertRequest):
    alert = alert_manager.fire_alert(
        alert_type=req.alert_type,
        severity=req.severity,
        message=req.message,
        model_id=req.model_id,
        details=req.details,
    )
    return alert

@router.post("/{alert_id}/resolve")
async def resolve_alert(alert_id: int):
    success = alert_manager.resolve_alert(alert_id)
    if not success:
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"status": "resolved", "alert_id": alert_id}
