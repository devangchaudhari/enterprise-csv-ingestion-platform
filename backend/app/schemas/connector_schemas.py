from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel

class DataSourceBase(BaseModel):
    name: str
    type: str  # rest_api, sftp, postgres, snowflake, csv_json
    connection_config: Dict[str, Any] = {}
    credentials_ref: Optional[str] = None
    is_active: bool = True

class DataSourceCreate(DataSourceBase):
    pass

class DataSourceUpdate(BaseModel):
    name: Optional[str] = None
    connection_config: Optional[Dict[str, Any]] = None
    credentials_ref: Optional[str] = None
    is_active: Optional[bool] = None

class DataSourceResponse(DataSourceBase):
    id: str
    status: str
    last_tested_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True

class DataDestinationBase(BaseModel):
    name: str
    type: str  # snowflake, postgres, rest_api, sftp
    connection_config: Dict[str, Any] = {}
    credentials_ref: Optional[str] = None
    is_active: bool = True

class DataDestinationCreate(DataDestinationBase):
    pass

class DataDestinationResponse(DataDestinationBase):
    id: str
    status: str
    last_tested_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True

class ConnectionTestResult(BaseModel):
    connector_id: str
    connector_type: str
    is_connected: bool
    latency_ms: float
    message: str
    details: Optional[Dict[str, Any]] = None
