from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
  """Настройки приложения. Читаются из .env и переменных окружения."""

  keitaro_base_url: str = Field(
    default="https://tlgk.host/admin_api/v1",
    description="Базовый URL Admin API Keitaro (без слеша в конце)",
  )
  keitaro_api_key: str = Field(
    ...,
    description="API-ключ Keitaro (из админки: Admin → API)",
  )

  database_url: str = Field(
    default="postgresql+asyncpg://postgres:postgres@localhost:5432/streamflow",
    description="DSN для async SQLAlchemy (драйвер asyncpg)",
  )

  app_debug: bool = Field(
    default=False,
    description="Режим отладки (влияет на логи и Swagger)",
  )

  model_config = SettingsConfigDict(
    env_file=".env",
    env_file_encoding="utf-8",
    case_sensitive=False,
    extra="ignore",
  )


settings = Settings()