import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Boolean, Integer, Float, DateTime, 
    ForeignKey, JSON, Index, Enum as SQLEnum
)
from sqlalchemy.orm import relationship
from backend.app.core.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class Role(Base):
    __tablename__ = "roles"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(50), unique=True, nullable=False, index=True)
    description = Column(String(255), nullable=True)
    permissions = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)

    users = relationship("User", back_populates="role_rel")


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(50), ForeignKey("roles.name"), nullable=False, default="viewer")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    role_rel = relationship("Role", back_populates="users")
    pipelines = relationship("Pipeline", back_populates="owner")
    audit_logs = relationship("AuditLog", back_populates="user")


class DataSource(Base):
    __tablename__ = "data_sources"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(100), nullable=False, index=True)
    type = Column(String(50), nullable=False)  # rest_api, sftp, postgres, snowflake, csv_json
    connection_config = Column(JSON, default=dict)
    credentials_ref = Column(String(100), nullable=True)
    status = Column(String(50), default="untested")  # active, failed, untested
    last_tested_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    pipelines = relationship("Pipeline", back_populates="source")


class DataDestination(Base):
    __tablename__ = "data_destinations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(100), nullable=False, index=True)
    type = Column(String(50), nullable=False)  # snowflake, postgres, rest_api, sftp
    connection_config = Column(JSON, default=dict)
    credentials_ref = Column(String(100), nullable=True)
    status = Column(String(50), default="untested")
    last_tested_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    pipelines = relationship("Pipeline", back_populates="destination")


class Pipeline(Base):
    __tablename__ = "pipelines"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(150), nullable=False, index=True)
    description = Column(Text, nullable=True)
    source_id = Column(String(36), ForeignKey("data_sources.id"), nullable=False)
    destination_id = Column(String(36), ForeignKey("data_destinations.id"), nullable=False)
    transformation_config = Column(JSON, default=dict)
    schedule_cron = Column(String(100), nullable=True)
    status = Column(String(50), default="active")  # active, paused, draft
    owner_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = relationship("User", back_populates="pipelines")
    source = relationship("DataSource", back_populates="pipelines")
    destination = relationship("DataDestination", back_populates="pipelines")
    versions = relationship("PipelineVersion", back_populates="pipeline", cascade="all, delete-orphan")
    workflow_definition = relationship("WorkflowDefinition", back_populates="pipeline", uselist=False, cascade="all, delete-orphan")
    runs = relationship("WorkflowRun", back_populates="pipeline", cascade="all, delete-orphan")
    schedules = relationship("Schedule", back_populates="pipeline", cascade="all, delete-orphan")


class PipelineVersion(Base):
    __tablename__ = "pipeline_versions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    pipeline_id = Column(String(36), ForeignKey("pipelines.id"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)
    config_snapshot = Column(JSON, nullable=False)
    created_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    pipeline = relationship("Pipeline", back_populates="versions")


class WorkflowDefinition(Base):
    __tablename__ = "workflow_definitions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    pipeline_id = Column(String(36), ForeignKey("pipelines.id"), nullable=False, unique=True)
    name = Column(String(150), nullable=False)
    steps_definition = Column(JSON, default=list)  # ordered list of steps
    retry_policy = Column(JSON, default=lambda: {"max_retries": 3, "backoff_seconds": 2})
    timeout_seconds = Column(Integer, default=300)
    created_at = Column(DateTime, default=datetime.utcnow)

    pipeline = relationship("Pipeline", back_populates="workflow_definition")
    runs = relationship("WorkflowRun", back_populates="workflow_definition")


class WorkflowRun(Base):
    __tablename__ = "workflow_runs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    workflow_id = Column(String(36), ForeignKey("workflow_definitions.id"), nullable=False, index=True)
    pipeline_id = Column(String(36), ForeignKey("pipelines.id"), nullable=False, index=True)
    run_number = Column(Integer, nullable=False)
    trigger_type = Column(String(50), default="manual")  # manual, scheduled, retry, azure_logic_app
    status = Column(String(50), default="pending", index=True)  # pending, running, completed, failed, cancelled
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, default=0.0)
    error_message = Column(Text, nullable=True)
    correlation_id = Column(String(64), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    pipeline = relationship("Pipeline", back_populates="runs")
    workflow_definition = relationship("WorkflowDefinition", back_populates="runs")
    steps = relationship("WorkflowStep", back_populates="run", cascade="all, delete-orphan")
    ingestion_batches = relationship("IngestionBatch", back_populates="workflow_run")
    transformation_runs = relationship("TransformationRun", back_populates="workflow_run")
    data_quality_results = relationship("DataQualityResult", back_populates="workflow_run")
    rejected_records = relationship("RejectedRecord", back_populates="workflow_run")
    delivery_attempts = relationship("DeliveryAttempt", back_populates="workflow_run")
    incidents = relationship("Incident", back_populates="workflow_run")


class WorkflowStep(Base):
    __tablename__ = "workflow_steps"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    workflow_run_id = Column(String(36), ForeignKey("workflow_runs.id"), nullable=False, index=True)
    step_name = Column(String(100), nullable=False)
    step_order = Column(Integer, nullable=False)
    status = Column(String(50), default="pending", index=True)  # pending, running, completed, failed, skipped
    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, default=0.0)
    retry_count = Column(Integer, default=0)
    logs = Column(Text, default="")
    error_details = Column(Text, nullable=True)
    output_data = Column(JSON, default=dict)

    run = relationship("WorkflowRun", back_populates="steps")


class IngestionBatch(Base):
    __tablename__ = "ingestion_batches"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    pipeline_id = Column(String(36), ForeignKey("pipelines.id"), nullable=False, index=True)
    workflow_run_id = Column(String(36), ForeignKey("workflow_runs.id", ondelete="CASCADE"), nullable=True, index=True)
    batch_number = Column(String(100), nullable=False, index=True)
    status = Column(String(50), default="in_progress")  # in_progress, completed, failed
    total_records = Column(Integer, default=0)
    source_type = Column(String(50), nullable=False)
    checkpoint_val = Column(String(100), nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    workflow_run = relationship("WorkflowRun", back_populates="ingestion_batches")
    source_records = relationship("SourceRecord", back_populates="batch", cascade="all, delete-orphan")


class SourceRecord(Base):
    __tablename__ = "source_records"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    batch_id = Column(String(36), ForeignKey("ingestion_batches.id"), nullable=False, index=True)
    raw_payload = Column(JSON, nullable=False)
    record_checksum = Column(String(64), nullable=False, index=True)
    business_key = Column(String(150), nullable=True, index=True)
    ingested_at = Column(DateTime, default=datetime.utcnow)

    batch = relationship("IngestionBatch", back_populates="source_records")


class TransformationRun(Base):
    __tablename__ = "transformation_runs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    workflow_run_id = Column(String(36), ForeignKey("workflow_runs.id", ondelete="CASCADE"), nullable=True, index=True)
    batch_id = Column(String(36), nullable=False)
    total_input = Column(Integer, default=0)
    total_transformed = Column(Integer, default=0)
    total_rejected = Column(Integer, default=0)
    status = Column(String(50), default="completed")
    executed_at = Column(DateTime, default=datetime.utcnow)

    workflow_run = relationship("WorkflowRun", back_populates="transformation_runs")


class DataQualityResult(Base):
    __tablename__ = "data_quality_results"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    workflow_run_id = Column(String(36), ForeignKey("workflow_runs.id", ondelete="CASCADE"), nullable=True, index=True)
    batch_id = Column(String(36), nullable=False)
    total_records = Column(Integer, default=0)
    valid_records = Column(Integer, default=0)
    rejected_records = Column(Integer, default=0)
    rules_triggered = Column(JSON, default=list)
    reconciliation_status = Column(String(50), default="passed")  # passed, warning, failed
    checked_at = Column(DateTime, default=datetime.utcnow)

    workflow_run = relationship("WorkflowRun", back_populates="data_quality_results")


class RejectedRecord(Base):
    __tablename__ = "rejected_records"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    workflow_run_id = Column(String(36), ForeignKey("workflow_runs.id", ondelete="CASCADE"), nullable=True, index=True)
    batch_id = Column(String(36), nullable=False)
    record_identifier = Column(String(150), nullable=True, index=True)
    raw_data = Column(JSON, nullable=False)
    rejection_reason = Column(Text, nullable=False)
    rule_violated = Column(String(100), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    workflow_run = relationship("WorkflowRun", back_populates="rejected_records")


class DeliveryAttempt(Base):
    __tablename__ = "delivery_attempts"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    workflow_run_id = Column(String(36), ForeignKey("workflow_runs.id", ondelete="CASCADE"), nullable=True, index=True)
    destination_id = Column(String(36), nullable=False)
    payload_hash = Column(String(64), nullable=False)
    attempt_number = Column(Integer, default=1)
    http_status = Column(Integer, nullable=True)
    response_body = Column(Text, nullable=True)
    status = Column(String(50), default="success")  # success, retried, failed
    created_at = Column(DateTime, default=datetime.utcnow)

    workflow_run = relationship("WorkflowRun", back_populates="delivery_attempts")


class Incident(Base):
    __tablename__ = "incidents"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    workflow_run_id = Column(String(36), ForeignKey("workflow_runs.id", ondelete="CASCADE"), nullable=True, index=True)
    pipeline_id = Column(String(36), ForeignKey("pipelines.id"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    severity = Column(String(50), default="medium")  # low, medium, high, critical
    status = Column(String(50), default="open", index=True)  # open, investigating, resolved
    root_cause = Column(Text, nullable=True)
    resolution_notes = Column(Text, nullable=True)
    reported_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)

    workflow_run = relationship("WorkflowRun", back_populates="incidents")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    action = Column(String(100), nullable=False, index=True)
    resource_type = Column(String(100), nullable=False)
    resource_id = Column(String(100), nullable=True)
    details = Column(JSON, default=dict)
    ip_address = Column(String(50), default="127.0.0.1")
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    user = relationship("User", back_populates="audit_logs")


class Schedule(Base):
    __tablename__ = "schedules"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    pipeline_id = Column(String(36), ForeignKey("pipelines.id"), nullable=False, index=True)
    cron_expression = Column(String(100), nullable=False)
    next_run_at = Column(DateTime, nullable=True)
    last_run_at = Column(DateTime, nullable=True)
    is_enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    pipeline = relationship("Pipeline", back_populates="schedules")


# --- Warehouse Tables ---

class WarehouseOrder(Base):
    __tablename__ = "wh_orders"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    order_id = Column(String(100), unique=True, nullable=False, index=True)
    customer_id = Column(String(100), nullable=False, index=True)
    store_id = Column(String(50), nullable=False, index=True)
    order_date = Column(DateTime, nullable=False)
    currency = Column(String(10), default="USD")
    original_amount = Column(Float, nullable=False)
    normalized_usd_amount = Column(Float, nullable=False)
    item_count = Column(Integer, default=1)
    status = Column(String(50), default="completed")
    created_at = Column(DateTime, default=datetime.utcnow)


class WarehouseOrderItem(Base):
    __tablename__ = "wh_order_items"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    order_id = Column(String(100), ForeignKey("wh_orders.order_id"), nullable=False, index=True)
    product_id = Column(String(100), nullable=False, index=True)
    sku = Column(String(100), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)
    total_price = Column(Float, nullable=False)
    discount_pct = Column(Float, default=0.0)


class WarehouseProduct(Base):
    __tablename__ = "wh_products"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    product_id = Column(String(100), unique=True, nullable=False, index=True)
    sku = Column(String(100), unique=True, nullable=False)
    name = Column(String(200), nullable=False)
    category = Column(String(100), nullable=False)
    standard_cost = Column(Float, nullable=False)
    retail_price = Column(Float, nullable=False)


class WarehouseInventory(Base):
    __tablename__ = "wh_inventory"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    store_id = Column(String(50), nullable=False, index=True)
    product_id = Column(String(100), nullable=False, index=True)
    stock_on_hand = Column(Integer, default=0)
    reserved_qty = Column(Integer, default=0)
    reorder_point = Column(Integer, default=10)
    last_updated = Column(DateTime, default=datetime.utcnow)


class WarehouseSupplier(Base):
    __tablename__ = "wh_suppliers"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    supplier_id = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    contact_email = Column(String(150), nullable=False)
    rating = Column(Float, default=5.0)
    fulfillment_sla_days = Column(Integer, default=3)


# --- Analytics Marts ---

class MartSales(Base):
    __tablename__ = "mart_sales"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    date = Column(DateTime, nullable=False, index=True)
    store_id = Column(String(50), nullable=False, index=True)
    category = Column(String(100), nullable=False)
    total_revenue_usd = Column(Float, default=0.0)
    total_orders = Column(Integer, default=0)
    average_order_value = Column(Float, default=0.0)
    updated_at = Column(DateTime, default=datetime.utcnow)


class MartInventory(Base):
    __tablename__ = "mart_inventory"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    store_id = Column(String(50), nullable=False, index=True)
    product_id = Column(String(100), nullable=False)
    product_name = Column(String(200), nullable=False)
    stock_level_status = Column(String(50), default="optimal")  # critical, low, optimal, surplus
    available_stock = Column(Integer, default=0)
    reorder_needed = Column(Boolean, default=False)
    updated_at = Column(DateTime, default=datetime.utcnow)


class MartSupplierPerformance(Base):
    __tablename__ = "mart_supplier_performance"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    supplier_id = Column(String(100), nullable=False, index=True)
    supplier_name = Column(String(200), nullable=False)
    on_time_delivery_rate = Column(Float, default=98.5)
    defect_rate_pct = Column(Float, default=0.5)
    overall_health_score = Column(Float, default=95.0)
    updated_at = Column(DateTime, default=datetime.utcnow)
