import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Boolean, Integer, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from backend.app.core.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class Folder(Base):
    __tablename__ = "folders"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    files = relationship("UploadedFile", back_populates="folder", cascade="all, delete-orphan")
    jobs = relationship("IngestionJob", back_populates="folder")


class UploadedFile(Base):
    __tablename__ = "uploaded_files"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    folder_id = Column(String(36), ForeignKey("folders.id"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size_bytes = Column(Integer, default=0)
    status = Column(String(50), default="pending", index=True)  # pending, processed, failed
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    records_inserted = Column(Integer, default=0)
    records_updated = Column(Integer, default=0)

    @property
    def created_at(self):
        return self.uploaded_at

    folder = relationship("Folder", back_populates="files")


class IngestionJob(Base):
    __tablename__ = "ingestion_jobs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(100), unique=True, nullable=False, index=True)  # e.g., DC_Employee
    folder_id = Column(String(36), ForeignKey("folders.id"), nullable=False, index=True)
    target_table = Column(String(100), nullable=False)  # e.g., EMPLOYEE
    is_active = Column(Boolean, default=True)
    schedule_type = Column(String(50), default="manual")  # manual, hourly, daily, custom_cron
    schedule_value = Column(String(100), nullable=True)  # cron string or interval
    columns_config = Column(JSON, nullable=False, default=list)  # list of {name, type, is_primary_key, is_required}
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    folder = relationship("Folder", back_populates="jobs")
    executions = relationship("JobExecution", back_populates="job", cascade="all, delete-orphan")


class JobExecution(Base):
    __tablename__ = "job_executions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    job_id = Column(String(36), ForeignKey("ingestion_jobs.id"), nullable=True, index=True)
    job_name = Column(String(100), nullable=False)
    execution_time = Column(DateTime, default=datetime.utcnow)
    execution_type = Column(String(50), default="Manual")  # Manual, Scheduled
    file_name = Column(String(255), nullable=True)
    records_processed = Column(Integer, default=0)
    records_inserted = Column(Integer, default=0)
    records_updated = Column(Integer, default=0)
    execution_status = Column(String(50), default="Success", index=True)  # Success, Failed
    error_details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    job = relationship("IngestionJob", back_populates="executions")


class SnowflakeConfig(Base):
    __tablename__ = "snowflake_config"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    account = Column(String(100), nullable=True)
    user = Column(String(100), nullable=True)
    password = Column(String(255), nullable=True)
    warehouse = Column(String(100), default="COMPUTE_WH")
    database = Column(String(100), default="ENTERPRISE_DW")
    schema_name = Column(String(100), default="PUBLIC")
    role = Column(String(100), default="ACCOUNTADMIN")
    is_active = Column(Boolean, default=False)
    last_tested_at = Column(DateTime, nullable=True)
    is_connected = Column(Boolean, default=False)
    connection_message = Column(String(255), default="Local Warehouse Mode active")
