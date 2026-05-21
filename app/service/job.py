from sqlalchemy.orm import Session
from app.repository.job import JobRepository
import random

class JobService:
    def __init__(self):
        self.repo = JobRepository()

    def get_all_jobs(self, db: Session):
        return self.repo.get_all(db)

    def get_job_by_id(self, db: Session, job_id: int):
        return self.repo.get_by_id(db, job_id)

    def assign_placeholder_compatability_scores(self, db: Session):
        jobs = self.repo.get_all(db)

        scores = []

        for job in jobs:
            score = random.randint(0, 100)

            scores.append({
                "job_id": job.id,
                "compatability_score": score
            })

        return scores
