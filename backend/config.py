from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    openai_api_key: str = ""
    tavily_api_key: str = ""
    api_key: str = "dev-secret"

    llm_model: str = "gpt-4o"
    embedding_model: str = "text-embedding-3-small"

    data_dir: str = "data/collections"
    chunk_size: int = 400
    chunk_overlap: int = 80

    max_retrieval_docs: int = 12
    agent_max_iterations: int = 10


@lru_cache
def get_settings() -> Settings:
    return Settings()
