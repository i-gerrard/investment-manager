import hashlib
import secrets
from datetime import datetime, timedelta

from fastapi import HTTPException, status
from jose import jwt
from passlib.context import CryptContext
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
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
from app.services.base import BaseService

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_token(user_id: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": user_id, "exp": expire}, settings.SECRET_KEY, algorithm="HS256")


class AuthService:
    def __init__(self):
        self.base = BaseService[User, UserRegister, UserRegister, UserResponse](User, UserResponse)

    async def register(self, db: AsyncSession, body: UserRegister) -> TokenResponse:
        result = await db.execute(select(User).where(User.username == body.username))
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Username already taken"
            )
        user = User(
            username=body.username,
            password_hash=pwd_context.hash(body.password),
            email=body.email,
        )
        db.add(user)
        await db.flush()
        token = create_token(user.id)
        result = TokenResponse(token=token, user=UserResponse.model_validate(user))
        await db.commit()
        return result

    async def login(self, db: AsyncSession, body: UserLogin) -> TokenResponse:
        result = await db.execute(select(User).where(User.username == body.username))
        user = result.scalar_one_or_none()
        if not user or not pwd_context.verify(body.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
            )
        token = create_token(user.id)
        return TokenResponse(token=token, user=UserResponse.model_validate(user))

    async def create_api_key(
        self, db: AsyncSession, user_id: str, body: ApiKeyCreate
    ) -> ApiKeyResponse:
        raw_key = "investr_" + secrets.token_urlsafe(32)
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        api_key = ApiKey(user_id=user_id, key_hash=key_hash, name=body.name)
        db.add(api_key)
        await db.flush()
        result = ApiKeyResponse(
            id=api_key.id, key=raw_key, name=api_key.name, last_used_at=None
        )
        await db.commit()
        return result

    async def list_api_keys(self, db: AsyncSession, user_id: str) -> list[ApiKeyListResponse]:
        result = await db.execute(select(ApiKey).where(ApiKey.user_id == user_id))
        return [ApiKeyListResponse.model_validate(k) for k in result.scalars().all()]

    async def delete_api_key(self, db: AsyncSession, key_id: str, user_id: str) -> None:
        result = await db.execute(
            select(ApiKey).where(ApiKey.id == key_id, ApiKey.user_id == user_id)
        )
        key = result.scalar_one_or_none()
        if not key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="API key not found"
            )
        await db.delete(key)
        await db.commit()
