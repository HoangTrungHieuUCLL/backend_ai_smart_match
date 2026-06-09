from __future__ import annotations

import csv
import json
import math
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.config import settings
from app.service.skill_taxonomy import canonicalize_skill_phrase


@dataclass(frozen=True)
class CompatibilityScoringConfig:
    dbscan_eps: float = 0.24
    dbscan_min_samples: int = 1
    coverage_weight: float = 0.58
    precision_weight: float = 0.27
    taxonomy_weight: float = 0.15

    def normalized(self) -> "CompatibilityScoringConfig":
        weight_total = self.coverage_weight + self.precision_weight + self.taxonomy_weight
        if not weight_total:
            return self

        return CompatibilityScoringConfig(
            dbscan_eps=self.dbscan_eps,
            dbscan_min_samples=self.dbscan_min_samples,
            coverage_weight=self.coverage_weight / weight_total,
            precision_weight=self.precision_weight / weight_total,
            taxonomy_weight=self.taxonomy_weight / weight_total,
        )


def load_scoring_config() -> CompatibilityScoringConfig:
    calibration_path = settings.COMPATIBILITY_CALIBRATION_PATH
    if calibration_path:
        loaded_config = _load_config_from_path(Path(calibration_path))
        if loaded_config is not None:
            return loaded_config.normalized()

    return CompatibilityScoringConfig(
        dbscan_eps=settings.COMPATIBILITY_DBSCAN_EPS,
        dbscan_min_samples=settings.COMPATIBILITY_DBSCAN_MIN_SAMPLES,
        coverage_weight=settings.COMPATIBILITY_COVERAGE_WEIGHT,
        precision_weight=settings.COMPATIBILITY_PRECISION_WEIGHT,
        taxonomy_weight=settings.COMPATIBILITY_TAXONOMY_WEIGHT,
    ).normalized()


def fit_scoring_config_from_labeled_pairs(csv_path: str | os.PathLike[str]) -> CompatibilityScoringConfig:
    rows = _load_labeled_rows(Path(csv_path))
    if not rows:
        raise ValueError("Calibration dataset is empty")

    eps_candidates = [0.20, 0.22, 0.24, 0.26, 0.28, 0.30]
    weight_candidates = [0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40]

    best_config = CompatibilityScoringConfig()
    best_error = math.inf

    for eps in eps_candidates:
        for coverage_weight in weight_candidates:
            for precision_weight in weight_candidates:
                taxonomy_weight = 1.0 - coverage_weight - precision_weight
                if taxonomy_weight < 0.05 or taxonomy_weight > 0.60:
                    continue

                candidate = CompatibilityScoringConfig(
                    dbscan_eps=eps,
                    coverage_weight=coverage_weight,
                    precision_weight=precision_weight,
                    taxonomy_weight=taxonomy_weight,
                ).normalized()

                error = _evaluate_candidate(candidate, rows)
                if error < best_error:
                    best_error = error
                    best_config = candidate

    return best_config.normalized()


def _load_config_from_path(path: Path) -> CompatibilityScoringConfig | None:
    if not path.exists():
        return None

    if path.suffix.lower() == ".json":
        with path.open("r", encoding="utf-8") as handle:
            raw_data = json.load(handle)
        return CompatibilityScoringConfig(
            dbscan_eps=float(raw_data.get("dbscan_eps", 0.24)),
            dbscan_min_samples=int(raw_data.get("dbscan_min_samples", 1)),
            coverage_weight=float(raw_data.get("coverage_weight", 0.58)),
            precision_weight=float(raw_data.get("precision_weight", 0.27)),
            taxonomy_weight=float(raw_data.get("taxonomy_weight", 0.15)),
        )

    if path.suffix.lower() == ".csv":
        return fit_scoring_config_from_labeled_pairs(path)

    return None


def _load_labeled_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows.append(row)
    return rows


def _evaluate_candidate(candidate: CompatibilityScoringConfig, rows: list[dict[str, Any]]) -> float:
    total_error = 0.0
    for row in rows:
        predicted = _score_row(candidate, row)
        expected = float(row.get("label", row.get("score", 0.0)))
        total_error += abs(predicted - expected)

    return total_error / len(rows)


def _score_row(candidate: CompatibilityScoringConfig, row: dict[str, Any]) -> float:
    cv_skills = _split_skills(row.get("cv_skills"))
    job_skills = _split_skills(row.get("job_requirements"))

    if not cv_skills or not job_skills:
        return 0.0

    all_phrases = cv_skills + job_skills
    embeddings = _encode_phrases(all_phrases)
    labels = _dbscan(embeddings, eps=candidate.dbscan_eps, min_samples=1)

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
            shared_taxonomy_groups.update(all_phrases[index] for index in cluster["cv"])
            shared_taxonomy_groups.update(all_phrases[len(cv_skills) + index] for index in cluster["job"])

    coverage = matched_job_requirements / len(job_skills)
    precision = matched_cv_skills / len(cv_skills)
    taxonomy_alignment = len(shared_taxonomy_groups) / len(set(job_skills))

    return round(
        100.0
        * (
            candidate.coverage_weight * coverage
            + candidate.precision_weight * precision
            + candidate.taxonomy_weight * taxonomy_alignment
        ),
        2,
    )


def _split_skills(value: Any) -> list[str]:
    if value is None:
        return []

    if isinstance(value, list):
        source = value
    else:
        source = str(value).split(",")

    cleaned: list[str] = []
    seen: set[str] = set()
    for item in source:
        skill = canonicalize_skill_phrase(" ".join(str(item).split()).strip())
        if not skill or skill in seen:
            continue
        seen.add(skill)
        cleaned.append(skill)
    return cleaned


_sentence_model = None


def _encode_phrases(phrases: list[str]) -> list[list[float]]:
    model = _get_sentence_model()
    vectors = model.encode(phrases, normalize_embeddings=True)
    return [_to_float_list(vector) or [] for vector in vectors]


def _get_sentence_model():
    global _sentence_model
    if _sentence_model is None:
        from sentence_transformers import SentenceTransformer

        _sentence_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

    return _sentence_model


def _dbscan(
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
        neighbors = _region_query(vectors, point_index, eps)

        if len(neighbors) < min_samples:
            labels[point_index] = -1
            continue

        labels[point_index] = cluster_id
        seeds = [neighbor for neighbor in neighbors if neighbor != point_index]

        while seeds:
            neighbor_index = seeds.pop()

            if neighbor_index not in visited:
                visited.add(neighbor_index)
                neighbor_neighbors = _region_query(vectors, neighbor_index, eps)
                if len(neighbor_neighbors) >= min_samples:
                    for candidate_index in neighbor_neighbors:
                        if candidate_index not in seeds:
                            seeds.append(candidate_index)

            if labels[neighbor_index] in {-99, -1}:
                labels[neighbor_index] = cluster_id

        cluster_id += 1

    return labels


def _region_query(vectors: list[list[float]], point_index: int, eps: float) -> list[int]:
    neighbors: list[int] = []
    for candidate_index, candidate_vector in enumerate(vectors):
        distance = _cosine_distance(vectors[point_index], candidate_vector)
        if distance <= eps:
            neighbors.append(candidate_index)

    return neighbors


def _cosine_distance(first: list[float], second: list[float]) -> float:
    if not first or not second or len(first) != len(second):
        return math.inf

    first_norm = math.sqrt(sum(value * value for value in first))
    second_norm = math.sqrt(sum(value * value for value in second))
    if not first_norm or not second_norm:
        return math.inf

    cosine_similarity = sum(a * b for a, b in zip(first, second)) / (first_norm * second_norm)
    return 1.0 - cosine_similarity


def _to_float_list(vector: list[float] | Any) -> list[float] | None:
    if vector is None:
        return None

    if hasattr(vector, "tolist"):
        vector = vector.tolist()

    try:
        return [float(value) for value in vector]
    except (TypeError, ValueError):
        return None