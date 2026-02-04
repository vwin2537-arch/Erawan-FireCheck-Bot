from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
from functools import lru_cache

class Settings(BaseSettings):
    # App Configuration
    APP_NAME: str = "FIRMS LINE Bot"
    APP_ENV: str = "development"
    DEBUG: bool = False
    SECRET_KEY: str = "your-secret-key-here"

    # NASA FIRMS API
    FIRMS_MAP_KEY: str = ""
    
    # LINE Messaging API
    LINE_CHANNEL_ACCESS_TOKEN: str = ""
    LINE_CHANNEL_SECRET: str = ""
    LINE_GROUP_ID: str = ""

    # Database (Railway provides DATABASE_URL automatically for Postgres)
    DATABASE_URL: str = "sqlite+aiosqlite:///./firms_bot.db"

    # Monitoring Area (Kanchanaburi)
    AREA_WEST: float = 98.0
    AREA_SOUTH: float = 13.4
    AREA_EAST: float = 100.0
    AREA_NORTH: float = 15.8

    # Scheduler Settings
    TIMEZONE: str = "Asia/Bangkok"
    CHECK_INTERVAL_PEAK: int = 10
    CHECK_INTERVAL_OFFPEAK: int = 30

    # Notification Settings
    MIN_CONFIDENCE: str = "nominal"
    NOTIFY_ON_STARTUP: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

@lru_cache()
def get_settings():
    return Settings()
