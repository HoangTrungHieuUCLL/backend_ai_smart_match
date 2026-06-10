from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.service.auth import auth_service, require_admin
from app.service.user_service import user_service
import re
from app.service.profile import ProfileService
from sqlalchemy.orm import Session
from app.database import SessionLocal
router = APIRouter()


class LoginRequest(BaseModel):
    email: str
    password: str

class RegisterRequest(BaseModel):
    email: str
    password: str

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