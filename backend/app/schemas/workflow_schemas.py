from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel

class WorkflowStepResponse(BaseModel):
    id: str
    step_name: str
    step_order: int
    status: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_seconds: float = 0.0
    retry_count: int = 0
    logs: str = ""
    error_details: Optional[str] = None
    output_data: Dict[str, Any] = {}

    class Config:
        from_attributes = True

class WorkflowRunResponse(BaseModel):
    id: str
    workflow_id: str
    pipeline_id: str
    run_number: int
    trigger_type: str
    status: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: float = 0.0
    error_message: Optional[str] = None
    correlation_id: str
    created_at: datetime
    steps: List[WorkflowStepResponse] = []

    class Config:
        from_attributes = True

class WorkflowRetryRequest(BaseModel):
    step_id: Optional[str] = None  # if null, reruns entire workflow
    clear_errors: bool = True
