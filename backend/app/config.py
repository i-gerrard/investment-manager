from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Use SQLite for local dev; set DATABASE_URL env var for PostgreSQL
    DATABASE_URL: str = "sqlite+aiosqlite:///./investr.db"
    SECRET_KEY: str = "dev-secret-change-in-production"
    CORS_ORIGINS: str = "http://localhost:3000"
    API_V1_PREFIX: str = "/api/v1"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    OPEN_BROWSER: bool = True

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
