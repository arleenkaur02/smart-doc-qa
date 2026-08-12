from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # OpenAI
    openai_api_key: str
    openai_embedding_model: str = "text-embedding-3-small"
    openai_chat_model: str = "gpt-4o-mini"

    # Pinecone
    pinecone_api_key: str
    pinecone_index_name: str = "smart-doc-qa"
    pinecone_environment: str = "us-east-1"
    pinecone_dimension: int = 384  # text-embedding-3-small dimension

    # App settings
    chunk_size: int = 1000
    chunk_overlap: int = 200
    max_context_chunks: int = 5

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
