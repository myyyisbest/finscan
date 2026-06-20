"""JWT 鉴权工具：密码哈希 + Token 创建/验证 + 当前用户依赖。"""
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import AuthError
from app.db import get_db
from app.models import User


_pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
_bearer = HTTPBearer(auto_error=False)


# ---- 密码 ----

def hash_password(raw: str) -> str:
    return _pwd_context.hash(raw)


def verify_password(raw: str, hashed: str) -> bool:
    return _pwd_context.verify(raw, hashed)


# ---- Token ----

def create_access_token(sub: str | int, expires_delta: timedelta | None = None) -> str:
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload = {"sub": str(sub), "exp": expire, "iat": datetime.now(timezone.utc)}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError as exc:
        raise AuthError(f"Token 无效或已过期: {exc}")


# ---- 依赖 ----

def get_current_user_id(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> int:
    """从 Bearer Token 提取 user_id。未登录返回 None（用于可选认证）。"""
    if credentials is None:
        raise AuthError("请先登录")
    payload = decode_token(credentials.credentials)
    uid = payload.get("sub")
    if not uid:
        raise AuthError("Token payload 异常")
    return int(uid)


def get_current_user(
    user_id: Annotated[int, Depends(get_current_user_id)],
    db: Session = Depends(get_db),
) -> User:
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise AuthError("用户不存在或已禁用")
    return user


# ---- 可选认证（不需要强制登录但可获取用户ID）----

def get_optional_user_id(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> int | None:
    """可选认证：有 token 返回 user_id，否则返回 None。"""
    if credentials is None:
        return None
    try:
        payload = decode_token(credentials.credentials)
        return int(payload.get("sub", 0))
    except AuthError:
        return None
