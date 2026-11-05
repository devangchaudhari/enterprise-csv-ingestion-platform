from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

class FolderCreate(BaseModel):
    name: str
    description: Optional[str] = None

class FolderResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    created_at: datetime
    file_count: Optional[int] = 0
    pending_file_count: Optional[int] = 0

    class Config:
        from_attributes = True

class UploadedFileResponse(BaseModel):
    id: str
    folder_id: str
    filename: str
    file_path: Optional[str] = None
    file_size_bytes: int
    status: str
    uploaded_at: datetime
    created_at: Optional[datetime] = None
    processed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    records_inserted: int = 0
    records_updated: int = 0

    class Config:
        from_attributes = True

class ColumnConfig(BaseModel):
    name: str
    type: str = "String"  # String, Integer, Float, Date, Boolean
    is_primary_key: bool = False
    is_required: bool = True

class JobCreate(BaseModel):
    name: str
    folder_id: str
    target_table: str
    is_active: bool = True
    schedule_type: str = "manual"  # manual, hourly, daily, custom_cron
    schedule_value: Optional[str] = None
    columns_config: List[ColumnConfig]

class JobUpdate(BaseModel):
    name: Optional[str] = None
    folder_id: Optional[str] = None
    target_table: Optional[str] = None
    is_active: Optional[bool] = None
    schedule_type: Optional[str] = None
    schedule_value: Optional[str] = None
    columns_config: Optional[List[ColumnConfig]] = None

class JobResponse(BaseModel):
    id: str
    name: str
    folder_id: str
    folder_name: Optional[str] = None
    target_table: str
    is_active: bool
    schedule_type: str
    schedule_value: Optional[str] = None
    columns_config: List[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime
    pending_files_count: Optional[int] = 0

    class Config:
        from_attributes = True

class JobExecutionResponse(BaseModel):
    id: str
    job_id: Optional[str] = None
    job_name: str
    execution_time: datetime
    execution_type: str
    file_name: Optional[str] = None
    records_processed: int
    records_inserted: int
    records_updated: int
    execution_status: str
    error_details: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class SnowflakeConfigSchema(BaseModel):
    account: Optional[str] = None
    user: Optional[str] = None
    password: Optional[str] = None
    warehouse: Optional[str] = "COMPUTE_WH"
    database: Optional[str] = "ENTERPRISE_DW"
    schema_name: Optional[str] = "PUBLIC"
    role: Optional[str] = "ACCOUNTADMIN"
    is_active: bool = False
    is_connected: bool = False
    connection_message: Optional[str] = None
