from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.api.deps import get_db
from backend.app.models.schema_models import IngestionJob, Folder, UploadedFile, JobExecution
from backend.app.schemas.ingestion_schemas import (
    JobCreate, JobUpdate, JobResponse, JobExecutionResponse
)
from backend.app.services.job_executor import JobExecutor
from backend.app.services.scheduler_service import SchedulerService

router = APIRouter(prefix="/jobs", tags=["Jobs"])

@router.get("", response_model=List[JobResponse])
def list_jobs(db: Session = Depends(get_db)):
    jobs = db.query(IngestionJob).order_by(IngestionJob.created_at.desc()).all()
    res = []
    for j in jobs:
        folder = db.query(Folder).filter(Folder.id == j.folder_id).first()
        pending_count = 0
        if folder:
            pending_count = db.query(UploadedFile).filter(
                UploadedFile.folder_id == folder.id,
                UploadedFile.status.in_(["pending", "failed"])
            ).count()

        res.append(JobResponse(
            id=j.id,
            name=j.name,
            folder_id=j.folder_id,
            folder_name=folder.name if folder else "Unknown",
            target_table=j.target_table,
            is_active=j.is_active,
            schedule_type=j.schedule_type,
            schedule_value=j.schedule_value,
            columns_config=j.columns_config,
            created_at=j.created_at,
            updated_at=j.updated_at,
            pending_files_count=pending_count
        ))
    return res

@router.post("", response_model=JobResponse)
def create_job(job_in: JobCreate, db: Session = Depends(get_db)):
    clean_name = job_in.name.strip()
    existing = db.query(IngestionJob).filter(IngestionJob.name.ilike(clean_name)).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Job '{clean_name}' already exists")

    folder = db.query(Folder).filter(Folder.id == job_in.folder_id).first()
    if not folder:
        raise HTTPException(status_code=400, detail="Invalid folder ID")

    # Validate primary key is configured
    pk_cols = [c.name for c in job_in.columns_config if c.is_primary_key]
    if not pk_cols:
        raise HTTPException(status_code=400, detail="Please designate at least one column as the Primary Key / Unique identifier")

    cols_json = [c.dict() for c in job_in.columns_config]

    job = IngestionJob(
        name=clean_name,
        folder_id=folder.id,
        target_table=job_in.target_table.strip().upper(),
        is_active=job_in.is_active,
        schedule_type=job_in.schedule_type,
        schedule_value=job_in.schedule_value,
        columns_config=cols_json
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # Register in scheduler if active
    SchedulerService.register_job(job)

    return JobResponse(
        id=job.id,
        name=job.name,
        folder_id=job.folder_id,
        folder_name=folder.name,
        target_table=job.target_table,
        is_active=job.is_active,
        schedule_type=job.schedule_type,
        schedule_value=job.schedule_value,
        columns_config=job.columns_config,
        created_at=job.created_at,
        updated_at=job.updated_at,
        pending_files_count=0
    )

@router.put("/{id}", response_model=JobResponse)
def update_job(id: str, job_in: JobUpdate, db: Session = Depends(get_db)):
    job = db.query(IngestionJob).filter(IngestionJob.id == id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job_in.name is not None:
        job.name = job_in.name.strip()
    if job_in.folder_id is not None:
        job.folder_id = job_in.folder_id
    if job_in.target_table is not None:
        job.target_table = job_in.target_table.strip().upper()
    if job_in.is_active is not None:
        job.is_active = job_in.is_active
    if job_in.schedule_type is not None:
        job.schedule_type = job_in.schedule_type
    if job_in.schedule_value is not None:
        job.schedule_value = job_in.schedule_value
    if job_in.columns_config is not None:
        pk_cols = [c.name for c in job_in.columns_config if c.is_primary_key]
        if not pk_cols:
            raise HTTPException(status_code=400, detail="Primary Key must be designated in column configuration")
        job.columns_config = [c.dict() for c in job_in.columns_config]

    db.commit()
    db.refresh(job)

    SchedulerService.register_job(job)

    folder = db.query(Folder).filter(Folder.id == job.folder_id).first()
    return JobResponse(
        id=job.id,
        name=job.name,
        folder_id=job.folder_id,
        folder_name=folder.name if folder else "Unknown",
        target_table=job.target_table,
        is_active=job.is_active,
        schedule_type=job.schedule_type,
        schedule_value=job.schedule_value,
        columns_config=job.columns_config,
        created_at=job.created_at,
        updated_at=job.updated_at,
        pending_files_count=0
    )

@router.delete("/{id}")
def delete_job(id: str, db: Session = Depends(get_db)):
    job = db.query(IngestionJob).filter(IngestionJob.id == id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    db.delete(job)
    db.commit()
    SchedulerService.sync_jobs()
    return {"message": f"Job '{job.name}' deleted successfully"}

@router.post("/{id}/run")
def run_job_manually(id: str, db: Session = Depends(get_db)):
    results = JobExecutor.execute_job(db, id, execution_type="Manual")
    return {"job_id": id, "results": results}

@router.get("/history", response_model=List[JobExecutionResponse])
def get_execution_history(limit: int = 50, db: Session = Depends(get_db)):
    return db.query(JobExecution).order_by(JobExecution.execution_time.desc()).limit(limit).all()
