"""
Application configuration loaded from environment variables.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings from environment variables."""

    model_config = SettingsConfigDict(
        env_file = ".env",
        env_file_encoding = "utf-8"
    )
    
    # Database
    database_url: str = Field(default="sqlite+aiosqlite:///./dmrv.db", alias="DATABASE_URL")
    
    # NASA POWER API
    nasa_power_base_url: str = Field(default="https://power.larc.nasa.gov/api/temporal/daily/point", alias="NASA_POWER_BASE_URL")
    
    # Application
    app_name: str = Field(default="Lumix dMRV Engine", alias="APP_NAME")
    app_version: str = Field(default="0.1.0", alias="APP_VERSION")
    debug: bool = Field(default=False, alias="DEBUG")
    port: int = Field(alias="PORT")

    


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

