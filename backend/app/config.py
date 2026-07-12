from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:postgres@db:5432/storyforge"
    redis_url: str = "redis://redis:6379/0"
    jwt_secret_key: str = ""
    jwt_expire_hours: int = 24

    # LLM configuration
    llm_api_key: str = ""
    llm_base_url: str = "https://api.deepseek.com/v1"
    llm_model: str = "deepseek-v4-flash"
    llm_models: str = ""
    llm_fallback_models: str = ""
    llm_proxy: str = ""
    llm_max_sys_chars: int = 12000
    llm_max_rag_chars: int = 1500

    # CORS configuration
    cors_origins: list[str] = ["http://localhost:5173"]

    # Embedding configuration
    embedding_base_url: str = ""
    embedding_model: str = "text-embedding-3-small"
    embedding_api_key: str = ""
    embedding_proxy: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
