from pathlib import Path
from pydantic_settings import BaseSettings

# Default SQLite DB next to this config file's parent (project root)
_DEFAULT_DB = str(Path(__file__).resolve().parent.parent.parent / "investr.db")


class Settings(BaseSettings):
    # Use SQLite for local dev; set DATABASE_URL env var for PostgreSQL
    DATABASE_URL: str = f"sqlite+aiosqlite:///{_DEFAULT_DB}"
    SECRET_KEY: str = "dev-secret-change-in-production"
    CORS_ORIGINS: str = "http://localhost:3000"
    API_V1_PREFIX: str = "/api/v1"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
