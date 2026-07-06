from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:postgres@db:5432/storyforge"
    redis_url: str = "redis://redis:6379/0"
    jwt_secret_key: str = ""
    jwt_expire_hours: int = 24
    deepseek_api_key: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
