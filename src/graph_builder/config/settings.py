"""Application settings using pydantic-settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_prefix="GRAPH_BUILDER_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Chunking settings
    chunk_size: int = 1000
    chunk_overlap: int = 200

    # spaCy settings
    spacy_model: str = "en_core_web_sm"

    # LLM settings
    openai_api_key: str = ""
    llm_model: str = "gpt-4o-mini"

    # Extraction settings
    use_llm: bool = False

    # Graph settings
    deduplicate_entities: bool = True


def get_settings() -> Settings:
    """Get application settings."""
    return Settings()
