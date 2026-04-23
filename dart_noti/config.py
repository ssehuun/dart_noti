import json
from pathlib import Path
from typing import Any

from pydantic.fields import FieldInfo
from pydantic_settings import BaseSettings, DotEnvSettingsSource, SettingsConfigDict


class _CommaSeparatedDotEnvSource(DotEnvSettingsSource):
    """list[str] 필드에 대해 JSON 파싱 실패 시 comma-separated 문자열로 fallback."""

    def decode_complex_value(self, field_name: str, field: FieldInfo, value: Any) -> Any:
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            if isinstance(value, str):
                return [v.strip() for v in value.split(",") if v.strip()]
            return value


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    dart_api_key: str
    telegram_bot_token: str
    telegram_chat_id: str
    watch_corp_codes: list[str]
    poll_interval_seconds: int = 300
    store_path: Path = Path("data/seen.json")
    seen_retention_days: int = 90

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: Any,
        env_settings: Any,
        dotenv_settings: Any,
        **kwargs: Any,
    ) -> tuple[Any, ...]:
        return (
            init_settings,
            env_settings,
            _CommaSeparatedDotEnvSource(
                settings_cls,
                env_file=".env",
                env_file_encoding="utf-8",
            ),
        )


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
