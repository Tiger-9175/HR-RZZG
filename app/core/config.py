"""Application configuration."""
import json
import os
import logging
from pydantic_settings import BaseSettings
from typing import Optional

logger = logging.getLogger(__name__)

# Config file path for persisting runtime LLM configuration changes
CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "llm_config.json")


class Settings(BaseSettings):
    # Application
    app_name: str = "昌飞任职资格智能评价系统"
    app_version: str = "1.0.0"
    debug: bool = False

    # LLM Configuration
    llm_api_key: str = "sk-placeholder"
    llm_base_url: str = "http://localhost:8000/v1"
    llm_model: str = "qwen2.5-72b-instruct"
    llm_max_tokens: int = 8192
    llm_temperature: float = 0.3

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # File paths
    upload_dir: str = "uploads"
    data_dir: str = "data"
    demo_dir: str = "demo"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()


def load_config_from_file():
    """Load LLM config from persisted JSON file, overriding env defaults.
    Called once at startup so runtime changes survive container restarts.

    Returns True if config was loaded from file, False otherwise.
    """
    if not os.path.exists(CONFIG_FILE):
        return False
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        # An empty config file (e.g. cleared before publishing) is not a
        # usable configuration: leave the env/default values in place.
        loaded = False
        if data.get("llm_api_key"):
            settings.llm_api_key = data["llm_api_key"]
            loaded = True
        if data.get("llm_base_url"):
            settings.llm_base_url = data["llm_base_url"]
        if data.get("llm_model"):
            settings.llm_model = data["llm_model"]
        logger.info(f"Loaded LLM config from {CONFIG_FILE}: model={settings.llm_model}, url={settings.llm_base_url}")
        return loaded
    except Exception as e:
        logger.warning(f"Failed to load config file: {e}")
        return False


def save_config_to_file():
    """Persist current LLM config to JSON file."""
    try:
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "llm_api_key": settings.llm_api_key,
                "llm_base_url": settings.llm_base_url,
                "llm_model": settings.llm_model,
            }, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved LLM config to {CONFIG_FILE}")
    except Exception as e:
        logger.warning(f"Failed to save config file: {e}")
