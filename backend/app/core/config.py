"""Application configuration using Pydantic Settings"""
from functools import lru_cache
from typing import List
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Application
    app_name: str = "Ink Inventory Management"
    environment: str = "development"
    debug: bool = True
    api_v1_prefix: str = "/api/v1"

    # Database
    database_url: str = ""
    db_echo: bool = False

    # Security
    secret_key: str = ""
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # CORS — set via CORS_ORIGINS env var (comma-separated string)
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @model_validator(mode="before")
    @classmethod
    def parse_database_url(cls, values):
        # Railway/Render/Neon give postgresql:// but SQLAlchemy async needs postgresql+asyncpg://
        db_url = values.get("database_url", "")
        if isinstance(db_url, str) and db_url.startswith("postgresql://"):
            values["database_url"] = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return values
    
    # Alert Thresholds (days before expiration)
    alert_threshold_120: int = 120
    alert_threshold_90: int = 90
    alert_threshold_60: int = 60
    alert_threshold_30: int = 30
    
    # Dead Stock Threshold
    dead_stock_days: int = 180
    
    # Email Settings (Resend)
    resend_api_key: str = ""
    email_from: str = "Lino Inventory <onboarding@resend.dev>"
    
    @property
    def is_development(self) -> bool:
        return self.environment == "development"
    
    @property
    def is_production(self) -> bool:
        return self.environment == "production"
    
    @property
    def alert_thresholds(self) -> List[int]:
        """Returns sorted list of alert thresholds"""
        return sorted([
            self.alert_threshold_120,
            self.alert_threshold_90,
            self.alert_threshold_60,
            self.alert_threshold_30
        ], reverse=True)


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance"""
    s = Settings()
    if not s.secret_key:
        raise ValueError("SECRET_KEY env var is required. Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(32))\"")
    return s


settings = get_settings()


