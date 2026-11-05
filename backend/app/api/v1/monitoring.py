from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.api.deps import get_db, get_current_user, require_role
from backend.app.models.all_models import Incident, AuditLog, WorkflowStep, User
from backend.app.schemas.monitoring_schemas import (
    IncidentResponse, IncidentUpdate, AuditLogResponse
)
from backend.app.services.incident_service import IncidentService

router = APIRouter(prefix="/monitoring", tags=["Monitoring & Incidents"])

@router.get("/incidents", response_model=List[IncidentResponse])
def list_incidents(
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Incident)
    if status:
        query = query.filter(Incident.status == status)
    return query.order_by(Incident.reported_at.desc()).all()

@router.patch("/incidents/{id}", response_model=IncidentResponse)
def update_incident(
    id: str,
    update_in: IncidentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "ops_engineer"]))
):
    incident = db.query(Incident).filter(Incident.id == id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    if update_in.status:
        incident.status = update_in.status
        if update_in.status == "resolved":
            incident.resolved_at = datetime.utcnow()
    if update_in.resolution_notes:
        incident.resolution_notes = update_in.resolution_notes
    if update_in.severity:
        incident.severity = update_in.severity

    db.commit()
    db.refresh(incident)
    return incident

@router.get("/audit-logs", response_model=List[AuditLogResponse])
def get_audit_logs(
    limit: int = 100,
    db: Session = Depends(get_db)
):
    return db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit).all()

@router.get("/live-logs")
def get_live_logs(
    limit: int = 50,
    db: Session = Depends(get_db)
):
    steps = db.query(WorkflowStep).filter(
        WorkflowStep.logs != ""
    ).order_by(WorkflowStep.start_time.desc()).limit(limit).all()

    return [
        {
            "step_id": s.id,
            "step_name": s.step_name,
            "run_id": s.workflow_run_id,
            "status": s.status,
            "logs": s.logs,
            "duration": s.duration_seconds,
            "timestamp": s.start_time.isoformat() if s.start_time else None
        }
        for s in steps
    ]
