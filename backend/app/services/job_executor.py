import os
from datetime import datetime
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from backend.app.models.schema_models import IngestionJob, UploadedFile, JobExecution, Folder
from backend.app.services.validator_service import ValidatorService
from backend.app.services.snowflake_engine import SnowflakeEngine
from backend.app.services.storage_service import StorageService

class JobExecutor:
    @staticmethod
    def execute_job(db: Session, job_id: str, execution_type: str = "Manual") -> List[Dict[str, Any]]:
        job = db.query(IngestionJob).filter(IngestionJob.id == job_id).first()
        if not job:
            raise ValueError(f"Job {job_id} not found")

        folder = db.query(Folder).filter(Folder.id == job.folder_id).first()
        if not folder:
            raise ValueError(f"Folder for job {job.name} not found")

        # Discover pending or failed files in the folder (from DB & filesystem)
        pending_files = db.query(UploadedFile).filter(
            UploadedFile.folder_id == folder.id,
            UploadedFile.status.in_(["pending", "failed"])
        ).all()

        results = []

        if not pending_files:
            # Check if there are unindexed physical files in folder
            physical_files = StorageService.list_files_in_folder(folder.name)
            for fname in physical_files:
                fpath = os.path.join(StorageService.get_folder_path(folder.name), fname)
                f_size = os.path.getsize(fpath) if os.path.exists(fpath) else 0
                new_file = UploadedFile(
                    folder_id=folder.id,
                    filename=fname,
                    file_path=fpath,
                    file_size_bytes=f_size,
                    status="pending"
                )
                db.add(new_file)
                db.commit()
                db.refresh(new_file)
                pending_files.append(new_file)

        if not pending_files:
            # Record an execution showing no files were waiting
            no_file_exec = JobExecution(
                job_id=job.id,
                job_name=job.name,
                execution_time=datetime.utcnow(),
                execution_type=execution_type,
                file_name=None,
                records_processed=0,
                records_inserted=0,
                records_updated=0,
                execution_status="Success",
                error_details="No files waiting to be ingested in folder."
            )
            db.add(no_file_exec)
            db.commit()
            return [{
                "file_name": "None",
                "status": "Success",
                "message": "No files waiting to be ingested in folder."
            }]

        for u_file in pending_files:
            file_name = u_file.filename
            file_path = u_file.file_path

            if not os.path.exists(file_path):
                u_file.status = "failed"
                u_file.error_message = f"Physical file not found on disk at {file_path}"
                db.commit()
                continue

            try:
                # 1. Validate CSV
                validated_records, pk_col = ValidatorService.validate_csv(file_path, job.columns_config)

                # 2. Ingest into Target Table (Snowflake / Local DW)
                ins_count, upd_count, engine_mode = SnowflakeEngine.upsert_records(
                    table_name=job.target_table,
                    records=validated_records,
                    columns_config=job.columns_config,
                    primary_key_col=pk_col
                )

                # 3. Mark file as successfully processed in DB
                u_file.status = "processed"
                u_file.processed_at = datetime.utcnow()
                u_file.records_inserted = ins_count
                u_file.records_updated = upd_count
                u_file.error_message = None

                # 4. Log successful execution record
                execution = JobExecution(
                    job_id=job.id,
                    job_name=job.name,
                    execution_time=datetime.utcnow(),
                    execution_type=execution_type,
                    file_name=file_name,
                    records_processed=len(validated_records),
                    records_inserted=ins_count,
                    records_updated=upd_count,
                    execution_status="Success",
                    error_details=None
                )
                db.add(execution)
                db.commit()

                # 5. Rule: Delete the original CSV file from the processing folder only after DB transaction succeeds!
                StorageService.delete_file(file_path)

                results.append({
                    "file_name": file_name,
                    "status": "Success",
                    "records_processed": len(validated_records),
                    "records_inserted": ins_count,
                    "records_updated": upd_count,
                    "engine": engine_mode
                })

            except Exception as e:
                error_msg = str(e)
                # Rule: On failure, do NOT delete file! Store error and allow user to correct & retry.
                u_file.status = "failed"
                u_file.error_message = error_msg

                fail_execution = JobExecution(
                    job_id=job.id,
                    job_name=job.name,
                    execution_time=datetime.utcnow(),
                    execution_type=execution_type,
                    file_name=file_name,
                    records_processed=0,
                    records_inserted=0,
                    records_updated=0,
                    execution_status="Failed",
                    error_details=error_msg
                )
                db.add(fail_execution)
                db.commit()

                results.append({
                    "file_name": file_name,
                    "status": "Failed",
                    "error": error_msg
                })

        return results
