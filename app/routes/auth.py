import base64
import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.service.cv import CVService
from app.service.cv_embedding_service import embed_skills
from app.service.auth import auth_service, require_admin, require_authenticated
from app.service.user_service import user_service
import re
from app.service.profile import ProfileService
from sqlalchemy.orm import Session
from app.database import SessionLocal
router = APIRouter()
cv_service = CVService()

LINKEDIN_AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
LINKEDIN_TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
LINKEDIN_USERINFO_URL = "https://api.linkedin.com/v2/userinfo"
LINKEDIN_SCOPES = "openid profile email"
STATE_MAX_AGE_SECONDS = 600


class LoginRequest(BaseModel):
    email: str
    password: str

class RegisterRequest(BaseModel):
    email: str
    password: str

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    email: str
    profile_id: int | None = None


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()



def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _base64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _base64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def _sign_state(payload: dict) -> str:
    body = _base64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signature = hmac.new(
        settings.AUTH_SECRET_KEY.encode("utf-8"),
        body.encode("ascii"),
        hashlib.sha256,
    ).digest()

    return f"{body}.{_base64url_encode(signature)}"


def _verify_state(state: str) -> dict:
    try:
        body, signature = state.split(".", 1)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid LinkedIn state") from exc

    expected = hmac.new(
        settings.AUTH_SECRET_KEY.encode("utf-8"),
        body.encode("ascii"),
        hashlib.sha256,
    ).digest()

    if not hmac.compare_digest(_base64url_decode(signature), expected):
        raise HTTPException(status_code=400, detail="Invalid LinkedIn state")

    payload = json.loads(_base64url_decode(body))
    issued_at = int(payload.get("iat", 0))

    if issued_at < int(time.time()) - STATE_MAX_AGE_SECONDS:
        raise HTTPException(status_code=400, detail="Expired LinkedIn state")

    return payload


def _frontend_redirect(path: str, **params: str | int | None) -> RedirectResponse:
    filtered = {key: value for key, value in params.items() if value is not None}
    query = urlencode(filtered)
    url = f"{settings.FRONTEND_URL.rstrip('/')}{path}"

    if query:
        url = f"{url}?{query}"

    return RedirectResponse(url)


def _linkedin_profile_redirect_params(userinfo: dict) -> dict[str, str | int | None]:
    return {
        "linkedinLinked": "true",
        "linkedinName": userinfo.get("name"),
        "linkedinGivenName": userinfo.get("given_name"),
        "linkedinFamilyName": userinfo.get("family_name"),
        "linkedinPicture": userinfo.get("picture"),
        "linkedinEmailVerified": str(bool(userinfo.get("email_verified"))).lower()
        if "email_verified" in userinfo
        else None,
    }


def _require_linkedin_config() -> None:
    if not settings.LINKEDIN_CLIENT_ID or not settings.LINKEDIN_CLIENT_SECRET:
        raise HTTPException(
            status_code=500,
            detail="LinkedIn authentication is not configured",
        )


async def _fetch_linkedin_userinfo(code: str, redirect_uri: str) -> dict:
    async with httpx.AsyncClient(timeout=10) as client:
        token_response = await client.post(
            LINKEDIN_TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": settings.LINKEDIN_CLIENT_ID,
                "client_secret": settings.LINKEDIN_CLIENT_SECRET,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        token_response.raise_for_status()
        access_token = token_response.json().get("access_token")

        if not access_token:
            raise ValueError("LinkedIn token response did not include access_token")

        userinfo_response = await client.get(
            LINKEDIN_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        userinfo_response.raise_for_status()
        return userinfo_response.json()

def validate_password(password: str) -> bool:
    return (
        len(password) >= 8
        and re.search(r"[A-Z]", password)
        and re.search(r"\d", password)
    )

@router.post("/auth/login", response_model=LoginResponse)
def login(credentials: LoginRequest,
           db: Session = Depends(get_db)):

    # ADMIN LOGIN (fallback)
    if auth_service.validate_admin_credentials(
        credentials.email,
        credentials.password,
    ):
        token = auth_service.create_access_token(
            credentials.email,
            "admin",
        )

        return {
            "access_token": token,
            "token_type": "bearer",
            "email": credentials.email,
            "profile_id": None,
        }

    # NORMAL USER LOGIN
    user = user_service.find_by_email(credentials.email)

    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not user_service.verify_password(
        credentials.password,
        user["password_hash"],
    ):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    profile = ProfileService().get_by_email(db, credentials.email)
    
    token = auth_service.create_access_token(
        credentials.email,
        user["role"],
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "email": credentials.email,
        "profile_id": profile.id if profile else None,
    }


@router.get("/auth/me")
def get_current_admin(admin=Depends(require_admin)):
    return {
        "email": admin["sub"],
        "role": admin["role"],
    }

@router.post("/auth/register")
def register(request: RegisterRequest):

    if user_service.email_exists(request.email):
        raise HTTPException(
            status_code=409,
            detail="EMAIL_EXISTS",
        )

    if not validate_password(request.password):
        raise HTTPException(
            status_code=400,
            detail="INVALID_PASSWORD",
        )

    user_service.create_user(
        request.email,
        request.password,
        role="user",
    )

    token = auth_service.create_access_token(
        request.email,
        "user",
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "email": request.email,
    }


@router.post("/auth/change-password")
def change_password(
    request: ChangePasswordRequest,
    current_user=Depends(require_authenticated),
):
    if not validate_password(request.new_password):
        raise HTTPException(
            status_code=400,
            detail="INVALID_PASSWORD",
        )

    user = user_service.find_by_email(current_user["sub"])

    if not user:
        raise HTTPException(status_code=404, detail="USER_NOT_FOUND")

    if not user_service.verify_password(
        request.current_password,
        user["password_hash"],
    ):
        raise HTTPException(status_code=400, detail="INVALID_CURRENT_PASSWORD")

    user_service.update_password(current_user["sub"], request.new_password)

    return {"message": "Password changed"}


@router.get("/auth/linkedin/cv-start")
def start_linkedin_cv_import():
    _require_linkedin_config()

    state = _sign_state({"iat": int(time.time()), "flow": "cv-import"})
    params = {
        "response_type": "code",
        "client_id": settings.LINKEDIN_CLIENT_ID,
        "redirect_uri": settings.LINKEDIN_REDIRECT_URI,
        "state": state,
        "scope": LINKEDIN_SCOPES,
    }

    return RedirectResponse(f"{LINKEDIN_AUTH_URL}?{urlencode(params)}")


@router.get("/auth/linkedin/login-start")
def start_linkedin_login():
    _require_linkedin_config()

    state = _sign_state({"iat": int(time.time()), "flow": "login"})
    params = {
        "response_type": "code",
        "client_id": settings.LINKEDIN_CLIENT_ID,
        "redirect_uri": settings.LINKEDIN_LOGIN_REDIRECT_URI,
        "state": state,
        "scope": LINKEDIN_SCOPES,
    }

    return RedirectResponse(f"{LINKEDIN_AUTH_URL}?{urlencode(params)}")


@router.get("/auth/linkedin/register-start")
def start_linkedin_register():
    _require_linkedin_config()

    state = _sign_state({"iat": int(time.time()), "flow": "register"})
    params = {
        "response_type": "code",
        "client_id": settings.LINKEDIN_CLIENT_ID,
        "redirect_uri": settings.LINKEDIN_REGISTER_REDIRECT_URI,
        "state": state,
        "scope": LINKEDIN_SCOPES,
    }

    return RedirectResponse(f"{LINKEDIN_AUTH_URL}?{urlencode(params)}")


@router.get("/auth/linkedin/login-callback")
async def linkedin_login_callback(
    code: str | None = Query(None),
    state: str | None = Query(None),
    error: str | None = Query(None),
):
    if error or not code or not state:
        return _frontend_redirect("/login", linkedinLogin="failed")

    try:
        _require_linkedin_config()
        state_payload = _verify_state(state)

        if state_payload.get("flow") != "login":
            raise ValueError("LinkedIn state flow did not match login")

        userinfo = await _fetch_linkedin_userinfo(
            code,
            settings.LINKEDIN_LOGIN_REDIRECT_URI,
        )
        email = (userinfo.get("email") or "").strip().lower()

        if not email:
            return _frontend_redirect("/login", linkedinLogin="missing_email")

        user = user_service.find_by_email(email)

        if not user:
            return _frontend_redirect("/login", linkedinLogin="not_found")

        token = auth_service.create_access_token(email, user["role"])

        return _frontend_redirect(
            "/linkedin-login-callback",
            token=token,
            email=email,
            role=user["role"],
            **_linkedin_profile_redirect_params(userinfo),
        )
    except Exception:
        return _frontend_redirect("/login", linkedinLogin="failed")


@router.get("/auth/linkedin/register-callback")
async def linkedin_register_callback(
    code: str | None = Query(None),
    state: str | None = Query(None),
    error: str | None = Query(None),
):
    if error or not code or not state:
        return _frontend_redirect("/register", linkedinRegister="failed")

    try:
        _require_linkedin_config()
        state_payload = _verify_state(state)

        if state_payload.get("flow") != "register":
            raise ValueError("LinkedIn state flow did not match registration")

        userinfo = await _fetch_linkedin_userinfo(
            code,
            settings.LINKEDIN_REGISTER_REDIRECT_URI,
        )
        email = (userinfo.get("email") or "").strip().lower()

        if not email:
            return _frontend_redirect("/register", linkedinRegister="missing_email")

        user = user_service.find_by_email(email)

        if not user:
            user = user_service.create_oauth_user(email, role="user")

        token = auth_service.create_access_token(email, user["role"])

        return _frontend_redirect(
            "/linkedin-login-callback",
            token=token,
            email=email,
            role=user["role"],
            **_linkedin_profile_redirect_params(userinfo),
        )
    except Exception:
        return _frontend_redirect("/register", linkedinRegister="failed")


@router.get("/auth/linkedin/cv-callback")
async def linkedin_cv_callback(
    code: str | None = Query(None),
    state: str | None = Query(None),
    error: str | None = Query(None),
    db: Session = Depends(get_db),
):
    if error or not code or not state:
        return _frontend_redirect(
            "/job-search-with-ai",
            linkedinImport="failed",
        )

    try:
        _require_linkedin_config()
        state_payload = _verify_state(state)

        if state_payload.get("flow") != "cv-import":
            raise ValueError("LinkedIn state flow did not match CV import")

        userinfo = await _fetch_linkedin_userinfo(code, settings.LINKEDIN_REDIRECT_URI)

        given_name = userinfo.get("given_name") or ""
        family_name = userinfo.get("family_name") or ""
        email = userinfo.get("email")

        structured_data = {
            "candidate_profile": {
                "given_name": given_name or "Unknown",
                "middle_name": None,
                "family_name": family_name or "Unknown",
                "current_title": None,
                "phone": None,
                "location": None,
                "email": email,
                "bio": None,
                "skills": [],
            },
            "work_experience": [],
            "education": [],
            "projects": [],
            "languages": [],
            "certifications": [],
            "skills_embedding": embed_skills([]),
        }

        profile = cv_service.save_ai_cv_result(
            db,
            filename="LinkedIn import",
            structured_data=structured_data,
            compatibility_scores=[],
        )

        return _frontend_redirect(
            "/linkedin-cv-callback",
            profileId=profile.id,
            cvId=profile.cv_id,
        )
    except Exception:
        db.rollback()
        return _frontend_redirect(
            "/job-search-with-ai",
            linkedinImport="failed",
        )
