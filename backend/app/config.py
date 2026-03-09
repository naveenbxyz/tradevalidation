import os
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # API Settings
    app_name: str = "Markets Trade Validator API"
    debug: bool = True

    # LLM Settings
    openai_api_key: Optional[str] = None
    openai_base_url: Optional[str] = None
    llm_model: str = "gpt-4.1-mini"
    verify_ssl: bool = True
    stream: bool = False
    llm_temperature: float = 0.0
    llm_timeout: int = 120
    llm_send_images: bool = False  # Set True only if your LLM supports multipart image_url

    # Data & file paths
    database_path: str = "../data/database.json"
    upload_dir: str = "../data/uploads"
    ingest_scan_dir: str = "../data/inbox"
    trs_schema_path: str = "app/schema_configs/trs_schema.json"

    # Local LLM (on-device inference engine, e.g. Qwen3-8B-MLX)
    local_llm_enabled: bool = False
    local_llm_base_url: str = "http://localhost:8080/v1"
    local_llm_model: str = "qwen3-8b-mlx-4bit"
    local_llm_timeout: int = 300  # local models can be slow
    local_llm_temperature: float = 0.0
    local_llm_max_tokens: int = 4096

    # Controls
    max_file_size: int = 20 * 1024 * 1024  # 20MB
    auto_pass_threshold: float = 0.85
    max_content_chars: int = 50000  # Max chars of text content sent to LLM (~12.5K tokens)

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()

os.makedirs(settings.upload_dir, exist_ok=True)
os.makedirs(settings.ingest_scan_dir, exist_ok=True)
