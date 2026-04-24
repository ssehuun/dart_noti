from pathlib import Path
from typing import Any

from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    dart_api_key: str
    telegram_bot_token: str
    telegram_chat_id: str
    poll_interval_seconds: int = 300
    store_path: Path = Path("data/seen.json")
    seen_retention_days: int = 90


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
