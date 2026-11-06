import sys
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

from fastapi import FastAPI, Depends, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.models.schema import (
    init_db, get_db, Folder, Document, Assignment, Claim, Profile
)
from backend.app.api.auth import router as auth_router
from backend.app.api.folders import router as folders_router
from backend.app.api.documents import router as documents_router
from backend.app.api.assignments import router as assignments_router, resolve_employee_ids
from backend.app.api.ai import router as ai_router
from backend.app.api.tags import router as tags_router
from backend.app.api.claims import router as claims_router
from backend.app.api.masters import router as masters_router
from backend.app.api.activity import router as activity_router

app = FastAPI(
    title="Bill Nexa API",
    description="AI-Powered Document Processing & Claims Automation Platform API",
    version="1.0.0"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount storage directory for static file access
settings.STORAGE_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/storage", StaticFiles(directory=str(settings.STORAGE_DIR)), name="storage")

# Include Routers
app.include_router(auth_router, prefix="/api")
app.include_router(folders_router, prefix="/api")
app.include_router(documents_router, prefix="/api")
app.include_router(assignments_router, prefix="/api")
app.include_router(ai_router, prefix="/api")
app.include_router(tags_router, prefix="/api")
app.include_router(claims_router, prefix="/api")
app.include_router(masters_router, prefix="/api")
app.include_router(activity_router, prefix="/api")

@app.on_event("startup")
def startup_event():
    init_db()

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": f"{type(exc).__name__}: {str(exc)}"}
    )

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "ai_provider": settings.AI_PROVIDER
    }

@app.get("/api/stats")
def get_system_stats(employee_id: str = None, db: Session = Depends(get_db)):
    """
    Returns dashboard KPI metrics for Admin and Employee.
    """
    if employee_id:
        # Employee stats
        target_ids = resolve_employee_ids(db, employee_id)
        emp_assignments = db.query(Assignment).filter(Assignment.employee_id.in_(target_ids)).all()
        total_assigned = len(emp_assignments)
        pending = sum(1 for a in emp_assignments if a.status == "Assigned")
        in_progress = sum(1 for a in emp_assignments if a.status == "In Progress")
        completed = sum(1 for a in emp_assignments if a.status == "Completed")
        returned = sum(1 for a in emp_assignments if a.status == "Pending Review")

        return {
            "total_assigned": total_assigned,
            "pending": pending,
            "in_progress": in_progress,
            "completed": completed,
            "returned": returned
        }
    else:
        # Admin stats
        total_folders = db.query(Folder).count()
        total_docs = db.query(Document).count()
        assignments = db.query(Assignment).all()
        total_assigned = len(assignments)
        unassigned = total_docs - total_assigned
        
        claims = db.query(Claim).all()
        completed_claims = sum(1 for c in claims if c.claim_status == "Submitted")
        review_required = sum(1 for c in claims if "Issue" in c.claim_status or c.claim_status == "Returned")
        pending_assignments = sum(1 for a in assignments if a.status in ["Assigned", "In Progress"])

        return {
            "total_folders": total_folders,
            "total_documents": total_docs,
            "total_assigned": total_assigned,
            "unassigned_documents": unassigned,
            "pending_assignments": pending_assignments,
            "completed_claims": completed_claims,
            "claims_requiring_review": review_required
        }

# Serve frontend build if present (MUST BE LAST ROUTE)
FRONTEND_DIST = ROOT_DIR / "frontend" / "dist"
if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="static-assets")

    from fastapi.responses import FileResponse
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        if full_path.startswith("api/") or full_path.startswith("storage/") or full_path.startswith("docs") or full_path.startswith("openapi.json"):
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="API route not found")
            
        file_path = FRONTEND_DIST / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(FRONTEND_DIST / "index.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
