from pydantic import BaseModel, Field
from typing import Optional


class UserRegister(BaseModel):
    username: str = Field(min_length=2, max_length=64)
    password: str = Field(min_length=6, max_length=128)
    email: Optional[str] = None


class UserLogin(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: str
    username: str
    email: Optional[str] = None

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    token: str
    user: UserResponse


class ApiKeyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)


class ApiKeyResponse(BaseModel):
    id: str
    key: str  # only shown once on creation
    name: str
    last_used_at: Optional[str] = None

    model_config = {"from_attributes": True}


class ApiKeyListResponse(BaseModel):
    id: str
    name: str
    last_used_at: Optional[str] = None

    model_config = {"from_attributes": True}
