from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')
    secret_key: str = 'dev-only-change-me-before-deployment'
    openai_api_key: str = ''
    openai_model: str = 'gpt-4.1-mini'
    realtime_model: str = 'gpt-realtime-2.1'
    judge0_url: str = ''  # HTTPS URL of a trusted isolated execution API
    judge0_api_key: str = ''
    judge0_api_host: str = ''
    smtp_host: str = ''
    smtp_port: int = 587
    smtp_user: str = ''
    smtp_password: str = ''
    smtp_from: str = ''
    enable_email: bool = False
    enable_reminders: bool = True
    database_url: str = 'sqlite:///./data/interviewloop.db'
    cors_origins: str = 'http://localhost:5173,http://127.0.0.1:5173'
    data_dir: str = './data'
    demo_mode: bool = False
    max_cv_mb: int = 8
    max_video_mb: int = 60

    @property
    def root(self) -> Path:
        path = Path(self.data_dir).resolve()
        path.mkdir(parents=True, exist_ok=True)
        return path


@lru_cache

def get_settings() -> Settings:
    return Settings()
