from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.service.auth import auth_service, require_authenticated
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
