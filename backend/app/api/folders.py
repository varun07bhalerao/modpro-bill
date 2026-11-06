import os
import shutil
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from backend.app.models.schema import get_db, Folder, Document, Assignment, Profile, ActivityLog
from backend.app.schemas.models import FolderResponse, DocumentResponse
from backend.app.core.config import settings
from backend.app.services.pdf_processor.pdf_service import pdf_service
from backend.app.api.auth import get_current_user

router = APIRouter(prefix="/folders", tags=["Folders"])

@router.get("", response_model=List[FolderResponse])
def get_folders(db: Session = Depends(get_db)):
    folders = db.query(Folder).order_by(Folder.created_at.desc()).all()
    results = []
    for f in folders:
        docs = db.query(Document).filter(Document.folder_id == f.id).all()
        doc_ids = [d.id for d in docs]
        assignments = db.query(Assignment).filter(Assignment.document_id.in_(doc_ids)).all() if doc_ids else []
        assigned_doc_ids = set(a.document_id for a in assignments)
        
        assigned_count = len(assigned_doc_ids)
        unassigned_count = len(docs) - assigned_count
        
        doc_responses = []
        for d in docs:
            asg = next((a for a in assignments if a.document_id == d.id), None)
            emp_name = asg.employee.full_name if asg and asg.employee else None
            emp_id = asg.employee_id if asg else None
            status = asg.status if asg else "Unassigned"
            doc_responses.append(DocumentResponse(
                id=d.id,
                folder_id=f.id,
                folder_name=f.folder_name,
                original_filename=d.original_filename,
                storage_path=d.storage_path,
                file_size_bytes=d.file_size_bytes,
                total_pages=d.total_pages,
                uploaded_by=d.uploaded_by,
                created_at=d.created_at,
                assignment_status=status,
                assigned_employee_name=emp_name,
                assigned_employee_id=emp_id
            ))
            
        results.append(FolderResponse(
            id=f.id,
            folder_name=f.folder_name,
            uploaded_by=f.uploaded_by,
            uploader_name=f.uploader.full_name if f.uploader else "Admin",
            total_files=len(docs),
            assigned_count=assigned_count,
            unassigned_count=unassigned_count,
            created_at=f.created_at,
            documents=doc_responses
        ))
    return results

@router.post("/upload")
async def upload_folder(
    folder_name: str = Form(...),
    files: List[UploadFile] = File(...),
    current_user: Profile = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Handles pre-sorted folder upload with multiple PDFs.
    Validates file types, saves each PDF, calculates page counts,
    and records in database.
    """
    clean_folder_name = folder_name.strip()
    if not clean_folder_name:
        raise HTTPException(status_code=400, detail="Folder name is required")
        
    # Check for invalid files
    for file in files:
        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(
                status_code=400, 
                detail=f"File '{file.filename}' is not a valid PDF. Only PDF files are supported."
            )
            
    # Create Folder in DB
    folder = Folder(
        folder_name=clean_folder_name,
        uploaded_by=current_user.id,
        total_files=len(files)
    )
    db.add(folder)
    db.commit()
    db.refresh(folder)

    # Save each PDF
    settings.ORIGINAL_DOCS_DIR.mkdir(parents=True, exist_ok=True)
    created_docs = []
    for file in files:
        original_name = Path(file.filename).name # preserve filename
        stored_filename = f"{folder.id}_{original_name}"
        dest_path = settings.ORIGINAL_DOCS_DIR / stored_filename
        
        with open(dest_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        file_size = dest_path.stat().st_size
        
        # Calculate pages using PyMuPDF
        try:
            pdf_info = pdf_service.get_pdf_info(str(dest_path))
            pages = pdf_info["total_pages"]
        except Exception:
            pages = 1

        doc = Document(
            folder_id=folder.id,
            original_filename=original_name,
            storage_path=f"original-documents/{stored_filename}",
            file_size_bytes=file_size,
            total_pages=pages,
            uploaded_by=current_user.id
        )
        db.add(doc)
        created_docs.append(doc)

    # Log activity
    log = ActivityLog(
        user_id=current_user.id,
        user_name=current_user.full_name,
        action="Folder Uploaded",
        details=f"Uploaded pre-sorted folder '{clean_folder_name}' with {len(files)} PDFs."
    )
    db.add(log)
    db.commit()

    return {
        "message": f"Folder '{clean_folder_name}' uploaded successfully with {len(files)} PDF documents.",
        "folder_id": folder.id,
        "folder_name": folder.folder_name,
        "total_files": len(files)
    }

@router.get("/{folder_id}", response_model=FolderResponse)
def get_folder_by_id(folder_id: str, db: Session = Depends(get_db)):
    folder = db.query(Folder).filter(Folder.id == folder_id).first()
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")
        
    docs = db.query(Document).filter(Document.folder_id == folder.id).all()
    doc_ids = [d.id for d in docs]
    assignments = db.query(Assignment).filter(Assignment.document_id.in_(doc_ids)).all() if doc_ids else []
    assigned_doc_ids = set(a.document_id for a in assignments)
    
    doc_responses = []
    for d in docs:
        asg = next((a for a in assignments if a.document_id == d.id), None)
        emp_name = asg.employee.full_name if asg and asg.employee else None
        emp_id = asg.employee_id if asg else None
        status = asg.status if asg else "Unassigned"
        doc_responses.append(DocumentResponse(
            id=d.id,
            folder_id=folder.id,
            folder_name=folder.folder_name,
            original_filename=d.original_filename,
            storage_path=d.storage_path,
            file_size_bytes=d.file_size_bytes,
            total_pages=d.total_pages,
            uploaded_by=d.uploaded_by,
            created_at=d.created_at,
            assignment_status=status,
            assigned_employee_name=emp_name,
            assigned_employee_id=emp_id
        ))

    return FolderResponse(
        id=folder.id,
        folder_name=folder.folder_name,
        uploaded_by=folder.uploaded_by,
        uploader_name=folder.uploader.full_name if folder.uploader else "Admin",
        total_files=len(docs),
        assigned_count=len(assigned_doc_ids),
        unassigned_count=len(docs) - len(assigned_doc_ids),
        created_at=folder.created_at,
        documents=doc_responses
    )

