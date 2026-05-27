from math import sqrt
from typing import Any

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
    
    def calculate_top_compatibility_scores(
    self,
    db: Session,
    cv_skills_embedding: list[float] | None,
    *,
    limit: int = 10,
    ) -> list[dict[str, Any]]:
        if not cv_skills_embedding:
            return []

        jobs = self.repo.get_all_with_requirements_embedding(db)
        scores: list[dict[str, Any]] = []

        for job in jobs:
            score = self._cosine_similarity_percentage(
                cv_skills_embedding,
                job.requirements_embedding,
            )

            if score is None:
                continue

            scores.append(
                {
                    "job_id": job.id,
                    "company_name": job.company_name,
                    "position": job.position,
                    "location": job.location,
                    "type": job.type,
                    "requirements": job.requirements,
                    "requirements_simplified": job.requirements_simplified,
                    "compatibility_score": score,
                }
            )

        scores.sort(key=lambda item: item["compatibility_score"], reverse=True)
        return scores[:limit]

    @staticmethod
    def _cosine_similarity_percentage(
        first_vector: list[float] | Any,
        second_vector: list[float] | Any,
    ) -> float | None:
        first = JobService._to_float_list(first_vector)
        second = JobService._to_float_list(second_vector)

        if not first or not second or len(first) != len(second):
            return None

        dot_product = sum(a * b for a, b in zip(first, second))
        first_magnitude = sqrt(sum(a * a for a in first))
        second_magnitude = sqrt(sum(b * b for b in second))

        if first_magnitude == 0 or second_magnitude == 0:
            return None

        cosine_similarity = dot_product / (first_magnitude * second_magnitude)
        percentage = ((cosine_similarity + 1) / 2) * 100
        return round(max(0, min(100, percentage)), 2)

    @staticmethod
    def _to_float_list(vector: list[float] | Any) -> list[float] | None:
        if vector is None:
            return None

        if hasattr(vector, "tolist"):
            vector = vector.tolist()

        try:
            return [float(value) for value in vector]
        except (TypeError, ValueError):
            return None
