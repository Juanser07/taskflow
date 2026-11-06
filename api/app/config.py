"""Configuración leída de variables de entorno (las inyecta docker-compose)."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "TaskFlow API"
    # En Docker apunta al contenedor "db": postgresql+psycopg://user:pass@db:5432/taskflow
    database_url: str = "sqlite:///./taskflow.db"
    jwt_secret: str = "dev-secret-cambiar"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 120
    seed_data: bool = False

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
