from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from backend.app.models.all_models import Incident, WorkflowRun

class IncidentService:
    def __init__(self, db: Session):
        self.db = db

    def create_incident(
        self, 
        workflow_run_id: str, 
        pipeline_id: str, 
        title: str, 
        root_cause: str,
        severity: str = "medium"
    ) -> Incident:
        incident = Incident(
            workflow_run_id=workflow_run_id,
            pipeline_id=pipeline_id,
            title=title,
            severity=severity,
            status="open",
            root_cause=root_cause,
            reported_at=datetime.utcnow()
        )
        self.db.add(incident)
        self.db.commit()
        self.db.refresh(incident)
        return incident

    def resolve_incident(self, incident_id: str, resolution_notes: str) -> Optional[Incident]:
        incident = self.db.query(Incident).filter(Incident.id == incident_id).first()
        if not incident:
            return None
        incident.status = "resolved"
        incident.resolution_notes = resolution_notes
        incident.resolved_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(incident)
        return incident
