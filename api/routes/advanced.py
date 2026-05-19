"""
Advanced features API routes.
Auto rollback + AI failure prediction.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from monitoring.advanced_features import auto_rollback, failure_predictor

router = APIRouter()


# ── Failure Prediction ───────────────────────────────────────

@router.get("/predict/{model_id}")
async def predict_failure(model_id: str):
    """Predict whether a model will fail in the next 15 minutes."""
    return failure_predictor.predict_failure(model_id)


@router.get("/predict")
async def predict_all_failures():
    """Run failure prediction across all active models."""
    return {"predictions": failure_predictor.predict_all_models()}


# ── Auto Rollback ────────────────────────────────────────────

@router.get("/rollback/evaluate/{model_id}")
async def evaluate_rollback(model_id: str):
    """Evaluate whether a model meets rollback criteria."""
    return auto_rollback.evaluate_model_for_rollback(model_id)


@router.get("/rollback/evaluate")
async def evaluate_all_rollbacks():
    """Evaluate all active models for rollback."""
    return {"evaluations": auto_rollback.check_all_models()}


class RollbackRequest(BaseModel):
    target_version: Optional[str] = None


@router.post("/rollback/{model_id}")
async def trigger_rollback(model_id: str, req: RollbackRequest = RollbackRequest()):
    """Manually trigger a rollback for a model."""
    result = auto_rollback.execute_rollback(model_id, req.target_version)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["reason"])
    return result
