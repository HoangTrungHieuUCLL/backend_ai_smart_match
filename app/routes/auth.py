from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.service.auth import auth_service, require_admin

router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    username: str


@router.post("/auth/login", response_model=LoginResponse)
def login(credentials: LoginRequest):
    if not auth_service.validate_admin_credentials(
        credentials.username,
        credentials.password,
    ):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    return {
        "access_token": auth_service.create_access_token(credentials.username),
        "token_type": "bearer",
        "username": credentials.username,
    }


@router.get("/auth/me")
def get_current_admin(admin=Depends(require_admin)):
    return {
        "username": admin["sub"],
        "role": admin["role"],
    }
