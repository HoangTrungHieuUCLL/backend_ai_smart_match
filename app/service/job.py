from typing import Any
import math
import re

from fastapi import HTTPException
import torch
from sqlalchemy.orm import Session
from sentence_transformers import util

from app.repository.job import JobRepository
from app.models.cv import CompatibilityScore
from app.schemas.job import JobCreate
from app.service.compatibility_calibration import load_scoring_config
from app.service.requirements_vectorizer import vectorize_requirements
from app.service.skill_taxonomy import canonicalize_skill_phrase


class JobService:
    def __init__(self):
        self.repo = JobRepository()
        self.scoring_config = load_scoring_config()

    def get_all_jobs(self, db: Session):
        return self.repo.get_all(db)

    def create_job(self, db: Session, job_data: JobCreate):
        data = job_data.model_dump()
        data["salary"] = data["salary"] or ""
        data["notes"] = data["notes"] or ""
        data["requirements_embedding"] = vectorize_requirements(
            data["requirements_simplified"]
        )

        return self.repo.create(db, data)

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

        cv_skills = self._skills_as_list(profile.skills)

        if profile.skills_embedding is None and not cv_skills:
            raise HTTPException(
                status_code=400,
                detail="Profile does not have extracted skills",
            )

        all_scores = self.calculate_top_compatibility_scores(
            db,
            profile.skills_embedding,
            cv_skills=cv_skills,
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
        cv_skills: list[str] | str | None = None,
        limit: int | None = 10,
    ) -> list[dict[str, Any]]:
        cv_skill_list = self._skills_as_list(cv_skills)

        if not cv_skill_list and cv_skills_embedding is None:
            return []

        cv_vector = self._to_float_list(cv_skills_embedding)
        jobs = self.repo.get_all_with_requirements_embedding(db)

        scores: list[dict[str, Any]] = []

        for job in jobs:
            job_requirements = self._skills_as_list(job.requirements_simplified or job.requirements)

            if cv_skill_list and job_requirements:
                score = self._dbscan_compatibility_score(cv_skill_list, job_requirements)
            else:
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

        return scores if limit is None else scores[:limit]

    @staticmethod
    def _skills_as_list(value: list[str] | str | None) -> list[str]:
        if value is None:
            return []

        if isinstance(value, list):
            source = value
        else:
            source = re.split(r"[;,\n]", value)

        cleaned: list[str] = []
        seen: set[str] = set()

        for item in source:
            phrase = " ".join(str(item).split()).strip()
            if not phrase:
                continue

            normalized = canonicalize_skill_phrase(phrase)
            lowered = normalized.lower()
            if lowered in seen:
                continue

            seen.add(lowered)
            cleaned.append(normalized)

        return cleaned

    def _dbscan_compatibility_score(
        self,
        cv_skills: list[str],
        job_requirements: list[str],
    ) -> float | None:
        all_phrases = cv_skills + job_requirements
        if not all_phrases:
            return None

        embeddings = self._encode_phrases(all_phrases)
        labels = self._dbscan(
            embeddings,
            eps=self.scoring_config.dbscan_eps,
            min_samples=self.scoring_config.dbscan_min_samples,
        )

        clusters: dict[int, dict[str, set[int]]] = {}
        for index, label in enumerate(labels):
            cluster = clusters.setdefault(label, {"cv": set(), "job": set()})
            if index < len(cv_skills):
                cluster["cv"].add(index)
            else:
                cluster["job"].add(index - len(cv_skills))

        matched_job_requirements = 0
        matched_cv_skills = 0
        shared_taxonomy_groups: set[str] = set()

        for cluster in clusters.values():
            if cluster["cv"] and cluster["job"]:
                matched_job_requirements += len(cluster["job"])
                matched_cv_skills += len(cluster["cv"])
                shared_taxonomy_groups.update(all_phrases[index] for index in cluster["cv"].union({len(cv_skills) + job_index for job_index in cluster["job"]}))

        if not job_requirements:
            return None

        coverage = matched_job_requirements / len(job_requirements)
        precision = matched_cv_skills / len(cv_skills) if cv_skills else 0.0
        taxonomy_alignment = len(shared_taxonomy_groups) / len(job_requirements)
        score = (
            self.scoring_config.coverage_weight * coverage
            + self.scoring_config.precision_weight * precision
            + self.scoring_config.taxonomy_weight * taxonomy_alignment
        ) * 100
        return round(min(100.0, max(0.0, score)), 2)

    def _encode_phrases(self, phrases: list[str]) -> list[list[float]]:
        model = self._get_sentence_model()
        vectors = model.encode(phrases, normalize_embeddings=True)
        return [self._to_float_list(vector) or [] for vector in vectors]

    @staticmethod
    def _get_sentence_model():
        from sentence_transformers import SentenceTransformer

        if not hasattr(JobService, "_sentence_model"):
            JobService._sentence_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

        return JobService._sentence_model

    def _dbscan(
        self,
        vectors: list[list[float]],
        *,
        eps: float,
        min_samples: int,
    ) -> list[int]:
        if not vectors:
            return []

        labels = [-99] * len(vectors)
        cluster_id = 0
        visited: set[int] = set()

        for point_index in range(len(vectors)):
            if point_index in visited:
                continue

            visited.add(point_index)
            neighbors = self._region_query(vectors, point_index, eps)

            if len(neighbors) < min_samples:
                labels[point_index] = -1
                continue

            labels[point_index] = cluster_id
            seeds = [neighbor for neighbor in neighbors if neighbor != point_index]

            while seeds:
                neighbor_index = seeds.pop()

                if neighbor_index not in visited:
                    visited.add(neighbor_index)
                    neighbor_neighbors = self._region_query(vectors, neighbor_index, eps)
                    if len(neighbor_neighbors) >= min_samples:
                        for candidate in neighbor_neighbors:
                            if candidate not in seeds:
                                seeds.append(candidate)

                if labels[neighbor_index] in {-99, -1}:
                    labels[neighbor_index] = cluster_id

            cluster_id += 1

        return labels

    def _region_query(self, vectors: list[list[float]], point_index: int, eps: float) -> list[int]:
        neighbors: list[int] = []
        for candidate_index, candidate_vector in enumerate(vectors):
            distance = self._cosine_distance(vectors[point_index], candidate_vector)
            if distance <= eps:
                neighbors.append(candidate_index)

        return neighbors

    @staticmethod
    def _cosine_distance(first: list[float], second: list[float]) -> float:
        if not first or not second or len(first) != len(second):
            return math.inf

        first_tensor = torch.tensor(first)
        second_tensor = torch.tensor(second)
        cosine_similarity = util.cos_sim(first_tensor, second_tensor).item()
        return 1.0 - cosine_similarity

    @staticmethod
    def _cosine_similarity_percentage(
        first_vector: list[float] | Any,
        second_vector: list[float] | Any,
    ) -> float | None:
        first = JobService._to_float_list(first_vector)
        second = JobService._to_float_list(second_vector)

        if not first or not second or len(first) != len(second):
            return None

        cosine_similarity = JobService._cosine_similarity(first, second)

        percentage = max(0, cosine_similarity) * 100

        return round(min(100, percentage), 2)

    @staticmethod
    def _cosine_similarity(first: list[float], second: list[float]) -> float:
        dot_product = sum(a * b for a, b in zip(first, second))
        first_norm = math.sqrt(sum(a * a for a in first))
        second_norm = math.sqrt(sum(b * b for b in second))

        if not first_norm or not second_norm:
            return 0.0

        return dot_product / (first_norm * second_norm)

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
