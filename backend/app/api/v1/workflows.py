from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from backend.app.api.deps import get_db, get_current_user, require_role
from backend.app.models.all_models import WorkflowRun, WorkflowStep, Pipeline, User
from backend.app.schemas.workflow_schemas import WorkflowRunResponse, WorkflowRetryRequest
from backend.app.services.workflow_engine import WorkflowExecutionEngine
from backend.app.services.azure_adapter import AzureLogicAppAdapter

router = APIRouter(prefix="/workflows", tags=["Workflows"])

@router.get("/runs", response_model=List[WorkflowRunResponse])
def list_workflow_runs(
    status: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    query = db.query(WorkflowRun)
    if status:
        query = query.filter(WorkflowRun.status == status)
    return query.order_by(WorkflowRun.created_at.desc()).limit(limit).all()

@router.get("/runs/{id}", response_model=WorkflowRunResponse)
def get_workflow_run(id: str, db: Session = Depends(get_db)):
    run = db.query(WorkflowRun).filter(WorkflowRun.id == id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Workflow run not found")
    return run

@router.post("/runs/{id}/retry", response_model=WorkflowRunResponse)
def retry_workflow_run(
    id: str,
    req: WorkflowRetryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "ops_engineer", "data_engineer"]))
):
    run = db.query(WorkflowRun).filter(WorkflowRun.id == id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Workflow run not found")

    engine = WorkflowExecutionEngine(db)
    # Retry execution cleanly (idempotent, deduplicated, no duplicated warehouse records)
    retried_run = engine.execute_workflow(
        pipeline_id=run.pipeline_id,
        trigger_type="retry",
        simulate_failure=None,  # Clear any injected failure on retry!
        existing_run_id=run.id
    )
    return retried_run

@router.post("/azure-logic-app/trigger")
def trigger_azure_logic_app(
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "ops_engineer", "data_engineer"]))
):
    adapter = AzureLogicAppAdapter()
    pipeline_id = payload.get("pipeline_id")
    if not pipeline_id:
        pipeline = db.query(Pipeline).first()
        pipeline_id = pipeline.id if pipeline else "default-pipeline"

    correlation_id = f"az-{payload.get('correlation_id', '12345')}"
    res = adapter.trigger_workflow(payload, correlation_id)
    return res
