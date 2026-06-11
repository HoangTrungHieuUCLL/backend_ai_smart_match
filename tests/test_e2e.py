from fastapi import FastAPI
from fastapi.testclient import TestClient
from types import SimpleNamespace

from app.routes import cv as cv_routes
from app.routes import executive as executive_routes
from app.routes import job as job_routes
from app.routes import auth as auth_routes
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


def test_linkedin_login_start_uses_login_callback(monkeypatch):
    app = FastAPI()
    app.include_router(auth_routes.router)

    monkeypatch.setattr(auth_routes.settings, "LINKEDIN_CLIENT_ID", "client-id")
    monkeypatch.setattr(auth_routes.settings, "LINKEDIN_CLIENT_SECRET", "client-secret")
    monkeypatch.setattr(
        auth_routes.settings,
        "LINKEDIN_LOGIN_REDIRECT_URI",
        "http://localhost:8000/auth/linkedin/login-callback",
    )

    client = TestClient(app)
    response = client.get("/auth/linkedin/login-start", follow_redirects=False)

    assert response.status_code == 307
    assert "redirect_uri=http%3A%2F%2Flocalhost%3A8000%2Fauth%2Flinkedin%2Flogin-callback" in response.headers["location"]
    assert "scope=openid+profile+email" in response.headers["location"]


def test_linkedin_login_callback_logs_in_existing_user(monkeypatch):
    app = FastAPI()
    app.include_router(auth_routes.router)

    async def fake_fetch_linkedin_userinfo(code, redirect_uri):
        return {"email": "USER@example.com"}

    monkeypatch.setattr(auth_routes.settings, "LINKEDIN_CLIENT_ID", "client-id")
    monkeypatch.setattr(auth_routes.settings, "LINKEDIN_CLIENT_SECRET", "client-secret")
    monkeypatch.setattr(auth_routes.settings, "FRONTEND_URL", "http://localhost:3000")
    monkeypatch.setattr(auth_routes, "_fetch_linkedin_userinfo", fake_fetch_linkedin_userinfo)
    monkeypatch.setattr(
        auth_routes.user_service,
        "find_by_email",
        lambda email: {"email": email, "password_hash": "hash", "role": "user"},
    )

    state = auth_routes._sign_state({"iat": int(auth_routes.time.time()), "flow": "login"})
    client = TestClient(app)
    response = client.get(
        f"/auth/linkedin/login-callback?code=abc&state={state}",
        follow_redirects=False,
    )

    assert response.status_code == 307
    assert response.headers["location"].startswith("http://localhost:3000/linkedin-login-callback?")
    assert "email=user%40example.com" in response.headers["location"]
    assert "role=user" in response.headers["location"]


def test_linkedin_login_callback_rejects_unknown_user(monkeypatch):
    app = FastAPI()
    app.include_router(auth_routes.router)

    async def fake_fetch_linkedin_userinfo(code, redirect_uri):
        return {"email": "new-user@example.com"}

    monkeypatch.setattr(auth_routes.settings, "LINKEDIN_CLIENT_ID", "client-id")
    monkeypatch.setattr(auth_routes.settings, "LINKEDIN_CLIENT_SECRET", "client-secret")
    monkeypatch.setattr(auth_routes.settings, "FRONTEND_URL", "http://localhost:3000")
    monkeypatch.setattr(auth_routes, "_fetch_linkedin_userinfo", fake_fetch_linkedin_userinfo)
    monkeypatch.setattr(auth_routes.user_service, "find_by_email", lambda email: None)

    state = auth_routes._sign_state({"iat": int(auth_routes.time.time()), "flow": "login"})
    client = TestClient(app)
    response = client.get(
        f"/auth/linkedin/login-callback?code=abc&state={state}",
        follow_redirects=False,
    )

    assert response.status_code == 307
    assert response.headers["location"] == "http://localhost:3000/login?linkedinLogin=not_found"


def test_linkedin_register_callback_creates_user(monkeypatch):
    app = FastAPI()
    app.include_router(auth_routes.router)
    created = {}

    async def fake_fetch_linkedin_userinfo(code, redirect_uri):
        return {"email": "new-user@example.com"}

    def fake_create_oauth_user(email, role="user"):
        created["email"] = email
        created["role"] = role
        return {"email": email, "role": role}

    monkeypatch.setattr(auth_routes.settings, "LINKEDIN_CLIENT_ID", "client-id")
    monkeypatch.setattr(auth_routes.settings, "LINKEDIN_CLIENT_SECRET", "client-secret")
    monkeypatch.setattr(auth_routes.settings, "FRONTEND_URL", "http://localhost:3000")
    monkeypatch.setattr(auth_routes, "_fetch_linkedin_userinfo", fake_fetch_linkedin_userinfo)
    monkeypatch.setattr(auth_routes.user_service, "find_by_email", lambda email: None)
    monkeypatch.setattr(auth_routes.user_service, "create_oauth_user", fake_create_oauth_user)

    state = auth_routes._sign_state({"iat": int(auth_routes.time.time()), "flow": "register"})
    client = TestClient(app)
    response = client.get(
        f"/auth/linkedin/register-callback?code=abc&state={state}",
        follow_redirects=False,
    )

    assert response.status_code == 307
    assert created == {"email": "new-user@example.com", "role": "user"}
    assert response.headers["location"].startswith("http://localhost:3000/linkedin-login-callback?")
    assert "email=new-user%40example.com" in response.headers["location"]


def test_linkedin_register_callback_logs_in_existing_user(monkeypatch):
    app = FastAPI()
    app.include_router(auth_routes.router)

    async def fake_fetch_linkedin_userinfo(code, redirect_uri):
        return {"email": "existing@example.com"}

    monkeypatch.setattr(auth_routes.settings, "LINKEDIN_CLIENT_ID", "client-id")
    monkeypatch.setattr(auth_routes.settings, "LINKEDIN_CLIENT_SECRET", "client-secret")
    monkeypatch.setattr(auth_routes.settings, "FRONTEND_URL", "http://localhost:3000")
    monkeypatch.setattr(auth_routes, "_fetch_linkedin_userinfo", fake_fetch_linkedin_userinfo)
    monkeypatch.setattr(
        auth_routes.user_service,
        "find_by_email",
        lambda email: {"email": email, "password_hash": "hash", "role": "user"},
    )
    monkeypatch.setattr(
        auth_routes.user_service,
        "create_oauth_user",
        lambda email, role="user": (_ for _ in ()).throw(AssertionError("should not create duplicate user")),
    )

    state = auth_routes._sign_state({"iat": int(auth_routes.time.time()), "flow": "register"})
    client = TestClient(app)
    response = client.get(
        f"/auth/linkedin/register-callback?code=abc&state={state}",
        follow_redirects=False,
    )

    assert response.status_code == 307
    assert response.headers["location"].startswith("http://localhost:3000/linkedin-login-callback?")
    assert "email=existing%40example.com" in response.headers["location"]
