from typing import List, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from backend.app.api.deps import get_db, get_current_user, require_role
from backend.app.models.all_models import DataSource, DataDestination, User, AuditLog
from backend.app.schemas.connector_schemas import (
    DataSourceCreate, DataSourceResponse, DataDestinationCreate, 
    DataDestinationResponse, ConnectionTestResult
)
from backend.app.services.connector_service import ConnectorService

router = APIRouter(prefix="/connectors", tags=["Connectors"])

@router.get("/sources", response_model=List[DataSourceResponse])
def list_data_sources(db: Session = Depends(get_db)):
    return db.query(DataSource).order_by(DataSource.created_at.desc()).all()

@router.post("/sources", response_model=DataSourceResponse)
def create_data_source(
    src_in: DataSourceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "data_engineer"]))
):
    src = DataSource(
        name=src_in.name,
        type=src_in.type,
        connection_config=src_in.connection_config,
        credentials_ref=src_in.credentials_ref,
        status="untested"
    )
    db.add(src)
    db.commit()
    db.refresh(src)
    return src

@router.post("/sources/{id}/test", response_model=ConnectionTestResult)
def test_source_connector(id: str, db: Session = Depends(get_db)):
    src = db.query(DataSource).filter(DataSource.id == id).first()
    if not src:
        raise HTTPException(status_code=404, detail="Source connector not found")

    res = ConnectorService.test_source_connection(src.type, src.connection_config)
    src.status = "active" if res.is_connected else "failed"
    src.last_tested_at = datetime.utcnow()
    db.commit()
    return res

@router.post("/sources/test-adhoc", response_model=ConnectionTestResult)
def test_adhoc_source(payload: Dict[str, Any] = Body(...)):
    source_type = payload.get("type", "rest_api")
    config = payload.get("connection_config", {})
    return ConnectorService.test_source_connection(source_type, config)

@router.get("/destinations", response_model=List[DataDestinationResponse])
def list_data_destinations(db: Session = Depends(get_db)):
    return db.query(DataDestination).order_by(DataDestination.created_at.desc()).all()

@router.post("/destinations", response_model=DataDestinationResponse)
def create_data_destination(
    dst_in: DataDestinationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "data_engineer"]))
):
    dst = DataDestination(
        name=dst_in.name,
        type=dst_in.type,
        connection_config=dst_in.connection_config,
        credentials_ref=dst_in.credentials_ref,
        status="untested"
    )
    db.add(dst)
    db.commit()
    db.refresh(dst)
    return dst

@router.post("/destinations/{id}/test", response_model=ConnectionTestResult)
def test_destination_connector(id: str, db: Session = Depends(get_db)):
    dst = db.query(DataDestination).filter(DataDestination.id == id).first()
    if not dst:
        raise HTTPException(status_code=404, detail="Destination connector not found")

    res = ConnectorService.test_source_connection(dst.type, dst.connection_config)
    dst.status = "active" if res.is_connected else "failed"
    dst.last_tested_at = datetime.utcnow()
    db.commit()
    return res
