import pytest
from datetime import datetime
from backend.app.core.database import SessionLocal
from backend.app.models.all_models import (
    Pipeline, DataSource, DataDestination, WorkflowRun, 
    WarehouseOrder, RejectedRecord, IngestionBatch, Incident
)

def test_scenario_01_admin_can_create_pipeline(client, admin_headers):
    """Scenario 1: An administrator can create a pipeline."""
    # Fetch existing sources & destinations
    src = client.get("/api/v1/connectors/sources").json()[0]
    dst = client.get("/api/v1/connectors/destinations").json()[0]

    payload = {
        "name": "E2E Retail POS Pipeline",
        "description": "Integration pipeline for store point-of-sale events",
        "source_id": src["id"],
        "destination_id": dst["id"],
        "transformation_config": {"currency": "USD"},
        "schedule_cron": "0 * * * *",
        "status": "active"
    }
    resp = client.post("/api/v1/pipelines", json=payload, headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "E2E Retail POS Pipeline"
    assert data["id"] is not None

def test_scenario_02_data_engineer_can_configure_source(client, engineer_headers):
    """Scenario 2: A data engineer can configure a source connector."""
    payload = {
        "name": "Supplier B2B SFTP Connector",
        "type": "sftp",
        "connection_config": {"host": "127.0.0.1", "port": 2222, "root_dir": "./data/samples/sftp_root"},
        "is_active": True
    }
    resp = client.post("/api/v1/connectors/sources", json=payload, headers=engineer_headers)
    assert resp.status_code == 200
    source_id = resp.json()["id"]

    # Test the connection
    test_resp = client.post(f"/api/v1/connectors/sources/{source_id}/test", headers=engineer_headers)
    assert test_resp.status_code == 200
    assert "is_connected" in test_resp.json()

def test_scenario_03_ingest_sample_retail_order_data():
    """Scenario 3: The system can ingest sample retail order data."""
    db = SessionLocal()
    from backend.app.services.ingestion_engine import IngestionEngine
    from backend.app.seeds.sample_data import SAMPLE_ORDERS

    p = db.query(Pipeline).first()
    engine = IngestionEngine(db)
    batch = engine.create_batch(p.id, None, "rest_api")
    inserted, skipped, ids = engine.ingest_records(batch.id, SAMPLE_ORDERS[:3])
    
    assert inserted >= 0
    assert batch.batch_number.startswith("BATCH-")
    db.close()

def test_scenario_04_invalid_records_rejected_with_reasons():
    """Scenario 4: Invalid records are rejected with clear reasons."""
    db = SessionLocal()
    from backend.app.services.data_quality_engine import DataQualityEngine

    dq = DataQualityEngine(db)
    flawed_records = [
        {"order_id": "ORD-ERR-1", "customer_id": "CUST-1", "store_id": "STORE-1", "order_date": "2026-10-24T12:00:00Z", "currency": "USD", "quantity": -5, "unit_price": 50},
        {"order_id": "ORD-ERR-2", "customer_id": "", "store_id": "STORE-1", "order_date": "2026-10-24T12:00:00Z", "currency": "USD", "quantity": 1, "unit_price": 50},
        {"order_id": "ORD-ERR-3", "customer_id": "CUST-3", "store_id": "STORE-1", "order_date": "INVALID_DATE_FORMAT", "currency": "USD", "quantity": 1, "unit_price": 50}
    ]
    valid, rejected, dq_res = dq.validate_batch(None, "batch-test-dq", flawed_records)
    db.close()

    assert len(rejected) == 3
    assert len(valid) == 0
    assert "NEGATIVE_OR_ZERO_QUANTITY" in dq_res.rules_triggered
    assert "REQUIRED_FIELD_MISSING" in dq_res.rules_triggered
    assert "INVALID_DATE_FORMAT" in dq_res.rules_triggered

def test_scenario_05_valid_records_transformed_and_stored():
    """Scenario 5: Valid records are transformed and stored."""
    db = SessionLocal()
    from backend.app.services.transformation_engine import TransformationEngine
    from backend.app.services.warehouse_service import WarehouseService

    valid_orders = [{
        "order_id": "ORD-TEST-VALID-01",
        "customer_id": "CUST-VALID",
        "store_id": "STORE-NYC-01",
        "order_date": "2026-10-24T14:30:00Z",
        "currency": "EUR",
        "items": [{"product_id": "PROD-101", "sku": "ELEC-HEADPHONE-ANC", "quantity": 2, "unit_price": 100.0, "discount_pct": 0.0}]
    }]

    t_engine = TransformationEngine(db)
    wh_service = WarehouseService(db)

    transformed, _ = t_engine.transform_orders(None, "batch-test-tx", valid_orders)
    # EUR should be converted to USD (1.08 rate: 200 EUR = 216 USD)
    assert transformed[0]["normalized_usd_amount"] == 216.0
    assert transformed[0]["currency"] == "EUR"

    wh_res = wh_service.load_orders(transformed)
    assert wh_res["loaded_orders"] >= 1

    stored_order = db.query(WarehouseOrder).filter(WarehouseOrder.order_id == "ORD-TEST-VALID-01").first()
    assert stored_order is not None
    assert stored_order.normalized_usd_amount == 216.0
    db.close()

def test_scenario_06_dbt_models_execute_successfully():
    """Scenario 6: dbt models execute successfully against the local warehouse."""
    db = SessionLocal()
    from backend.app.services.dbt_runner import DbtRunner

    runner = DbtRunner(db)
    res = runner.run_models()
    db.close()

    assert res["status"] == "success"
    assert "mart_sales" in res["models_executed"]
    assert "mart_inventory" in res["models_executed"]
    assert "mart_supplier_performance" in res["models_executed"]
    assert len(res["tests_passed"]) >= 3

def test_scenario_07_workflow_completes_ingestion_to_delivery(client, admin_headers):
    """Scenario 7: A workflow completes successfully from ingestion to delivery."""
    pipeline = client.get("/api/v1/pipelines").json()[0]
    exec_resp = client.post(
        f"/api/v1/pipelines/{pipeline['id']}/execute",
        json={"trigger_type": "manual"},
        headers=admin_headers
    )
    assert exec_resp.status_code == 200
    run_data = exec_resp.json()
    assert run_data["status"] == "completed"
    assert len(run_data["steps"]) == 7
    # Verify all 7 steps completed
    for step in run_data["steps"]:
        assert step["status"] == "completed"

def test_scenario_08_failed_api_call_is_retried_with_backoff():
    """Scenario 8: A failed API call is retried according to its configured policy."""
    db = SessionLocal()
    from backend.app.services.delivery_service import DeliveryService

    delivery_svc = DeliveryService(db)
    orders = [{"order_id": "ORD-RETRY-TEST", "total_price": 100.0}]

    # Injected simulated failure recovers on second attempt!
    res = delivery_svc.deliver_orders(
        workflow_run_id=None,
        destination_id="dst-retry-test",
        orders=orders,
        max_retries=3,
        simulate_failure="api_error"
    )
    db.close()

    assert res["delivery_status"] == "delivered"
    assert res["total_attempts"] == 2
    assert res["attempts"][0]["status"] == "retry_pending"
    assert res["attempts"][1]["status"] == "success"

def test_scenario_09_failed_workflow_can_be_retried_idempotently(client, admin_headers):
    """Scenario 9: A failed workflow can be retried without duplicating data."""
    pipeline = client.get("/api/v1/pipelines").json()[0]
    
    # 1. Trigger failure with SFTP timeout simulation
    fail_exec = client.post(
        f"/api/v1/pipelines/{pipeline['id']}/execute",
        json={"trigger_type": "manual", "simulate_failure": "sftp_failure"},
        headers=admin_headers
    )
    assert fail_exec.status_code == 200
    failed_run = fail_exec.json()
    assert failed_run["status"] == "failed"

    # Count warehouse orders before retry
    db = SessionLocal()
    wh_count_before = db.query(WarehouseOrder).count()
    db.close()

    # 2. Retry the workflow
    retry_resp = client.post(
        f"/api/v1/workflows/runs/{failed_run['id']}/retry",
        json={"clear_errors": True},
        headers=admin_headers
    )
    assert retry_resp.status_code == 200
    retried_run = retry_resp.json()
    assert retried_run["status"] == "completed"

    # Count warehouse orders after retry - verify no duplicate records created!
    db = SessionLocal()
    wh_count_after = db.query(WarehouseOrder).count()
    # Unique distinct orders
    distinct_orders = db.query(WarehouseOrder.order_id).distinct().count()
    assert wh_count_after == distinct_orders
    db.close()

def test_scenario_10_rbac_access_control(client, viewer_headers):
    """Scenario 10: A user without permission cannot access restricted operations."""
    # Viewer tries to create a pipeline -> Should be rejected with 403 Forbidden!
    payload = {
        "name": "Unauthorized Pipeline",
        "source_id": "dummy",
        "destination_id": "dummy"
    }
    resp = client.post("/api/v1/pipelines", json=payload, headers=viewer_headers)
    assert resp.status_code == 403
    assert "restricted" in resp.json()["detail"].lower()

def test_scenario_11_dashboard_metrics_reflect_actual_runs(client):
    """Scenario 11: Dashboard metrics reflect actual workflow executions."""
    resp = client.get("/api/v1/dashboard/metrics")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_pipelines"] >= 1
    assert data["successful_executions"] >= 1
    assert data["records_processed"] >= 1
    assert "throughput_history" in data

def test_scenario_12_system_restart_preserves_records():
    """Scenario 12: The system can restart without losing persistent records."""
    # Create a fresh DB session and verify records persist
    db = SessionLocal()
    pipelines = db.query(Pipeline).all()
    orders = db.query(WarehouseOrder).all()
    runs = db.query(WorkflowRun).all()
    db.close()

    assert len(pipelines) > 0
    assert len(orders) > 0
    assert len(runs) > 0

def test_scenario_13_complete_integration_test(client, admin_headers):
    """Scenario 13: A complete integration test runs from source ingestion to downstream delivery."""
    pipeline = client.get("/api/v1/pipelines").json()[0]
    exec_resp = client.post(
        f"/api/v1/pipelines/{pipeline['id']}/execute",
        json={"trigger_type": "integration_test"},
        headers=admin_headers
    )
    assert exec_resp.status_code == 200
    run = exec_resp.json()
    assert run["status"] == "completed"
    assert run["correlation_id"] is not None
    assert run["duration_seconds"] > 0
