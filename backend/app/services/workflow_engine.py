import time
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from backend.app.models.all_models import (
    WorkflowRun, WorkflowStep, WorkflowDefinition, Pipeline, AuditLog
)
from backend.app.services.connector_service import ConnectorService
from backend.app.services.ingestion_engine import IngestionEngine
from backend.app.services.data_quality_engine import DataQualityEngine
from backend.app.services.transformation_engine import TransformationEngine
from backend.app.services.warehouse_service import WarehouseService
from backend.app.services.dbt_runner import DbtRunner
from backend.app.services.delivery_service import DeliveryService
from backend.app.services.incident_service import IncidentService

WORKFLOW_STEPS = [
    (1, "Retrieve Source Orders", "Connect to configured data source and ingest raw payloads"),
    (2, "Validate Incoming Records", "Execute enterprise data quality checks and isolate rejected records"),
    (3, "Transform and Normalize Data", "Standardize date/currency, map product SKUs and calculate line item totals"),
    (4, "Load Data into Warehouse", "Persist normalized entities into relational data warehouse tables"),
    (5, "Run dbt Transformations", "Execute staging, intermediate, and analytical mart dbt models"),
    (6, "Deliver Downstream Results", "Deliver validated orders to partner REST API with retry policies"),
    (7, "Generate Execution Summary", "Reconcile audit totals, compute metrics, and seal workflow run")
]

class WorkflowExecutionEngine:
    def __init__(self, db: Session):
        self.db = db
        self.connector_svc = ConnectorService()
        self.ingestion_engine = IngestionEngine(db)
        self.dq_engine = DataQualityEngine(db)
        self.transform_engine = TransformationEngine(db)
        self.wh_service = WarehouseService(db)
        self.dbt_runner = DbtRunner(db)
        self.delivery_svc = DeliveryService(db)
        self.incident_svc = IncidentService(db)

    def execute_workflow(
        self, 
        pipeline_id: str, 
        trigger_type: str = "manual", 
        simulate_failure: Optional[str] = None,
        source_override: Optional[Dict[str, Any]] = None,
        existing_run_id: Optional[str] = None
    ) -> WorkflowRun:
        pipeline = self.db.query(Pipeline).filter(Pipeline.id == pipeline_id).first()
        if not pipeline:
            raise ValueError(f"Pipeline {pipeline_id} not found")

        # Get or create workflow definition
        wf_def = self.db.query(WorkflowDefinition).filter(WorkflowDefinition.pipeline_id == pipeline_id).first()
        if not wf_def:
            wf_def = WorkflowDefinition(
                pipeline_id=pipeline_id,
                name=f"Workflow-{pipeline.name}",
                steps_definition=[{"step": s[0], "name": s[1]} for s in WORKFLOW_STEPS]
            )
            self.db.add(wf_def)
            self.db.commit()
            self.db.refresh(wf_def)

        # Setup Run
        if existing_run_id:
            run = self.db.query(WorkflowRun).filter(WorkflowRun.id == existing_run_id).first()
            run.status = "running"
            run.error_message = None
            run.start_time = datetime.utcnow()
            run.end_time = None
        else:
            run_count = self.db.query(WorkflowRun).filter(WorkflowRun.pipeline_id == pipeline_id).count()
            correlation_id = f"corr-{uuid.uuid4().hex[:16]}"
            run = WorkflowRun(
                workflow_id=wf_def.id,
                pipeline_id=pipeline_id,
                run_number=run_count + 1,
                trigger_type=trigger_type,
                status="running",
                start_time=datetime.utcnow(),
                correlation_id=correlation_id
            )
            self.db.add(run)
            self.db.commit()
            self.db.refresh(run)

            # Create step records
            for order, name, desc in WORKFLOW_STEPS:
                step = WorkflowStep(
                    workflow_run_id=run.id,
                    step_name=name,
                    step_order=order,
                    status="pending"
                )
                self.db.add(step)
            self.db.commit()

        # Step-by-step state dictionary
        context = {
            "raw_records": [],
            "batch_id": None,
            "valid_records": [],
            "rejected_records": [],
            "transformed_orders": [],
            "dq_result": None,
            "wh_result": None,
            "dbt_result": None,
            "delivery_result": None
        }

        steps = self.db.query(WorkflowStep).filter(
            WorkflowStep.workflow_run_id == run.id
        ).order_by(WorkflowStep.step_order).all()

        try:
            for step in steps:
                step.status = "running"
                step.start_time = datetime.utcnow()
                step_start_perf = time.time()
                self.db.commit()

                try:
                    if step.step_order == 1:
                        # Step 1: Ingest
                        if simulate_failure == "sftp_failure":
                            raise ConnectionError("Simulated SFTP timeout during incoming order fetch!")

                        source = pipeline.source
                        src_type = source.type if source else "csv_json"
                        src_cfg = source_override or (source.connection_config if source else {})

                        raw = self.connector_svc.fetch_records(src_type, src_cfg, limit=50)
                        batch = self.ingestion_engine.create_batch(pipeline.id, run.id, src_type)
                        inserted, skipped, _ = self.ingestion_engine.ingest_records(batch.id, raw)
                        context["raw_records"] = raw
                        context["batch_id"] = batch.id
                        step.logs = f"Ingested {inserted} records from {src_type}. Skipped duplicates: {skipped}. Batch ID: {batch.batch_number}"
                        step.output_data = {"batch_id": batch.id, "total_ingested": inserted, "skipped": skipped}

                    elif step.step_order == 2:
                        # Step 2: Validate
                        val_records = context["raw_records"]
                        if simulate_failure == "invalid_data":
                            # Inject invalid payload
                            val_records = [
                                {"order_id": "SIM-ERR-01", "quantity": -5, "unit_price": -20},
                                {"order_id": "SIM-ERR-02", "order_date": "BAD"}
                            ]

                        valid, rejected, dq_res = self.dq_engine.validate_batch(run.id, context["batch_id"], val_records)
                        context["valid_records"] = valid
                        context["rejected_records"] = rejected
                        context["dq_result"] = dq_res
                        step.logs = f"Validation completed: {len(valid)} valid records, {len(rejected)} rejected records. Status: {dq_res.reconciliation_status}"
                        step.output_data = {
                            "valid_count": len(valid),
                            "rejected_count": len(rejected),
                            "rules_triggered": dq_res.rules_triggered
                        }

                        if len(valid) == 0 and len(val_records) > 0:
                            raise ValueError("All records in batch failed data quality validation rules!")

                    elif step.step_order == 3:
                        # Step 3: Transform
                        transformed, t_run = self.transform_engine.transform_orders(
                            run.id, context["batch_id"], context["valid_records"]
                        )
                        context["transformed_orders"] = transformed
                        step.logs = f"Normalized {len(transformed)} orders: dates converted to ISO-8601 UTC, currencies normalized to USD."
                        step.output_data = {"transformed_count": len(transformed)}

                    elif step.step_order == 4:
                        # Step 4: Load Warehouse
                        wh_res = self.wh_service.load_orders(context["transformed_orders"])
                        context["wh_result"] = wh_res
                        step.logs = f"Loaded {wh_res['loaded_orders']} orders and {wh_res['loaded_items']} items into warehouse. {wh_res['snowflake_sync']}"
                        step.output_data = wh_res

                    elif step.step_order == 5:
                        # Step 5: dbt Transformations
                        dbt_res = self.dbt_runner.run_models()
                        context["dbt_result"] = dbt_res
                        step.logs = f"Executed {len(dbt_res['models_executed'])} dbt analytical models ({', '.join(dbt_res['models_executed'])}). Passed {len(dbt_res['tests_passed'])} schema & integrity tests."
                        step.output_data = dbt_res

                    elif step.step_order == 6:
                        # Step 6: Downstream Partner Delivery
                        target_url = pipeline.destination.connection_config.get("url") if pipeline.destination else None
                        del_res = self.delivery_svc.deliver_orders(
                            run.id,
                            pipeline.destination_id,
                            context["transformed_orders"],
                            target_url=target_url,
                            simulate_failure=simulate_failure if simulate_failure == "api_error" else None
                        )
                        context["delivery_result"] = del_res
                        step.logs = f"Dispatched payload to partner API ({del_res['url']}). Final HTTP status: {del_res['final_http_status']} after {del_res['total_attempts']} attempt(s)."
                        step.output_data = del_res

                    elif step.step_order == 7:
                        # Step 7: Summary
                        step.logs = (
                            f"Workflow run {run.run_number} finished with success. "
                            f"Total processed: {len(context['raw_records'])}, "
                            f"Warehouse loaded: {len(context['transformed_orders'])}, "
                            f"Rejected: {len(context['rejected_records'])}."
                        )
                        step.output_data = {
                            "summary": "success",
                            "correlation_id": run.correlation_id,
                            "warehouse_orders": len(context["transformed_orders"]),
                            "rejected_orders": len(context["rejected_records"])
                        }

                    step.status = "completed"
                    step.end_time = datetime.utcnow()
                    step.duration_seconds = round(time.time() - step_start_perf, 3)
                    self.db.commit()

                except Exception as step_err:
                    step.status = "failed"
                    step.end_time = datetime.utcnow()
                    step.duration_seconds = round(time.time() - step_start_perf, 3)
                    step.error_details = str(step_err)
                    step.logs += f"\nERROR: {str(step_err)}"
                    self.db.commit()

                    # Create Incident
                    self.incident_svc.create_incident(
                        workflow_run_id=run.id,
                        pipeline_id=pipeline.id,
                        title=f"Workflow Step Failed: {step.step_name}",
                        root_cause=f"Step {step.step_order} ({step.step_name}) raised: {str(step_err)}",
                        severity="high"
                    )
                    raise step_err

            # Mark run completed
            run.status = "completed"
            run.end_time = datetime.utcnow()
            run.duration_seconds = round((run.end_time - run.start_time).total_seconds(), 2)
            self.db.commit()

        except Exception as run_err:
            run.status = "failed"
            run.end_time = datetime.utcnow()
            run.duration_seconds = round((run.end_time - run.start_time).total_seconds(), 2)
            run.error_message = str(run_err)
            self.db.commit()

        # Audit log entry
        audit = AuditLog(
            user_id=pipeline.owner_id,
            action="EXECUTE_WORKFLOW",
            resource_type="pipeline",
            resource_id=pipeline.id,
            details={
                "run_id": run.id,
                "status": run.status,
                "duration": run.duration_seconds,
                "correlation_id": run.correlation_id
            }
        )
        self.db.add(audit)
        self.db.commit()

        return run
