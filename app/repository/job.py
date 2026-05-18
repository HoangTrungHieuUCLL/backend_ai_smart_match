from sqlalchemy.orm import Session
from app.models.job import Job

class JobRepository:

    def get_all(self, db: Session):
        return db.query(Job).all()

    def get_by_id(self, db: Session, job_id: int):
        return db.query(Job).filter(Job.id == job_id).first()
