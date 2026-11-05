import os
from datetime import datetime
from backend.app.core.database import SessionLocal, Base, engine
from backend.app.core.security import get_password_hash
from backend.app.models.all_models import (
    Role, User, DataSource, DataDestination, Pipeline, 
    WarehouseProduct, WarehouseInventory, WarehouseSupplier
)
from backend.app.seeds.sample_data import (
    dump_sample_files, SAMPLE_PRODUCTS, SAMPLE_INVENTORY, SAMPLE_SUPPLIERS
)

def init_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # 1. Seed Roles
    roles_data = [
        ("admin", "Full system administrator access", ["*"]),
        ("data_engineer", "Manage pipelines, mappings, connectors and executions", ["pipeline:write", "connector:write", "workflow:execute"]),
        ("ops_engineer", "Monitor runs, investigate failures and trigger retries", ["workflow:retry", "incident:manage", "logs:read"]),
        ("viewer", "Read-only access to dashboards, executions and reports", ["dashboard:read", "pipeline:read", "workflow:read"])
    ]
    for r_name, r_desc, r_perms in roles_data:
        if not db.query(Role).filter(Role.name == r_name).first():
            db.add(Role(name=r_name, description=r_desc, permissions=r_perms))
    db.commit()

    # 2. Seed Users
    users_data = [
        ("admin@retailhub.enterprise", "System Administrator", "AdminSecret2026!", "admin"),
        ("engineer@retailhub.enterprise", "Lead Data Engineer", "EngineerSecret2026!", "data_engineer"),
        ("ops@retailhub.enterprise", "Site Reliability Engineer", "OpsSecret2026!", "ops_engineer"),
        ("viewer@retailhub.enterprise", "Business Analyst", "ViewerSecret2026!", "viewer")
    ]
    admin_user = None
    for email, name, pwd, role in users_data:
        existing = db.query(User).filter(User.email == email).first()
        if not existing:
            u = User(
                email=email,
                full_name=name,
                hashed_password=get_password_hash(pwd),
                role=role,
                is_active=True
            )
            db.add(u)
            if role == "admin":
                admin_user = u
        elif role == "admin":
            admin_user = existing
    db.commit()

    if not admin_user:
        admin_user = db.query(User).filter(User.email == "admin@retailhub.enterprise").first()

    # 3. Seed Data Sources
    sources_data = [
        ("Retail Sales REST API", "rest_api", {"url": "http://127.0.0.1:8000/api/v1/mock-retail/orders", "auth_type": "bearer", "token": "mock-retail-token-2026"}, "active"),
        ("Store Orders SFTP Drop", "sftp", {"host": "127.0.0.1", "port": 2222, "username": "retail_partner", "root_dir": "./data/samples/sftp_root"}, "active"),
        ("Orders Batch CSV/JSON Feed", "csv_json", {"file_path": "./data/samples/orders.json"}, "active"),
        ("Store DB Replica (PostgreSQL)", "postgres", {"host": "localhost", "port": 5432, "database": "retail_ops"}, "active"),
        ("Snowflake Enterprise Lakehouse", "snowflake", {"account": "RETAIL_CORP", "database": "RETAIL_DW", "warehouse": "COMPUTE_WH"}, "untested")
    ]
    created_sources = {}
    for name, s_type, cfg, status in sources_data:
        src = db.query(DataSource).filter(DataSource.name == name).first()
        if not src:
            src = DataSource(
                name=name,
                type=s_type,
                connection_config=cfg,
                status=status,
                last_tested_at=datetime.utcnow()
            )
            db.add(src)
            db.commit()
            db.refresh(src)
        created_sources[name] = src

    # 4. Seed Data Destinations
    dests_data = [
        ("Downstream Partner Order Delivery API", "rest_api", {"url": "http://127.0.0.1:8000/api/v1/mock-retail/downstream-orders"}, "active"),
        ("Snowflake Production Warehouse", "snowflake", {"account": "RETAIL_CORP", "database": "RETAIL_DW"}, "untested"),
        ("Local Analytics Warehouse", "postgres", {"host": "localhost", "database": "retail_dw"}, "active")
    ]
    created_dests = {}
    for name, d_type, cfg, status in dests_data:
        dst = db.query(DataDestination).filter(DataDestination.name == name).first()
        if not dst:
            dst = DataDestination(
                name=name,
                type=d_type,
                connection_config=cfg,
                status=status,
                last_tested_at=datetime.utcnow()
            )
            db.add(dst)
            db.commit()
            db.refresh(dst)
        created_dests[name] = dst

    # 5. Seed Core Retail Pipelines
    pipelines_data = [
        (
            "OmniRetail POS & Digital Order Ingestion",
            "Continuous ingestion of store POS and digital retail orders, schema validation, currency normalization, and warehouse sync.",
            created_sources["Retail Sales REST API"].id,
            created_dests["Downstream Partner Order Delivery API"].id,
            "0 * * * *"
        ),
        (
            "Daily Inventory Replenishment Sync",
            "Ingestion of store inventory levels, safety stock recalculation, and stockout risk alert mart generation.",
            created_sources["Orders Batch CSV/JSON Feed"].id,
            created_dests["Local Analytics Warehouse"].id,
            "0 2 * * *"
        ),
        (
            "Supplier Performance Analytics Pipeline",
            "ETL processing of vendor lead times, fulfillment SLAs, and delivery defect tracking.",
            created_sources["Store Orders SFTP Drop"].id,
            created_dests["Local Analytics Warehouse"].id,
            "0 4 * * *"
        )
    ]
    for p_name, p_desc, src_id, dst_id, cron in pipelines_data:
        p = db.query(Pipeline).filter(Pipeline.name == p_name).first()
        if not p:
            p = Pipeline(
                name=p_name,
                description=p_desc,
                source_id=src_id,
                destination_id=dst_id,
                transformation_config={"normalize_currency": True, "target_currency": "USD", "deduplicate_by": "order_id"},
                schedule_cron=cron,
                status="active",
                owner_id=admin_user.id
            )
            db.add(p)
    db.commit()

    # 6. Seed Sample Files
    dump_sample_files()

    # 7. Seed Warehouse Reference Catalog (Products, Inventory, Suppliers)
    for prod in SAMPLE_PRODUCTS:
        if not db.query(WarehouseProduct).filter(WarehouseProduct.product_id == prod["product_id"]).first():
            db.add(WarehouseProduct(**prod))

    for inv in SAMPLE_INVENTORY:
        if not db.query(WarehouseInventory).filter(
            WarehouseInventory.store_id == inv["store_id"], 
            WarehouseInventory.product_id == inv["product_id"]
        ).first():
            db.add(WarehouseInventory(**inv))

    for sup in SAMPLE_SUPPLIERS:
        if not db.query(WarehouseSupplier).filter(WarehouseSupplier.supplier_id == sup["supplier_id"]).first():
            db.add(WarehouseSupplier(**sup))

    db.commit()
    db.close()
    print("Database seeding completed successfully.")

if __name__ == "__main__":
    init_db()
