from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routes import cv as cv_routes


class DummyProfile:
    def __init__(self):
        self.cv_id = 999
        self.id = 888


class DummyParsedCV:
    def model_dump(self):
        return {"candidate_profile": {"skills": ["Python", "FastAPI"]}}


async def dummy_parse_uploaded_cv(cv):
    return DummyParsedCV()


def fake_save_ai_cv_result(db, filename, structured_data, compatibility_scores=None):
    return DummyProfile()


def override_get_db():
    class DummyDB:
        def rollback(self):
            pass

    yield DummyDB()


def test_parse_cv_endpoint_end_to_end(monkeypatch):
    app = FastAPI()
    app.include_router(cv_routes.router)
    app.dependency_overrides[cv_routes.get_db] = override_get_db

    monkeypatch.setattr(cv_routes, "_parse_uploaded_cv", dummy_parse_uploaded_cv)
    monkeypatch.setattr(cv_routes, "embed_skills", lambda skills: [0.5, 0.5, 0.5])
    monkeypatch.setattr(cv_routes, "build_cv_filename", lambda given_name, middle_name, family_name: "John_Doe_CV_20250101.pdf")
    monkeypatch.setattr(cv_routes.service, "save_ai_cv_result", fake_save_ai_cv_result)

    client = TestClient(app)
    response = client.post(
        "/parse-cv",
        files={"cv": ("resume.pdf", b"dummy content", "application/pdf")},
        data={"given_name": "John", "family_name": "Doe", "email": "john@example.com"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["message"] == "CV processed and saved"
    assert payload["cv_file_name"] == "John_Doe_CV_20250101.pdf"
    assert payload["ai_result"]["skills_embedding"] == [0.5, 0.5, 0.5]
    assert payload["ai_result"]["candidate_profile"]["email"] == "john@example.com"
