import pytest
from fastapi import HTTPException

import app.service.auth as auth_module
from app.service.auth import AuthService


@pytest.fixture
def auth_service(monkeypatch):
    monkeypatch.setattr(auth_module, "ADMIN_USERNAME", "test-admin")
    monkeypatch.setattr(auth_module, "ADMIN_PASSWORD", "test-password")
    monkeypatch.setattr(auth_module, "AUTH_SECRET_KEY", "test-secret")
    monkeypatch.setattr(auth_module, "AUTH_TOKEN_EXPIRE_SECONDS", 60)
    return AuthService()


def _signed_token(service, payload):
    encoded_payload = service._encode_json(payload)
    return f"{encoded_payload}.{service._sign(encoded_payload)}"


def test_create_access_token_returns_string_with_payload_and_signature(auth_service, monkeypatch):
    monkeypatch.setattr(auth_module.time, "time", lambda: 1000)

    token = auth_service.create_access_token("test-admin")

    assert isinstance(token, str)
    parts = token.split(".")
    assert len(parts) == 2
    assert all(parts)


def test_verify_access_token_returns_payload_for_fresh_token(auth_service, monkeypatch):
    monkeypatch.setattr(auth_module.time, "time", lambda: 1000)
    token = auth_service.create_access_token("test-admin")

    payload = auth_service.verify_access_token(token)

    assert payload["sub"] == "test-admin"
    assert payload["role"] == "admin"
    assert payload["exp"] == 1060


def test_verify_access_token_rejects_invalid_signature(auth_service, monkeypatch):
    monkeypatch.setattr(auth_module.time, "time", lambda: 1000)
    token = auth_service.create_access_token("test-admin")
    encoded_payload, _ = token.split(".", 1)

    with pytest.raises(HTTPException) as exc_info:
        auth_service.verify_access_token(f"{encoded_payload}.invalid-signature")

    assert exc_info.value.status_code == 401


def test_verify_access_token_rejects_expired_token(auth_service, monkeypatch):
    monkeypatch.setattr(auth_module.time, "time", lambda: 1000)
    token = _signed_token(
        auth_service,
        {"sub": "test-admin", "role": "admin", "exp": 999},
    )

    with pytest.raises(HTTPException) as exc_info:
        auth_service.verify_access_token(token)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Token expired"


def test_verify_access_token_rejects_non_admin_role(auth_service, monkeypatch):
    monkeypatch.setattr(auth_module.time, "time", lambda: 1000)
    token = _signed_token(
        auth_service,
        {"sub": "test-admin", "role": "user", "exp": 1060},
    )

    with pytest.raises(HTTPException) as exc_info:
        auth_service.verify_access_token(token)

    assert exc_info.value.status_code == 403


def test_verify_access_token_rejects_malformed_token(auth_service):
    with pytest.raises(HTTPException) as exc_info:
        auth_service.verify_access_token("not-a-token")

    assert exc_info.value.status_code == 401


def test_validate_admin_credentials_accepts_correct_credentials(auth_service):
    assert auth_service.validate_admin_credentials("test-admin", "test-password") is True


@pytest.mark.parametrize(
    ("username", "password"),
    [
        ("test-admin", "wrong-password"),
        ("wrong-admin", "test-password"),
        ("", ""),
    ],
)
def test_validate_admin_credentials_rejects_invalid_credentials(auth_service, username, password):
    assert auth_service.validate_admin_credentials(username, password) is False


def test_tokens_created_at_different_times_have_different_expiry_values(auth_service, monkeypatch):
    now = 1000
    monkeypatch.setattr(auth_module.time, "time", lambda: now)
    first_payload = auth_service.verify_access_token(auth_service.create_access_token("test-admin"))

    now = 1005
    second_payload = auth_service.verify_access_token(auth_service.create_access_token("test-admin"))

    assert first_payload["exp"] == 1060
    assert second_payload["exp"] == 1065
    assert first_payload["exp"] != second_payload["exp"]
