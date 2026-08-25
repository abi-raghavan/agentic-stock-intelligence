from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:3b"
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "stock_documents"
    database_url: str = "sqlite:///./data/stock_intel.db"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: str = "http://localhost:3000"
    enable_live_data: bool = False
    seed_data_on_startup: bool = True
    log_level: str = "INFO"
    sample_data_dir: str = "sample_data"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
