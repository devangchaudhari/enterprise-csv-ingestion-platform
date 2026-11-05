from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.api.deps import get_db
from backend.app.models.schema_models import SnowflakeConfig
from backend.app.schemas.ingestion_schemas import SnowflakeConfigSchema
from backend.app.services.snowflake_engine import SnowflakeEngine

router = APIRouter(prefix="/snowflake", tags=["Snowflake Connection"])

@router.get("/config", response_model=SnowflakeConfigSchema)
def get_snowflake_config(db: Session = Depends(get_db)):
    cfg = db.query(SnowflakeConfig).first()
    if not cfg:
        cfg = SnowflakeConfig(
            account="",
            user="",
            warehouse="COMPUTE_WH",
            database="ENTERPRISE_DW",
            schema_name="PUBLIC",
            role="ACCOUNTADMIN",
            is_active=False,
            is_connected=False,
            connection_message="Local Warehouse Mode active"
        )
        db.add(cfg)
        db.commit()
        db.refresh(cfg)

    return SnowflakeConfigSchema(
        account=cfg.account or "",
        user=cfg.user or "",
        password="***" if cfg.password else "",
        warehouse=cfg.warehouse,
        database=cfg.database,
        schema_name=cfg.schema_name,
        role=cfg.role,
        is_active=cfg.is_active,
        is_connected=cfg.is_connected,
        connection_message=cfg.connection_message
    )

@router.post("/config", response_model=SnowflakeConfigSchema)
def save_snowflake_config(cfg_in: SnowflakeConfigSchema, db: Session = Depends(get_db)):
    cfg = db.query(SnowflakeConfig).first()
    if not cfg:
        cfg = SnowflakeConfig()
        db.add(cfg)

    cfg.account = cfg_in.account
    cfg.user = cfg_in.user
    if cfg_in.password and cfg_in.password != "***":
        cfg.password = cfg_in.password
    cfg.warehouse = cfg_in.warehouse
    cfg.database = cfg_in.database
    cfg.schema_name = cfg_in.schema_name
    cfg.role = cfg_in.role
    cfg.is_active = cfg_in.is_active

    db.commit()
    db.refresh(cfg)

    # Test
    is_cloud, msg = SnowflakeEngine.is_cloud_connected()
    cfg.is_connected = is_cloud
    cfg.connection_message = msg
    db.commit()

    return SnowflakeConfigSchema(
        account=cfg.account or "",
        user=cfg.user or "",
        password="***" if cfg.password else "",
        warehouse=cfg.warehouse,
        database=cfg.database,
        schema_name=cfg.schema_name,
        role=cfg.role,
        is_active=cfg.is_active,
        is_connected=cfg.is_connected,
        connection_message=cfg.connection_message
    )

@router.post("/test")
def test_connection():
    is_cloud, msg = SnowflakeEngine.is_cloud_connected()
    return {"is_connected": is_cloud, "message": msg}
