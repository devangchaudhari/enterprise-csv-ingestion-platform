import os
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from backend.app.api.deps import get_db
from backend.app.models.schema_models import Folder, UploadedFile
from backend.app.schemas.ingestion_schemas import UploadedFileResponse
from backend.app.services.storage_service import StorageService

router = APIRouter(prefix="/files", tags=["Files"])

@router.get("", response_model=List[UploadedFileResponse])
def list_files(
    folder_id: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(UploadedFile)
    if folder_id:
        query = query.filter(UploadedFile.folder_id == folder_id)
    if status:
        query = query.filter(UploadedFile.status == status)
    return query.order_by(UploadedFile.uploaded_at.desc()).all()

@router.post("/upload", response_model=UploadedFileResponse)
async def upload_file(
    folder_id: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    folder = db.query(Folder).filter(Folder.id == folder_id).first()
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files (.csv) are accepted for ingestion")

    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Uploaded CSV file is empty")

    # Save to physical folder on disk
    file_path = StorageService.save_file(folder.name, file.filename, content)

    # Upsert in database
    uploaded = UploadedFile(
        folder_id=folder.id,
        filename=file.filename,
        file_path=file_path,
        file_size_bytes=len(content),
        status="pending"
    )
    db.add(uploaded)
    db.commit()
    db.refresh(uploaded)

    return uploaded

@router.delete("/{id}")
def delete_file_manually(id: str, db: Session = Depends(get_db)):
    uploaded = db.query(UploadedFile).filter(UploadedFile.id == id).first()
    if not uploaded:
        raise HTTPException(status_code=404, detail="File not found")

    # Remove from physical disk
    StorageService.delete_file(uploaded.file_path)

    db.delete(uploaded)
    db.commit()
    return {"message": f"File '{uploaded.filename}' deleted successfully"}
