from sqlalchemy.orm import Session
from app.models.job import Job

class JobRepository:

    def get_all(self, db: Session):
        return db.query(Job).all()

    def get_by_id(self, db: Session, job_id: int):
        return db.query(Job).filter(Job.id == job_id).first()
    
    def get_all_with_requirements_embedding(self, db: Session):
        return (
            db.query(Job)
            .filter(Job.requirements_embedding.isnot(None))
            .all()
        )

    def update_by_id(self, db: Session, job_id: int, data: dict):
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return None

        for key, value in data.items():
            if hasattr(job, key):
                setattr(job, key, value)

        db.commit()
        db.refresh(job)
        return job
