"""Environment based configuration for the local demo."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Application paths and safe defaults for a laptop-sized demo."""

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_name: str = "TVH Findability Demo"
    app_host: str = "127.0.0.1"
    app_port: int = Field(default=8000, ge=1, le=65535)
    log_level: str = "INFO"
    data_dir: Path = Path("data")
    index_path: Path = Path("models/catalog_index.json")
    recommendations_path: Path = Path("models/recommendations.json")
    max_pages_per_pdf: int = Field(default=0, ge=0)
    search_result_limit: int = Field(default=10, ge=1, le=50)
    openai_api_key: str | None = None
    openai_model: str = "gpt-5"

    @model_validator(mode="after")
    def resolve_paths(self) -> "Settings":
        """Resolve relative paths once, consistently from the project root."""
        for field_name in ("data_dir", "index_path", "recommendations_path"):
            value = getattr(self, field_name)
            if not value.is_absolute():
                setattr(self, field_name, PROJECT_ROOT / value)
        return self

    def ensure_directories(self) -> None:
        """Create persistent storage folders when the app starts."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self.recommendations_path.parent.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return one validated settings object per process."""
    return Settings()
