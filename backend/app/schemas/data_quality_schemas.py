from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel

class RejectedRecordResponse(BaseModel):
    id: str
    workflow_run_id: str
    batch_id: str
    record_identifier: Optional[str] = None
    raw_data: Dict[str, Any]
    rejection_reason: str
    rule_violated: str
    created_at: datetime

    class Config:
        from_attributes = True

class DataQualityResultResponse(BaseModel):
    id: str
    workflow_run_id: str
    batch_id: str
    total_records: int
    valid_records: int
    rejected_records: int
    rules_triggered: List[str] = []
    reconciliation_status: str
    checked_at: datetime

    class Config:
        from_attributes = True
