from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.api.deps import get_db
from backend.app.models.schema_models import Folder, UploadedFile
from backend.app.schemas.ingestion_schemas import FolderCreate, FolderResponse
from backend.app.services.storage_service import StorageService

router = APIRouter(prefix="/folders", tags=["Folders"])

@router.get("", response_model=List[FolderResponse])
def list_folders(db: Session = Depends(get_db)):
    folders = db.query(Folder).order_by(Folder.name.asc()).all()
    res = []
    for f in folders:
        total_files = db.query(UploadedFile).filter(UploadedFile.folder_id == f.id).count()
        pending_files = db.query(UploadedFile).filter(
            UploadedFile.folder_id == f.id,
            UploadedFile.status.in_(["pending", "failed"])
        ).count()
        res.append(FolderResponse(
            id=f.id,
            name=f.name,
            description=f.description,
            created_at=f.created_at,
            file_count=total_files,
            pending_file_count=pending_files
        ))
    return res

@router.post("", response_model=FolderResponse)
def create_folder(folder_in: FolderCreate, db: Session = Depends(get_db)):
    clean_name = folder_in.name.strip().replace(" ", "_")
    existing = db.query(Folder).filter(Folder.name.ilike(clean_name)).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Folder '{clean_name}' already exists")

    # Create physical folder on disk
    StorageService.get_folder_path(clean_name)

    folder = Folder(name=clean_name, description=folder_in.description)
    db.add(folder)
    db.commit()
    db.refresh(folder)

    return FolderResponse(
        id=folder.id,
        name=folder.name,
        description=folder.description,
        created_at=folder.created_at,
        file_count=0,
        pending_file_count=0
    )

@router.delete("/{id}")
def delete_folder(id: str, db: Session = Depends(get_db)):
    folder = db.query(Folder).filter(Folder.id == id).first()
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    db.delete(folder)
    db.commit()
    return {"message": f"Folder '{folder.name}' deleted successfully"}
