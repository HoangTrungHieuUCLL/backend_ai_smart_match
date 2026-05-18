from sqlalchemy.orm import Session
from app.repository.job import JobRepository

class JobService:
    def __init__(self):
        self.repo = JobRepository()

    def get_all_jobs(self, db: Session):
        return self.repo.get_all(db)

    def get_job_by_id(self, db: Session, job_id: int):
        return self.repo.get_by_id(db, job_id)
