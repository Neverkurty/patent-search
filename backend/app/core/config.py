"""Application settings loaded from environment."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Runtime configuration."""

    model_config = SettingsConfigDict(
        env_file=(_REPO_ROOT / ".env", _REPO_ROOT / ".env.example"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = (
        "postgresql+asyncpg://paten:paten@localhost:5433/paten"
    )
    embedding_model: str = "paraphrase-multilingual-MiniLM-L12-v2"
    embedding_dimension: int = 384
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    fips_live_enabled: bool = True
    fips_live_max_results: int = 25
    fips_search_cache_ttl: int = 300
    fips_live_timeout_sec: int = 90
    chrome_version_main: int | None = None  # e.g. 148 if ChromeDriver mismatch

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def patent_schema_path(self) -> Path:
        return _REPO_ROOT / "contracts" / "patent.schema.json"

    @property
    def default_patents_json(self) -> Path:
        return _REPO_ROOT / "parser" / "output" / "patents_dump.json"


@lru_cache
def get_settings() -> Settings:
    return Settings()
