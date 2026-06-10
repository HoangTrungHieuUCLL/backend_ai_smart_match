from fastapi import FastAPI
from fastapi.testclient import TestClient
from types import SimpleNamespace

from app.routes import cv as cv_routes
from app.routes import executive as executive_routes
from app.routes import job as job_routes
from app.service.auth import auth_service


class DummyProfile:
    def __init__(self):
        self.cv_id = 999
        self.id = 888


class DummyParsedCV:
    def model_dump(self):
        return {"candidate_profile": {"skills": ["Python", "FastAPI"]}}


async def dummy_parse_uploaded_cv(cv):
    return DummyParsedCV(), []


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


def test_create_job_endpoint_requires_admin():
    app = FastAPI()
    app.include_router(job_routes.router)
    app.dependency_overrides[job_routes.get_db] = override_get_db

    client = TestClient(app)
    response = client.post("/jobs", json={})

    assert response.status_code == 401


def test_executive_view_endpoint_requires_authentication():
    app = FastAPI()
    app.include_router(executive_routes.router)
    app.dependency_overrides[executive_routes.get_db] = override_get_db

    client = TestClient(app)
    response = client.get("/executive-view")

    assert response.status_code == 401


def test_executive_view_endpoint_rejects_regular_user_token():
    app = FastAPI()
    app.include_router(executive_routes.router)
    app.dependency_overrides[executive_routes.get_db] = override_get_db

    token = auth_service.create_access_token("user@example.com", "user")
    client = TestClient(app)
    response = client.get(
        "/executive-view",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


def test_create_job_endpoint_returns_created_job(monkeypatch):
    app = FastAPI()
    app.include_router(job_routes.router)
    app.dependency_overrides[job_routes.get_db] = override_get_db

    payload = {
        "company_name": "HR Next",
        "position": "Data Analyst",
        "date": "2026-06-04",
        "location": "Brussels",
        "type": "Data",
        "overview": "Analyze hiring data.",
        "responsibilities": "Build dashboards.",
        "requirements": "Python and SQL.",
        "requirements_simplified": "Python, SQL",
        "offers": "Flexible work.",
        "salary": None,
        "notes": None,
    }

    def fake_create_job(db, job):
        data = job.model_dump()
        data["id"] = 123
        data["salary"] = data["salary"] or ""
        data["notes"] = data["notes"] or ""
        data["requirements_embedding"] = [0.1, 0.2, 0.3]
        return SimpleNamespace(**data)

    monkeypatch.setattr(job_routes.service, "create_job", fake_create_job)

    token = auth_service.create_access_token("admin")
    client = TestClient(app)
    response = client.post(
        "/jobs",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["id"] == 123
    assert response.json()["position"] == "Data Analyst"
    assert response.json()["requirements_embedding"] == [0.1, 0.2, 0.3]
