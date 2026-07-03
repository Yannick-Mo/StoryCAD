from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:postgres@db:5432/storyforge"
    neo4j_uri: str = "bolt://neo4j:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password"
    redis_url: str = "redis://redis:6379/0"
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    model_name: str = "deepseek-chat"
    llm_provider: str = "deepseek"
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"

    class Config:
        env_file = ".env"


settings = Settings()
