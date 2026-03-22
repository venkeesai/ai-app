from __future__ import annotations

from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Tamil Newsroom Translator"
    environment: str = "development"
    tesseract_cmd: str | None = None
    translation_model: str = "Helsinki-NLP/opus-mt-ta-en"
    use_transformers: bool = True
    storage_dir: Path = Field(default=Path("storage"))
    export_dir: Path = Field(default=Path("storage/exports"))
    asset_dir: Path = Field(default=Path("storage/assets"))

    model_config = SettingsConfigDict(env_prefix="NEWSROOM_", env_file=".env", extra="ignore")


settings = Settings()
settings.storage_dir.mkdir(parents=True, exist_ok=True)
settings.export_dir.mkdir(parents=True, exist_ok=True)
settings.asset_dir.mkdir(parents=True, exist_ok=True)
