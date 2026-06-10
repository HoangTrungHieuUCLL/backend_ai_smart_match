import importlib.util
import math
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

from app.service.compatibility_calibration import CompatibilityScoringConfig


def _stub_module(name, attrs=None):
    module = ModuleType(name)
    if attrs:
        for key, value in attrs.items():
            setattr(module, key, value)
    return module


@pytest.fixture
def real_job_module(monkeypatch):
    monkeypatch.setitem(
        sys.modules,
        "app.repository.job",
        _stub_module("app.repository.job", {"JobRepository": type("JobRepository", (), {})}),
    )
    monkeypatch.setitem(
        sys.modules,
        "app.models.cv",
        _stub_module("app.models.cv", {"CompatibilityScore": type("CompatibilityScore", (), {})}),
    )
    monkeypatch.setitem(
        sys.modules,
        "app.schemas.job",
        _stub_module("app.schemas.job", {"JobCreate": object, "JobUpdate": object}),
    )
    monkeypatch.setitem(
        sys.modules,
        "app.service.requirements_vectorizer",
        _stub_module(
            "app.service.requirements_vectorizer",
            {
                "simplify_requirements": lambda requirements: requirements or "",
                "vectorize_requirements": lambda requirements: [0.0, 0.0, 0.0],
            },
        ),
    )

    module_path = Path(__file__).resolve().parents[1] / "app" / "service" / "job.py"
    spec = importlib.util.spec_from_file_location("real_job_service_for_tests", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    def cos_sim(first, second):
        dot_product = sum(a * b for a, b in zip(first, second))
        first_norm = math.sqrt(sum(a * a for a in first))
        second_norm = math.sqrt(sum(b * b for b in second))
        value = dot_product / (first_norm * second_norm)
        return SimpleNamespace(item=lambda: value)

    module.util.cos_sim = cos_sim
    return module


@pytest.fixture
def scoring_service(real_job_module):
    service = real_job_module.JobService.__new__(real_job_module.JobService)
    service.scoring_config = CompatibilityScoringConfig(
        dbscan_eps=0.05,
        dbscan_min_samples=1,
    ).normalized()
    return service


def test_cosine_similarity_with_itself_is_one(real_job_module):
    assert real_job_module.JobService._cosine_similarity([1.0, 2.0], [1.0, 2.0]) == pytest.approx(1.0)


def test_cosine_similarity_with_orthogonal_vectors_is_zero(real_job_module):
    assert real_job_module.JobService._cosine_similarity([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)


def test_cosine_helpers_handle_empty_vectors(real_job_module):
    assert real_job_module.JobService._cosine_similarity([], []) == 0.0
    assert math.isinf(real_job_module.JobService._cosine_distance([], []))


def test_cosine_helpers_handle_different_length_vectors(real_job_module):
    assert real_job_module.JobService._cosine_similarity([1.0], [1.0, 2.0]) == 0.0
    assert math.isinf(real_job_module.JobService._cosine_distance([1.0], [1.0, 2.0]))


def test_dbscan_compatibility_score_returns_100_for_identical_skills(scoring_service):
    scoring_service._encode_phrases = lambda phrases: [[1.0, 0.0] for _ in phrases]

    score = scoring_service._dbscan_compatibility_score(["python"], ["python"])

    assert score == 100.0


def test_dbscan_compatibility_score_returns_zero_for_no_overlap(scoring_service):
    vectors = {
        "python": [1.0, 0.0],
        "java": [0.0, 1.0],
    }
    scoring_service._encode_phrases = lambda phrases: [vectors[phrase] for phrase in phrases]

    score = scoring_service._dbscan_compatibility_score(["python"], ["java"])

    assert score == 0.0


def test_dbscan_compatibility_score_is_bounded(scoring_service):
    scoring_service._encode_phrases = lambda phrases: [[1.0, 0.0] for _ in phrases]

    score = scoring_service._dbscan_compatibility_score(["python", "sql"], ["python"])

    assert 0.0 <= score <= 100.0


@pytest.mark.parametrize(
    ("cv_skills", "job_requirements"),
    [
        ([], ["python"]),
        (["python"], []),
        ([], []),
    ],
)
def test_dbscan_compatibility_score_returns_none_for_empty_skill_lists(scoring_service, cv_skills, job_requirements):
    assert scoring_service._dbscan_compatibility_score(cv_skills, job_requirements) is None


def test_skills_as_list_splits_comma_separated_string(real_job_module):
    assert real_job_module.JobService._skills_as_list("Python, SQL, FastAPI") == [
        "python",
        "sql",
    ]


def test_skills_as_list_deduplicates_and_cleans_list_input(real_job_module):
    assert real_job_module.JobService._skills_as_list([" Python ", "python", "", " SQL "]) == [
        "python",
        "sql",
    ]


def test_skills_as_list_returns_empty_list_for_none(real_job_module):
    assert real_job_module.JobService._skills_as_list(None) == []


def test_scoring_config_normalized_weights_sum_to_one():
    config = CompatibilityScoringConfig(
        coverage_weight=2.0,
        precision_weight=3.0,
        taxonomy_weight=5.0,
    ).normalized()

    total = config.coverage_weight + config.precision_weight + config.taxonomy_weight
    assert total == pytest.approx(1.0)


def test_scoring_config_with_zero_weights_is_unchanged():
    config = CompatibilityScoringConfig(
        coverage_weight=0.0,
        precision_weight=0.0,
        taxonomy_weight=0.0,
    )

    assert config.normalized() == config
