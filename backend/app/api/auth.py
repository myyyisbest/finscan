"""认证 API：注册 / 登录 / 当前用户。"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth import hash_password, verify_password, create_access_token, get_current_user
from app.core.exceptions import BizException, AuthError
from app.core.response import ok
from app.db import get_db
from app.models import User


router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class RegisterIn(BaseModel):
    username: str
    password: str
    email: str | None = None


class LoginIn(BaseModel):
    username: str
    password: str


@router.post("/register")
def register(body: RegisterIn, db: Session = Depends(get_db)):
    exists = db.query(User).filter(User.username == body.username).first()
    if exists:
        raise BizException(1001, "用户名已存在")
    user = User(
        username=body.username,
        hashed_password=hash_password(body.password),
        email=body.email,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(user.id)
    return ok({
        "access_token": token,
        "token_type": "bearer",
        "user_id": user.id,
        "username": user.username,
        "is_admin": user.is_admin,
    })


@router.post("/login")
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == body.username).first()
    if user is None or not verify_password(body.password, user.hashed_password):
        raise AuthError("用户名或密码错误")
    if not user.is_active:
        raise AuthError("账号已禁用")
    token = create_access_token(user.id)
    return ok({
        "access_token": token,
        "token_type": "bearer",
        "user_id": user.id,
        "username": user.username,
        "is_admin": user.is_admin,
    })


@router.get("/me")
def get_me(user: User = Depends(get_current_user)):
    return ok({
        "user_id": user.id,
        "username": user.username,
        "email": user.email,
        "is_active": user.is_active,
        "is_admin": user.is_admin,
    })
