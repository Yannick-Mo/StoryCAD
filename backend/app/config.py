from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:postgres@db:5432/storyforge"
    redis_url: str = "redis://redis:6379/0"
    jwt_secret_key: str = ""
    jwt_expire_hours: int = 24

    # LLM configuration
    deepseek_api_key: str = ""      # deprecated, use llm_api_key
    llm_api_key: str = ""
    llm_base_url: str = "https://api.deepseek.com/v1"
    llm_model: str = "deepseek-chat"

    class Config:
        env_file = ".env"


settings = Settings()
