from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.schemas.job import Job, JobCreate, JobUpdate
from app.service.auth import require_admin
from app.service.job import JobService


router = APIRouter()
service = JobService()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/jobs", response_model=list[Job])
def get_all_jobs(db: Session = Depends(get_db)):
    return service.get_all_jobs(db)

@router.post("/jobs", response_model=Job)
def create_job(
    job: JobCreate,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    return service.create_job(db, job)

@router.put("/jobs/{job_id}", response_model=Job)
def update_job(
    job_id: int,
    job: JobUpdate,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    return service.update_job(db, job_id, job)

@router.delete("/jobs/{job_id}", response_model=Job)
def delete_job(
    job_id: int,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    return service.delete_job(db, job_id)

@router.get("/jobs/{job_id}", response_model=Job)
def get_job_by_id(job_id: int, db: Session = Depends(get_db)):
    return service.get_job_by_id(db, job_id)
