"""
============================================================
config.py — Centralized Application Configuration
============================================================
Loads all environment variables and provides typed settings
used across every module in the application.
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache
import os


class Settings(BaseSettings):
    """
    Application settings loaded from .env file.
    All values have sensible defaults so the app
    runs even without a .env file configured.
    """

    # ── App ──────────────────────────────────────────────
    APP_NAME: str = "Weather Forecast & Alert Application"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # ── Database ─────────────────────────────────────────
    DATABASE_URL: str = "sqlite:///./db/weather.db"

    # ── Open-Meteo API ───────────────────────────────────
    OPEN_METEO_BASE_URL: str = "https://api.open-meteo.com/v1/forecast"

    # ── Alert Thresholds ─────────────────────────────────
    RAIN_PROBABILITY_THRESHOLD: float = 60.0   # percent
    HEAT_TEMPERATURE_THRESHOLD: float = 40.0   # °C
    WIND_GUST_THRESHOLD: float = 60.0          # km/h
    UV_INDEX_THRESHOLD: float = 8.0            # UV index

    # ── Scheduler ────────────────────────────────────────
    REFRESH_INTERVAL_MINUTES: int = 180        # 3 hours

    # ── Email Notifications ──────────────────────────────
    EMAIL_ENABLED: bool = False
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    ALERT_RECIPIENT: str = ""

    # ── Telegram Notifications ───────────────────────────
    TELEGRAM_ENABLED: bool = False
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """
    Returns a cached Settings instance.
    Using lru_cache ensures we only read .env once.
    """
    return Settings()


# Module-level shortcut used across the codebase
settings = get_settings()
