import os
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # API Settings
    app_name: str = "TRS Trade Validation API"
    debug: bool = True

    # LLM Settings
    openai_api_key: Optional[str] = None
    openai_base_url: Optional[str] = None
    llm_model: str = "gpt-4.1-mini"

    # Data & file paths
    database_path: str = "../data/database.json"
    upload_dir: str = "../data/uploads"
    ingest_scan_dir: str = "../data/inbox"
    trs_schema_path: str = "app/schema_configs/trs_schema.json"

    # Controls
    max_file_size: int = 20 * 1024 * 1024  # 20MB
    auto_pass_threshold: float = 0.85

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()

os.makedirs(settings.upload_dir, exist_ok=True)
os.makedirs(settings.ingest_scan_dir, exist_ok=True)
