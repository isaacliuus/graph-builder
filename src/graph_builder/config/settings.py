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
    #TODO: move this to the .env file
    openai_api_key: str = "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"
    llm_model: str = "gpt-4o-mini"

    # Extraction settings
    use_llm: bool = False

    # Graph settings
    deduplicate_entities: bool = True


def get_settings() -> Settings:
    """Get application settings."""
    return Settings()
