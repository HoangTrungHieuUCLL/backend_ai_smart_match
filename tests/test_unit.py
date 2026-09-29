from datetime import date

import pytest

from app.routes import cv as cv_routes
from app.schemas.job import JobCreate
from app.service import job as job_service_module
from app.service.job import JobService
from app.utils.cv_filename import build_cv_filename
from app.utils.text_cleaning import TextCleaner


def test_build_cv_filename_with_clean_name_parts():
    result = build_cv_filename(
        given_name="Hamza",
        middle_name="M.",
        family_name="Eren",
        today=date(2025, 12, 31),
    )

    assert result == "HamzaMEren_CV_20251231.pdf"


def test_build_cv_filename_defaults_to_unknown_when_no_name_parts_provided():
    result = build_cv_filename(given_name=None, middle_name=None, family_name=None, today=date(2023, 1, 1))

    assert result == "Unknown_CV_20230101.pdf"


def test_build_cv_filename_strips_punctuation_and_accents():
    result = build_cv_filename(
        given_name="Ján",
        middle_name="",
        family_name="O'Neil",
        today=date(2024, 5, 5),
    )

    assert result == "JanONeil_CV_20240505.pdf"


def test_text_cleaner_removes_junk_and_normalizes_spacing():
    cleaner = TextCleaner()
    raw_text = "Hello\r\n• Python developer\r\nO @\r\nExperience:\nLine one\nLine two"
    cleaned = cleaner.clean(raw_text)

    assert "Python developer" in cleaned
    assert "O @" not in cleaned
    assert "Line one Line two" in cleaned


def test_prepare_ai_result_with_skills_embedding_injects_names_and_embeds_skills(monkeypatch):
    dummy_cv = type("DummyCV", (), {"model_dump": lambda self: {"candidate_profile": {"skills": ["Python", "FastAPI"]}}})()

    monkeypatch.setattr(cv_routes, "embed_skills", lambda skills: [0.1, 0.2, 0.3])

    result = cv_routes._prepare_ai_result_with_skills_embedding(
        dummy_cv,
        given_name="Berk",
        middle_name="A.",
        family_name="Can",
        email="berk@example.com",
    )

    assert result["candidate_profile"]["given_name"] == "Berk"
    assert result["candidate_profile"]["middle_name"] == "A."
    assert result["candidate_profile"]["family_name"] == "Can"
    assert result["candidate_profile"]["email"] == "berk@example.com"
    assert result["skills_embedding"] == [0.1, 0.2, 0.3]


def test_create_job_vectorizes_simplified_requirements(monkeypatch):
    captured = {}

    class FakeJobRepository:
        def create(self, db, data):
            captured.update(data)
            return data

    service = JobService()
    service.repo = FakeJobRepository()

    monkeypatch.setattr(
        job_service_module,
        "vectorize_requirements",
        lambda requirements: [0.1, 0.2, 0.3],
    )

    payload = JobCreate(
        company_name="HR Next",
        position="Data Analyst",
        date="2026-06-04",
        location="Brussels",
        type="Data",
        overview="Analyze hiring data.",
        responsibilities="Build dashboards.",
        requirements="Python and SQL.",
        requirements_simplified="Python, SQL",
        offers="Flexible work.",
        salary=None,
        notes=None,
    )

    result = service.create_job(db=object(), job_data=payload)

    assert result["requirements_embedding"] == [0.1, 0.2, 0.3]
    assert captured["requirements_simplified"] == "Python, SQL"
    assert captured["salary"] == ""
    assert captured["notes"] == ""


def test_text_cleaner_keeps_diacritics_emails_and_bullets():
    cleaner = TextCleaner()

    assert "Nguyễn Văn Anh Kỹ sư phần mềm" in cleaner.clean("Nguyễn Văn Anh\nKỹ sư phần mềm")
    assert "email: a@b.com" in cleaner.clean("email: a@b.com")
    assert cleaner.clean("experienced engineer").startswith("experienced")
    assert cleaner.clean("• Built APIs\n• Led team") == "- Built APIs\n- Led team"


def test_text_cleaner_puts_each_section_heading_on_its_own_line_once():
    cleaned = TextCleaner().clean("WORK EXPERIENCE\nAcme\nSKILLS & COMPETENCIES\nPython")

    assert cleaned == "WORK EXPERIENCE\nAcme\n\nSKILLS & COMPETENCIES\nPython"


def _fake_cv(skills):
    profile = type("Profile", (), {"skills": skills})()
    return type("ParsedCV", (), {"candidate_profile": profile})()


def test_parse_cv_uses_bert_skills_filtered_to_taxonomy(monkeypatch):
    heuristic_cv = _fake_cv(["heuristic skill"])
    bert = type("Bert", (), {"extract_cv_structure": lambda self, text: (_fake_cv(["python", "munich", "sql"]), [{"word": "x", "label": "O"}])})()
    monkeypatch.setattr(cv_routes.cv_parser_service, "parse_cv", lambda text, pages=None: heuristic_cv, raising=False)
    monkeypatch.setattr(cv_routes, "extract_words_and_boxes_from_pdf_bytes", lambda data: None)
    monkeypatch.setattr(cv_routes, "get_bert_classifier", lambda: bert)

    parsed, tokens = cv_routes._parse_cv_bytes_sync(b"pdf")

    assert parsed is heuristic_cv
    assert parsed.candidate_profile.skills == ["python", "sql"]
    assert tokens == [{"word": "x", "label": "O"}]


def test_parse_cv_keeps_heuristic_skills_when_bert_fails(monkeypatch):
    heuristic_cv = _fake_cv(["heuristic skill"])
    monkeypatch.setattr(cv_routes.cv_parser_service, "parse_cv", lambda text, pages=None: heuristic_cv, raising=False)
    monkeypatch.setattr(cv_routes, "extract_words_and_boxes_from_pdf_bytes", lambda data: None)
    monkeypatch.setattr(cv_routes, "get_bert_classifier", lambda: (_ for _ in ()).throw(OSError("no weights")))

    parsed, tokens = cv_routes._parse_cv_bytes_sync(b"pdf")

    assert parsed.candidate_profile.skills == ["heuristic skill"]
    assert tokens == []
