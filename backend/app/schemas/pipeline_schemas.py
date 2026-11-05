from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel
from backend.app.schemas.connector_schemas import DataSourceResponse, DataDestinationResponse

class PipelineBase(BaseModel):
    name: str
    description: Optional[str] = None
    source_id: str
    destination_id: str
    transformation_config: Dict[str, Any] = {}
    schedule_cron: Optional[str] = "0 * * * *"
    status: str = "active"

class PipelineCreate(PipelineBase):
    pass

class PipelineUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    source_id: Optional[str] = None
    destination_id: Optional[str] = None
    transformation_config: Optional[Dict[str, Any]] = None
    schedule_cron: Optional[str] = None
    status: Optional[str] = None
    is_active: Optional[bool] = None

class PipelineResponse(PipelineBase):
    id: str
    owner_id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    source: Optional[DataSourceResponse] = None
    destination: Optional[DataDestinationResponse] = None

    class Config:
        from_attributes = True

class PipelineExecuteRequest(BaseModel):
    trigger_type: str = "manual"
    simulate_failure: Optional[str] = None  # None, "api_error", "invalid_data", "sftp_failure"
    source_override: Optional[Dict[str, Any]] = None
