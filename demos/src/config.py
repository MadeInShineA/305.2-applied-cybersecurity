import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass
class Config:
    """Data class for storing Telegram API configuration."""
    telegram_api_id: str
    telegram_api_hash: str


def load_config() -> Config:
    """
    Load configuration from environment variables.
    
    Reads TG_API_ID and TG_API_HASH from .env file or system environment.
    Returns a Config dataclass with the loaded values.
    """
    load_dotenv()
    return Config(
        telegram_api_id=os.getenv("TG_API_ID", ""),
        telegram_api_hash=os.getenv("TG_API_HASH", ""),
    )