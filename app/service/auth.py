import base64
import hashlib
import hmac
import json
import time
from typing import Any

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.config import (
    ADMIN_PASSWORD,
    ADMIN_USERNAME,
    AUTH_SECRET_KEY,
    AUTH_TOKEN_EXPIRE_SECONDS,
)

security = HTTPBearer(auto_error=False)


class AuthService:
    def validate_admin_credentials(self, username: str, password: str) -> bool:
        return hmac.compare_digest(username, ADMIN_USERNAME) and hmac.compare_digest(
            password,
            ADMIN_PASSWORD,
        )

    def create_access_token(self, identity: str, role: str = "admin") -> str:
        payload = {
            "sub": identity,
            "role": role,
            "exp": int(time.time()) + AUTH_TOKEN_EXPIRE_SECONDS,
        }
        encoded_payload = self._encode_json(payload)
        signature = self._sign(encoded_payload)

        return f"{encoded_payload}.{signature}"

    def verify_access_token(self, token: str) -> dict[str, Any]:
        try:
            encoded_payload, signature = token.split(".", 1)
        except ValueError as exc:
            raise HTTPException(status_code=401, detail="Invalid token") from exc

        expected_signature = self._sign(encoded_payload)

        if not hmac.compare_digest(signature, expected_signature):
            raise HTTPException(status_code=401, detail="Invalid token")

        payload = self._decode_json(encoded_payload)

        # if payload.get("role") != "admin":
        #     raise HTTPException(status_code=403, detail="Admin access required")

        if int(payload.get("exp", 0)) < int(time.time()):
            raise HTTPException(status_code=401, detail="Token expired")

        return payload

    def _sign(self, value: str) -> str:
        digest = hmac.new(
            AUTH_SECRET_KEY.encode("utf-8"),
            value.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        return self._base64_url_encode(digest)

    def _encode_json(self, payload: dict[str, Any]) -> str:
        data = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        return self._base64_url_encode(data)

    def _decode_json(self, value: str) -> dict[str, Any]:
        try:
            data = self._base64_url_decode(value)
            payload = json.loads(data)
        except (ValueError, json.JSONDecodeError) as exc:
            raise HTTPException(status_code=401, detail="Invalid token") from exc

        if not isinstance(payload, dict):
            raise HTTPException(status_code=401, detail="Invalid token")

        return payload

    @staticmethod
    def _base64_url_encode(value: bytes) -> str:
        return base64.urlsafe_b64encode(value).decode("utf-8").rstrip("=")

    @staticmethod
    def _base64_url_decode(value: str) -> bytes:
        padding = "=" * (-len(value) % 4)
        return base64.urlsafe_b64decode(value + padding)


auth_service = AuthService()


def require_admin(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict[str, Any]:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Authentication required")

    payload = auth_service.verify_access_token(credentials.credentials)

    if payload.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    return payload

def require_authenticated(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict[str, Any]:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Authentication required")

    return auth_service.verify_access_token(credentials.credentials)
