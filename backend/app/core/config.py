from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://postgres:postgres@localhost:5432/edureg"
    qdrant_url: str = "http://localhost:6333"
    llm_provider: str = "openai"
    openai_api_key: str = ""
    llm_model: str = "gpt-4.1-mini"
    embedding_model: str = "text-embedding-3-small"

    class Config:
        env_file = ".env"


settings = Settings()
