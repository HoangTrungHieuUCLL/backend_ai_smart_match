from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import SavedJob, Profile

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/profiles/{profile_id}/saved-jobs/{job_id}")
def save_job(profile_id: int, job_id: int, db: Session = Depends(get_db)):
    existing = db.query(SavedJob).filter_by(
        profile_id=profile_id,
        job_id=job_id
    ).first()

    if existing:
        return {"message": "Already saved"}

    db.add(SavedJob(profile_id=profile_id, job_id=job_id))
    db.commit()

    return {"message": "Job saved"}


@router.delete("/profiles/{profile_id}/saved-jobs/{job_id}")
def remove_job(profile_id: int, job_id: int, db: Session = Depends(get_db)):
    db.query(SavedJob).filter_by(
        profile_id=profile_id,
        job_id=job_id
    ).delete()

    db.commit()

    return {"message": "Job removed"}


@router.get("/profiles/{profile_id}/saved-jobs")
def get_saved_jobs(profile_id: int, db: Session = Depends(get_db)):
    rows = db.query(SavedJob).filter_by(profile_id=profile_id).all()
    return [r.job_id for r in rows]