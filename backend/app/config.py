from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://investr:changeme@localhost:5432/investment_manager"
    SECRET_KEY: str = "dev-secret-change-in-production"
    CORS_ORIGINS: str = "http://localhost:3000"
    API_V1_PREFIX: str = "/api/v1"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
