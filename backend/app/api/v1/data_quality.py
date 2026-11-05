import csv
import io
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session
from backend.app.api.deps import get_db
from backend.app.models.all_models import DataQualityResult, RejectedRecord
from backend.app.schemas.data_quality_schemas import (
    DataQualityResultResponse, RejectedRecordResponse
)

router = APIRouter(prefix="/data-quality", tags=["Data Quality"])

@router.get("/results", response_model=List[DataQualityResultResponse])
def get_data_quality_results(
    limit: int = 50,
    db: Session = Depends(get_db)
):
    return db.query(DataQualityResult).order_by(DataQualityResult.checked_at.desc()).limit(limit).all()

@router.get("/rejected-records", response_model=List[RejectedRecordResponse])
def get_rejected_records(
    rule: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    query = db.query(RejectedRecord)
    if rule:
        query = query.filter(RejectedRecord.rule_violated == rule)
    return query.order_by(RejectedRecord.created_at.desc()).limit(limit).all()

@router.get("/rejected-records/export")
def export_rejected_records_csv(db: Session = Depends(get_db)):
    records = db.query(RejectedRecord).order_by(RejectedRecord.created_at.desc()).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "workflow_run_id", "record_identifier", "rule_violated", "rejection_reason", "created_at"])
    for r in records:
        writer.writerow([r.id, r.workflow_run_id, r.record_identifier, r.rule_violated, r.rejection_reason, r.created_at.isoformat()])
    
    csv_data = output.getvalue()
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=rejected_records_report.csv"}
    )
