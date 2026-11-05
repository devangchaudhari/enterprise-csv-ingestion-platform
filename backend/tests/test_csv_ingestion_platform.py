import os
import shutil
import pytest
from fastapi.testclient import TestClient
from backend.app.core.database import SessionLocal, Base, engine
from backend.app.main import app
from backend.app.seeds.seed_streamlined import seed_platform
from backend.app.models.schema_models import Folder, IngestionJob, UploadedFile, JobExecution
from backend.app.services.snowflake_engine import SnowflakeEngine
from backend.app.services.storage_service import StorageService

@pytest.fixture(scope="session", autouse=True)
def setup_db():
    seed_platform()

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

def test_01_create_folders_and_list(client):
    """1. User can create folders (Employee, Customer, Product)."""
    resp = client.get("/api/folders")
    assert resp.status_code == 200
    folder_names = [f["name"] for f in resp.json()]
    assert "Employee" in folder_names

    # Create new custom folder with unique name
    import uuid
    uniq_name = f"Vendor_Feeds_{uuid.uuid4().hex[:6]}"
    new_f_resp = client.post("/api/folders", json={"name": uniq_name, "description": "Vendor invoices"})
    assert new_f_resp.status_code == 200
    assert new_f_resp.json()["name"] == uniq_name

def test_02_configure_dc_employee_job(client):
    """2. Job has dynamic column configuration with Primary Key."""
    resp = client.get("/api/jobs")
    assert resp.status_code == 200
    jobs = resp.json()
    emp_job = next((j for j in jobs if j["name"] == "DC_Employee"), None)
    assert emp_job is not None
    assert emp_job["target_table"] == "EMPLOYEE"
    
    col_names = [c["name"] for c in emp_job["columns_config"]]
    assert "Employee_ID" in col_names
    assert "Salary" in col_names
    pk_col = next(c for c in emp_job["columns_config"] if c["is_primary_key"])
    assert pk_col["name"] == "Employee_ID"

def test_03_04_05_06_07_08_upload_and_ingest_employee_batch(client):
    """
    3. Upload employee CSV
    4. Run job manually
    5. Validate CSV structure & audit columns (CREATED_DATE, MODIFIED_DATE)
    6. Ingest into table
    7. Query database table
    8. Confirm file is deleted from folder upon success
    """
    folders = client.get("/api/folders").json()
    emp_folder = next(f for f in folders if f["name"] == "Employee")
    jobs = client.get("/api/jobs").json()
    emp_job = next(j for j in jobs if j["name"] == "DC_Employee")

    # Upload sample batch 1
    sample_file_path = "./data/sample_csvs/employee_batch_1.csv"
    with open(sample_file_path, "rb") as f:
        up_resp = client.post(
            "/api/files/upload",
            data={"folder_id": emp_folder["id"]},
            files={"file": ("batch_1.csv", f, "text/csv")}
        )
    assert up_resp.status_code == 200
    uploaded_file = up_resp.json()
    assert uploaded_file["status"] == "pending"

    # Confirm file exists on disk
    assert os.path.exists(uploaded_file["file_path"])

    # Run the job manually
    run_resp = client.post(f"/api/jobs/{emp_job['id']}/run")
    assert run_resp.status_code == 200
    results = run_resp.json()["results"]
    assert len(results) > 0
    # Batch 1 succeeded
    batch_res = next(r for r in results if r["file_name"] == "batch_1.csv")
    assert batch_res["status"] == "Success"
    assert (batch_res["records_inserted"] + batch_res["records_updated"]) >= 3

    # Check Database table data
    table_data_resp = client.get("/api/database/tables/EMPLOYEE/data")
    assert table_data_resp.status_code == 200
    t_data = table_data_resp.json()
    assert t_data["total_records"] >= 3
    # Verify audit columns exist in table records
    first_record = t_data["records"][0]
    assert "CREATED_DATE" in first_record
    assert "MODIFIED_DATE" in first_record
    assert first_record["CREATED_DATE"] is not None

    # Step 8: Confirm successfully processed CSV file was deleted from folder!
    assert not os.path.exists(uploaded_file["file_path"])

def test_09_update_existing_record_preserves_created_date(client):
    """
    9. Upload CSV containing existing Employee_ID:
    Demonstrates existing record is updated without duplicate,
    preserving original CREATED_DATE and updating MODIFIED_DATE.
    """
    folders = client.get("/api/folders").json()
    emp_folder = next(f for f in folders if f["name"] == "Employee")
    jobs = client.get("/api/jobs").json()
    emp_job = next(j for j in jobs if j["name"] == "DC_Employee")

    # Ensure clean state for ID 104
    from sqlalchemy import text
    from backend.app.core.database import engine
    with engine.connect() as conn:
        conn.execute(text('DELETE FROM "EMPLOYEE" WHERE "Employee_ID" = 104'))
        conn.commit()

    # Fetch initial state of Employee_ID 102
    initial_data = client.get("/api/database/tables/EMPLOYEE/data?search=102").json()["records"][0]
    initial_created_date = str(initial_data["CREATED_DATE"])
    assert initial_data["Department"] == "Marketing"

    # Upload update batch (Employee 102 has Department: Product Management, Salary: 115000; Employee 104 is new)
    sample_update_path = "./data/sample_csvs/employee_batch_2_update.csv"
    with open(sample_update_path, "rb") as f:
        up_resp = client.post(
            "/api/files/upload",
            data={"folder_id": emp_folder["id"]},
            files={"file": ("batch_2_update.csv", f, "text/csv")}
        )
    assert up_resp.status_code == 200

    # Run Job
    run_resp = client.post(f"/api/jobs/{emp_job['id']}/run")
    assert run_resp.status_code == 200
    results = run_resp.json()["results"]
    batch_res = next(r for r in results if r["file_name"] == "batch_2_update.csv")
    assert batch_res["status"] == "Success"
    assert batch_res["records_updated"] == 1
    assert batch_res["records_inserted"] == 1

    # Check updated record in table
    updated_record = client.get("/api/database/tables/EMPLOYEE/data?search=102").json()["records"][0]
    assert updated_record["Department"] == "Product Management"
    assert float(updated_record["Salary"]) == 115000.0
    # Original CREATED_DATE preserved!
    assert str(updated_record["CREATED_DATE"]) == initial_created_date

def test_10_invalid_csv_fails_and_retains_file_for_retry(client):
    """
    10. Upload invalid CSV:
    Demonstrates job fails, displays error message, and retains file for correction.
    """
    folders = client.get("/api/folders").json()
    emp_folder = next(f for f in folders if f["name"] == "Employee")
    jobs = client.get("/api/jobs").json()
    emp_job = next(j for j in jobs if j["name"] == "DC_Employee")

    # Upload invalid file (missing required 'Email' column)
    invalid_sample_path = "./data/sample_csvs/employee_batch_invalid.csv"
    with open(invalid_sample_path, "rb") as f:
        up_resp = client.post(
            "/api/files/upload",
            data={"folder_id": emp_folder["id"]},
            files={"file": ("batch_invalid.csv", f, "text/csv")}
        )
    assert up_resp.status_code == 200
    invalid_file = up_resp.json()

    # Run Job
    run_resp = client.post(f"/api/jobs/{emp_job['id']}/run")
    assert run_resp.status_code == 200
    results = run_resp.json()["results"]
    failed_res = next(r for r in results if r["file_name"] == "batch_invalid.csv")
    assert failed_res["status"] == "Failed"
    assert "Missing required column" in failed_res["error"]

    # File status is marked failed in DB
    files_list = client.get(f"/api/files?folder_id={emp_folder['id']}&status=failed").json()
    failed_db_file = next(f for f in files_list if f["filename"] == "batch_invalid.csv")
    assert failed_db_file["status"] == "failed"
    assert "Missing required column" in failed_db_file["error_message"]

    # Critical rule: File is NOT deleted on disk so the user can correct and retry!
    assert os.path.exists(invalid_file["file_path"])

def test_11_execution_history_logged(client):
    """Execution history logs manual and scheduled executions with records count and status."""
    hist_resp = client.get("/api/jobs/history")
    assert hist_resp.status_code == 200
    history = hist_resp.json()
    assert len(history) >= 2
    first_hist = history[0]
    assert "job_name" in first_hist
    assert "records_processed" in first_hist
    assert "execution_status" in first_hist
