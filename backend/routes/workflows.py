"""FastAPI workflow routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.services.workflow_service import (
    get_history_service,
    replay_workflow_service,
    run_workflow_service,
)


router = APIRouter(prefix="/workflows", tags=["workflows"])


class WorkflowRequest(BaseModel):
    query: str
    enable_compare: bool = True


@router.post("/run")
def run_workflow_endpoint(payload: WorkflowRequest):
    return run_workflow_service(payload.query, enable_compare=payload.enable_compare)


@router.get("/history")
def workflow_history_endpoint(limit: int = 20):
    return {"items": get_history_service(limit=limit)}


@router.get("/replay/{run_id}")
def workflow_replay_endpoint(run_id: int):
    data = replay_workflow_service(run_id)
    if not data:
        raise HTTPException(status_code=404, detail="Workflow run not found.")
    return data


@router.get("/export/{run_id}")
def workflow_export_endpoint(run_id: int):
    data = replay_workflow_service(run_id)
    if not data:
        raise HTTPException(status_code=404, detail="Workflow run not found.")
    return {"export_paths": data.get("export_paths", {})}
