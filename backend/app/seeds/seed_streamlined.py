import os
import shutil
from backend.app.core.database import SessionLocal, Base, engine
from backend.app.models.schema_models import Folder, IngestionJob, UploadedFile, SnowflakeConfig
from backend.app.services.storage_service import StorageService
from backend.app.services.snowflake_engine import SnowflakeEngine

def seed_platform():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # 1. Folders
    folders_data = [
        ("Employee", "Employee personal, department, and salary CSV drops"),
        ("Customer", "Customer CRM profiles and contact master records"),
        ("Product", "Retail SKU catalog, pricing, and category feeds")
    ]

    folder_map = {}
    for name, desc in folders_data:
        StorageService.get_folder_path(name)
        f = db.query(Folder).filter(Folder.name == name).first()
        if not f:
            f = Folder(name=name, description=desc)
            db.add(f)
            db.commit()
            db.refresh(f)
        folder_map[name] = f

    # 2. Ingestion Jobs: DC_Employee
    dc_emp_cols = [
        {"name": "Employee_ID", "type": "Integer", "is_primary_key": True, "is_required": True},
        {"name": "Employee_Name", "type": "String", "is_primary_key": False, "is_required": True},
        {"name": "Department", "type": "String", "is_primary_key": False, "is_required": True},
        {"name": "Email", "type": "String", "is_primary_key": False, "is_required": True},
        {"name": "Salary", "type": "Float", "is_primary_key": False, "is_required": True}
    ]

    emp_job = db.query(IngestionJob).filter(IngestionJob.name == "DC_Employee").first()
    if not emp_job:
        emp_job = IngestionJob(
            name="DC_Employee",
            folder_id=folder_map["Employee"].id,
            target_table="EMPLOYEE",
            is_active=True,
            schedule_type="manual",
            columns_config=dc_emp_cols
        )
        db.add(emp_job)
        db.commit()
        db.refresh(emp_job)

    # Pre-create the Snowflake / Local DW table
    SnowflakeEngine.ensure_table("EMPLOYEE", dc_emp_cols, "Employee_ID")

    # 3. Stage initial sample file in Employee folder
    sample_src = "./data/sample_csvs/employee_batch_1.csv"
    if os.path.exists(sample_src):
        dest_path = os.path.join(StorageService.get_folder_path("Employee"), "employees_initial.csv")
        shutil.copyfile(sample_src, dest_path)
        
        # Check if already in DB
        existing_file = db.query(UploadedFile).filter(
            UploadedFile.folder_id == folder_map["Employee"].id,
            UploadedFile.filename == "employees_initial.csv"
        ).first()
        if not existing_file:
            db.add(UploadedFile(
                folder_id=folder_map["Employee"].id,
                filename="employees_initial.csv",
                file_path=dest_path,
                file_size_bytes=os.path.getsize(dest_path),
                status="pending"
            ))
            db.commit()

    db.close()
    print("Streamlined CSV Ingestion Platform seeded successfully.")

if __name__ == "__main__":
    seed_platform()
