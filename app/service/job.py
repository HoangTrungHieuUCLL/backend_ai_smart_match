from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session
from sentence_transformers import util
import torch

from app.repository.job import JobRepository
from app.models.cv import CompatibilityScore


class JobService:
    def __init__(self):
        self.repo = JobRepository()

    def get_all_jobs(self, db: Session):
        return self.repo.get_all(db)

    def get_job_by_id(self, db: Session, job_id: int):
        return self.repo.get_by_id(db, job_id)

    def get_top_compatibility_scores_for_profile(
        self,
        db: Session,
        profile_id: int,
        *,
        limit: int | None = 10,
    ) -> dict[str, Any]:
        scores = self.repo.get_top_compatibility_scores_for_profile(
            db,
            profile_id,
            limit=limit,
        )

        return {
            "profile_id": profile_id,
            "top_10_compatibility_scores": scores,
        }

    def calculate_and_save_scores_for_profile(
        self,
        db: Session,
        profile_id: int,
    ) -> dict[str, Any]:
        profile = self.repo.get_profile_by_id(db, profile_id)

        if profile is None:
            raise HTTPException(status_code=404, detail="Profile not found")

        if profile.skills_embedding is None:
            raise HTTPException(
                status_code=400,
                detail="Profile does not have a skills embedding",
            )

        all_scores = self.calculate_top_compatibility_scores(
            db,
            profile.skills_embedding,
            limit=None,
        )

        """
        db.query(CompatibilityScore).filter(
            CompatibilityScore.profile_id == profile_id
        ).delete()
        """
        for item in all_scores:
            db.add(
                CompatibilityScore(
                    profile_id=profile_id,
                    job_id=item["job_id"],
                    score=item["compatibility_score"],
                )
            )

        db.commit()

        return {
            "profile_id": profile_id,
            "saved_count": len(all_scores),
            "jobs": all_scores,
        }

    def calculate_top_compatibility_scores(
        self,
        db: Session,
        cv_skills_embedding: list[float] | None,
        *,
        limit: int | None = 10,
    ) -> list[dict[str, Any]]:
        if cv_skills_embedding is None:
            print("DEBUG: cv_skills_embedding is None")
            return []

        cv_vector = self._to_float_list(cv_skills_embedding)
        print("DEBUG: cv embedding type:", type(cv_skills_embedding))
        print("DEBUG: cv embedding length:", len(cv_vector or []))

        jobs = self.repo.get_all_with_requirements_embedding(db)
        print("DEBUG: embedded jobs found:", len(jobs))

        scores: list[dict[str, Any]] = []

        for job in jobs:
            job_vector = self._to_float_list(job.requirements_embedding)

            print(
                "DEBUG job:",
                job.id,
                job.position,
                "raw type:",
                type(job.requirements_embedding),
                "vector length:",
                len(job_vector or []),
            )

            score = self._cosine_similarity_percentage(
                cv_skills_embedding,
                job.requirements_embedding,
            )

            print("DEBUG score:", job.id, score)

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

        print("DEBUG total scores created:", len(scores))
        
        return scores if limit is None else scores[:limit]

    @staticmethod
    def _cosine_similarity_percentage(
        first_vector: list[float] | Any,
        second_vector: list[float] | Any,
    ) -> float | None:
        first = JobService._to_float_list(first_vector)
        second = JobService._to_float_list(second_vector)

        if not first or not second or len(first) != len(second):
            return None

        first_tensor = torch.tensor(first)
        second_tensor = torch.tensor(second)

        cosine_similarity = util.cos_sim(first_tensor, second_tensor).item()

        percentage = max(0, cosine_similarity) * 100

        return round(min(100, percentage), 2)

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