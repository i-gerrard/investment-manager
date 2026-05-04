import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from jose import jwt
from passlib.context import CryptContext
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.config import settings
from app.database import get_db
from app.models.user import ApiKey, User
from app.schemas.auth import (
    ApiKeyCreate,
    ApiKeyListResponse,
    ApiKeyResponse,
    TokenResponse,
    UserLogin,
    UserRegister,
    UserResponse,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_token(user_id: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": user_id, "exp": expire}, settings.SECRET_KEY, algorithm="HS256")


@router.post("/register", response_model=TokenResponse)
async def register(body: UserRegister, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(User).where(User.username == body.username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already taken")

    user = User(
        username=body.username,
        password_hash=pwd_context.hash(body.password),
        email=body.email,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_token(user.id)
    return TokenResponse(token=token, user=UserResponse.model_validate(user))


@router.post("/login", response_model=TokenResponse)
async def login(body: UserLogin, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(User).where(User.username == body.username))
    user = result.scalar_one_or_none()
    if not user or not pwd_context.verify(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = create_token(user.id)
    return TokenResponse(token=token, user=UserResponse.model_validate(user))


@router.get("/me", response_model=UserResponse)
async def me(current_user: Annotated[User, Depends(get_current_user)]):
    return UserResponse.model_validate(current_user)


@router.post("/api-keys", response_model=ApiKeyResponse)
async def create_api_key(
    body: ApiKeyCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    raw_key = "investr_" + secrets.token_urlsafe(32)
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

    api_key = ApiKey(user_id=current_user.id, key_hash=key_hash, name=body.name)
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)

    return ApiKeyResponse(id=api_key.id, key=raw_key, name=api_key.name)


@router.get("/api-keys", response_model=list[ApiKeyListResponse])
async def list_api_keys(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(ApiKey).where(ApiKey.user_id == current_user.id))
    return [ApiKeyListResponse.model_validate(k) for k in result.scalars().all()]


@router.delete("/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api_key(
    key_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(ApiKey).where(ApiKey.id == key_id, ApiKey.user_id == current_user.id))
    key = result.scalar_one_or_none()
    if not key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")
    await db.delete(key)
    await db.commit()
