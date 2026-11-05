from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from backend.app.api.deps import get_db, get_current_user, require_role
from backend.app.models.all_models import (
    Pipeline, PipelineVersion, WorkflowRun, DataSource, DataDestination, User, AuditLog
)
from backend.app.schemas.pipeline_schemas import (
    PipelineCreate, PipelineUpdate, PipelineResponse, PipelineExecuteRequest
)
from backend.app.schemas.workflow_schemas import WorkflowRunResponse
from backend.app.services.workflow_engine import WorkflowExecutionEngine

router = APIRouter(prefix="/pipelines", tags=["Pipelines"])

@router.get("", response_model=List[PipelineResponse])
def list_pipelines(
    status: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Pipeline)
    if status:
        query = query.filter(Pipeline.status == status)
    if search:
        query = query.filter(Pipeline.name.ilike(f"%{search}%"))
    return query.order_by(Pipeline.created_at.desc()).all()

@router.post("", response_model=PipelineResponse)
def create_pipeline(
    p_in: PipelineCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "data_engineer"]))
):
    # Verify source & destination exist
    src = db.query(DataSource).filter(DataSource.id == p_in.source_id).first()
    dst = db.query(DataDestination).filter(DataDestination.id == p_in.destination_id).first()
    if not src or not dst:
        raise HTTPException(status_code=400, detail="Invalid source or destination ID")

    pipeline = Pipeline(
        name=p_in.name,
        description=p_in.description,
        source_id=p_in.source_id,
        destination_id=p_in.destination_id,
        transformation_config=p_in.transformation_config,
        schedule_cron=p_in.schedule_cron,
        status=p_in.status,
        owner_id=current_user.id
    )
    db.add(pipeline)
    db.commit()
    db.refresh(pipeline)

    # Create initial version
    version = PipelineVersion(
        pipeline_id=pipeline.id,
        version_number=1,
        config_snapshot={
            "name": pipeline.name,
            "source_id": pipeline.source_id,
            "destination_id": pipeline.destination_id,
            "transformation_config": pipeline.transformation_config,
            "schedule_cron": pipeline.schedule_cron
        },
        created_by=current_user.id
    )
    db.add(version)

    # Audit log
    audit = AuditLog(
        user_id=current_user.id,
        action="CREATE_PIPELINE",
        resource_type="pipeline",
        resource_id=pipeline.id,
        details={"name": pipeline.name}
    )
    db.add(audit)
    db.commit()

    return pipeline

@router.get("/{id}", response_model=PipelineResponse)
def get_pipeline(id: str, db: Session = Depends(get_db)):
    pipeline = db.query(Pipeline).filter(Pipeline.id == id).first()
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return pipeline

@router.put("/{id}", response_model=PipelineResponse)
def update_pipeline(
    id: str,
    p_in: PipelineUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "data_engineer"]))
):
    pipeline = db.query(Pipeline).filter(Pipeline.id == id).first()
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    update_data = p_in.dict(exclude_unset=True)
    for field, val in update_data.items():
        setattr(pipeline, field, val)
    pipeline.updated_at = datetime.utcnow()

    # Track version
    latest_ver = db.query(PipelineVersion).filter(
        PipelineVersion.pipeline_id == pipeline.id
    ).order_by(PipelineVersion.version_number.desc()).first()
    next_ver = (latest_ver.version_number + 1) if latest_ver else 1

    version = PipelineVersion(
        pipeline_id=pipeline.id,
        version_number=next_ver,
        config_snapshot=update_data,
        created_by=current_user.id
    )
    db.add(version)
    db.commit()
    db.refresh(pipeline)
    return pipeline

@router.post("/{id}/execute", response_model=WorkflowRunResponse)
def execute_pipeline(
    id: str,
    req: PipelineExecuteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "data_engineer", "ops_engineer"]))
):
    pipeline = db.query(Pipeline).filter(Pipeline.id == id).first()
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    engine = WorkflowExecutionEngine(db)
    run = engine.execute_workflow(
        pipeline_id=pipeline.id,
        trigger_type=req.trigger_type,
        simulate_failure=req.simulate_failure,
        source_override=req.source_override
    )
    return run

@router.get("/{id}/runs", response_model=List[WorkflowRunResponse])
def get_pipeline_runs(id: str, db: Session = Depends(get_db)):
    return db.query(WorkflowRun).filter(
        WorkflowRun.pipeline_id == id
    ).order_by(WorkflowRun.created_at.desc()).all()
