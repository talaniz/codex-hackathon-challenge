from typing import Annotated
from uuid import uuid4

from fastapi import Depends, Form, HTTPException, Request, status
from itsdangerous import BadSignature, URLSafeTimedSerializer
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.responses import Response

from app.config import get_settings
from app.db import get_session
from app.models import AdminUser


SESSION_COOKIE = "codex_session"
SESSION_MAX_AGE_SECONDS = 60 * 60 * 8
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SessionDep = Annotated[Session, Depends(get_session)]


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(get_settings().secret_key, salt="codex-session")


def hash_password(password: str) -> str:
    return _pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return _pwd_context.verify(password, password_hash)


def seed_admin_user(session: Session) -> None:
    settings = get_settings()
    admin = session.scalar(select(AdminUser).where(AdminUser.username == settings.admin_username))
    if admin is not None:
        return
    session.add(AdminUser(username=settings.admin_username, password_hash=hash_password(settings.admin_password)))
    session.commit()


def authenticate_admin(session: Session, username: str, password: str) -> AdminUser | None:
    admin = session.scalar(select(AdminUser).where(AdminUser.username == username))
    if admin is None or not verify_password(password, admin.password_hash):
        return None
    return admin


def read_session(request: Request) -> dict[str, object]:
    cookie = request.cookies.get(SESSION_COOKIE)
    if cookie is None:
        return {}
    try:
        data = _serializer().loads(cookie, max_age=SESSION_MAX_AGE_SECONDS)
    except BadSignature:
        return {}
    return data if isinstance(data, dict) else {}


def write_session(response: Response, data: dict[str, object]) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        _serializer().dumps(data),
        httponly=True,
        samesite="lax",
        max_age=SESSION_MAX_AGE_SECONDS,
    )


def clear_session(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE)


def ensure_csrf_token(request: Request) -> tuple[str, dict[str, object]]:
    session_data = read_session(request)
    token = str(session_data.get("csrf_token") or uuid4())
    session_data["csrf_token"] = token
    return token, session_data


def require_admin(request: Request, session: SessionDep) -> AdminUser:
    session_data = read_session(request)
    admin_id = session_data.get("admin_id")
    if not isinstance(admin_id, int):
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": "/admin/login"},
        )
    admin = session.get(AdminUser, admin_id)
    if admin is None:
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": "/admin/login"},
        )
    return admin


def validate_csrf(request: Request, csrf_token: Annotated[str, Form()]) -> None:
    session_data = read_session(request)
    expected = session_data.get("csrf_token")
    if not isinstance(expected, str) or csrf_token != expected:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid CSRF token")
