from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session
from sentence_transformers import util
import torch
import re

from app.repository.job import JobRepository
from app.models.cv import CompatibilityScore


_SKILL_ALIASES = {
    "system administration": {"server administrator", "server administration", "sysadmin", "windows server", "redhat", "linux", "solaris"},
    "terminal-based system administration": {"linux cli", "command line", "terminal", "shell", "bash", "linux"},
    "troubleshooting": {"problem solving", "problem-solving", "debugging", "maintenance", "monitoring", "alerts", "incident response"},
    "docker": {"docker image", "container", "containerized", "containers"},
    "kubernetes": {"k8s", "container orchestration"},
    "python": {"python"},
    "scripting": {"script", "scripting", "automation", "python", "vba", "bash", "shell"},
    "automation": {"automated", "automation", "airflow", "ci/cd", "github actions", "vba"},
    "debugging": {"debug", "debugging", "troubleshooting", "problem solving", "problem-solving"},
    "bash": {"bash", "shell", "terminal", "linux cli", "command line"},
    "programming languages": {"python", "java", "javascript", "typescript", "c#", "ruby", "sql"},
    "infrastructure": {"server", "network", "virtualization", "vmware", "cloud", "azure", "aws", "redhat", "linux"},
    "build systems": {"ci/cd", "github actions", "pipeline", "pipelines", "build"},
    "version control": {"git", "github", "github actions"},
    "infrastructure recovery": {"backup", "disaster recovery", "recovery", "restore", "logsystem"},
    "communication skills": {"communication", "scrum", "agile", "team", "collaboration"},
    "written communication": {"documentation", "written", "report"},
    "verbal communication": {"communication", "presentation", "team"},
}


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
            limit=limit or 10,
        )

        return {
            "profile_id": profile_id,
            "compatibility_scores": scores,
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
            profile.skills,
            limit=None,
        )

        db.query(CompatibilityScore).filter(
            CompatibilityScore.profile_id == profile_id
        ).delete()

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
        cv_skills_text: str | None = None,
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

            cosine = self._cosine_similarity(
                cv_skills_embedding,
                job.requirements_embedding,
            )

            score = self._compatibility_score(
                cosine,
                cv_skills_text,
                job.requirements_simplified,
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
        
        scores.sort(key=lambda item: item["compatibility_score"], reverse=True)

        return scores if limit is None else scores[:limit]

    @staticmethod
    def _cosine_similarity(
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

        return max(0, cosine_similarity)

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
        
    @staticmethod
    def _compatibility_score(
        cosine_similarity: float | None,
        cv_skills_text: str | None,
        job_requirements_simplified: str | None,
    ) -> float | None:
        if cosine_similarity is None:
            return None

        semantic_score = JobService._scale_cosine_to_percentage(cosine_similarity)
        overlap_score = JobService._keyword_overlap_percentage(
            cv_skills_text,
            job_requirements_simplified,
        )

        if overlap_score is None:
            final_score = semantic_score
        else:
            final_score = (semantic_score * 0.65) + (overlap_score * 0.35)

        return round(min(100, max(0, final_score)), 2)


    @staticmethod
    def _scale_cosine_to_percentage(
        cosine_similarity: float,
        *,
        floor: float = 0.0,
        ceiling: float = 0.30,
    ) -> float:
        if cosine_similarity <= floor:
            return 0.0

        if cosine_similarity >= ceiling:
            return 100.0

        return ((cosine_similarity - floor) / (ceiling - floor)) * 100


    @staticmethod
    def _keyword_overlap_percentage(
        cv_skills_text: str | None,
        job_requirements_simplified: str | None,
    ) -> float | None:
        cv_keywords = JobService._keyword_set(cv_skills_text)
        job_keywords = JobService._keyword_set(job_requirements_simplified)

        if not cv_keywords or not job_keywords:
            return None

        matched_keywords = {
            job_keyword
            for job_keyword in job_keywords
            if JobService._keyword_matches(job_keyword, cv_keywords)
        }

        return (len(matched_keywords) / len(job_keywords)) * 100


    @staticmethod
    def _keyword_set(value: str | None) -> set[str]:
        if not value:
            return set()

        keywords = re.split(r"[,;\n]+", value)

        cleaned_keywords = {
            re.sub(r"\s+", " ", keyword.strip().lower())
            for keyword in keywords
            if keyword.strip()
        }

        return cleaned_keywords

    @staticmethod
    def _keyword_matches(job_keyword: str, cv_keywords: set[str]) -> bool:
        if job_keyword in cv_keywords:
            return True

        job_terms = JobService._keyword_terms(job_keyword)
        aliases = _SKILL_ALIASES.get(job_keyword, set())

        for cv_keyword in cv_keywords:
            cv_terms = JobService._keyword_terms(cv_keyword)

            if job_terms and job_terms.issubset(cv_terms):
                return True

            if cv_terms and cv_terms.issubset(job_terms) and len(cv_terms) > 1:
                return True

            if any(JobService._phrase_matches(alias, cv_keyword) for alias in aliases):
                return True

        return False

    @staticmethod
    def _keyword_terms(value: str) -> set[str]:
        return {
            term
            for term in re.findall(r"[a-z0-9+#.]+", value.lower())
            if len(term) > 1
        }

    @staticmethod
    def _phrase_matches(needle: str, haystack: str) -> bool:
        needle = needle.lower()
        haystack = haystack.lower()
        return needle in haystack or haystack in needle
