from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel

class DashboardMetrics(BaseModel):
    total_pipelines: int
    successful_executions: int
    failed_executions: int
    running_workflows: int
    records_processed: int
    data_validation_failures: int
    average_execution_duration_sec: float
    active_incidents: int
    throughput_history: List[Dict[str, Any]] = []
    status_distribution: Dict[str, int] = {}
    validation_failures_by_rule: Dict[str, int] = {}

class IncidentResponse(BaseModel):
    id: str
    workflow_run_id: str
    pipeline_id: str
    title: str
    severity: str
    status: str
    root_cause: Optional[str] = None
    resolution_notes: Optional[str] = None
    reported_at: datetime
    resolved_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class IncidentUpdate(BaseModel):
    status: Optional[str] = None
    resolution_notes: Optional[str] = None
    severity: Optional[str] = None

class AuditLogResponse(BaseModel):
    id: str
    user_id: Optional[str] = None
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    details: Dict[str, Any] = {}
    ip_address: str
    created_at: datetime

    class Config:
        from_attributes = True
