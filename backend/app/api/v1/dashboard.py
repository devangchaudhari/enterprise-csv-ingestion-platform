from datetime import datetime, timedelta
from typing import Dict, Any, List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.app.api.deps import get_db, get_current_user
from backend.app.models.all_models import (
    Pipeline, WorkflowRun, IngestionBatch, RejectedRecord, 
    Incident, WarehouseOrder
)
from backend.app.schemas.monitoring_schemas import DashboardMetrics

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("/metrics", response_model=DashboardMetrics)
def get_dashboard_metrics(db: Session = Depends(get_db)):
    total_pipelines = db.query(Pipeline).count()
    successful_runs = db.query(WorkflowRun).filter(WorkflowRun.status == "completed").count()
    failed_runs = db.query(WorkflowRun).filter(WorkflowRun.status == "failed").count()
    running_workflows = db.query(WorkflowRun).filter(WorkflowRun.status == "running").count()

    # Total records processed through ingestion
    total_records = db.query(func.coalesce(func.sum(IngestionBatch.total_records), 0)).scalar() or 0
    if total_records == 0:
        total_records = db.query(WarehouseOrder).count()

    # Validation failures
    validation_failures = db.query(RejectedRecord).count()

    # Average execution duration for completed runs
    avg_duration = db.query(func.avg(WorkflowRun.duration_seconds)).filter(
        WorkflowRun.status == "completed",
        WorkflowRun.duration_seconds > 0
    ).scalar() or 0.0

    # Active incidents
    active_incidents = db.query(Incident).filter(Incident.status.in_(["open", "investigating"])).count()

    # Status distribution
    status_counts = db.query(WorkflowRun.status, func.count(WorkflowRun.id)).group_by(WorkflowRun.status).all()
    status_dist = {status: count for status, count in status_counts}

    # Validation failures grouped by rule
    failures_by_rule_query = db.query(
        RejectedRecord.rule_violated, 
        func.count(RejectedRecord.id)
    ).group_by(RejectedRecord.rule_violated).all()
    rule_dist = {rule: count for rule, count in failures_by_rule_query}

    # Recent throughput trend
    throughput_history = []
    recent_runs = db.query(WorkflowRun).order_by(WorkflowRun.created_at.desc()).limit(7).all()
    for r in reversed(recent_runs):
        throughput_history.append({
            "run_number": f"Run #{r.run_number}",
            "duration": round(r.duration_seconds, 2),
            "status": r.status,
            "created_at": r.created_at.strftime("%H:%M:%S")
        })

    return DashboardMetrics(
        total_pipelines=total_pipelines,
        successful_executions=successful_runs,
        failed_executions=failed_runs,
        running_workflows=running_workflows,
        records_processed=int(total_records),
        data_validation_failures=validation_failures,
        average_execution_duration_sec=round(float(avg_duration), 2),
        active_incidents=active_incidents,
        throughput_history=throughput_history,
        status_distribution=status_dist,
        validation_failures_by_rule=rule_dist
    )
