from sqlalchemy.orm import Session

from app.models.job import Job
from app.models.cv import CompatibilityScore, Profile

class JobRepository:
    def get_all(self, db: Session):
        return db.query(Job).all()

    def get_distinct_values(self, db: Session, column_name: str) -> list[str]:
        column = getattr(Job, column_name)
        rows = (
            db.query(column)
            .filter(column.isnot(None), column != "")
            .distinct()
            .order_by(column)
            .all()
        )
        return [value for (value,) in rows]

    def create(self, db: Session, data: dict):
        job = Job(**data)
        db.add(job)
        db.commit()
        db.refresh(job)
        return job

    def get_by_id(self, db: Session, job_id: int):
        return db.query(Job).filter(Job.id == job_id).first()

    def get_profile_by_id(self, db: Session, profile_id: int):
        return db.query(Profile).filter(Profile.id == profile_id).first()

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

    def delete_by_id(self, db: Session, job_id: int):
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return None

        db.delete(job)
        db.commit()
        return job

    def get_top_compatibility_scores_for_profile(
        self,
        db: Session,
        profile_id: int,
        *,
        limit: int = 10,
    ):
        rows = (
            db.query(CompatibilityScore, Job)
            .join(Job, CompatibilityScore.job_id == Job.id)
            .filter(CompatibilityScore.profile_id == profile_id)
            .order_by(CompatibilityScore.score.desc())
            .limit(limit)
            .all()
        )

        return [
            {
                "job_id": job.id,
                "company_name": job.company_name,
                "position": job.position,
                "location": job.location,
                "type": job.type,
                "requirements": job.requirements,
                "requirements_simplified": job.requirements_simplified,
                "compatibility_score": compatibility_score.score,
            }
            for compatibility_score, job in rows
        ]
