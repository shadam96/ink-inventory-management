"""Application configuration using Pydantic Settings"""
from functools import lru_cache
from typing import List
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
    database_url: str = "postgresql+asyncpg://inventory_user:inventory_pass_2024@localhost:5432/inventory_db"
    db_echo: bool = False
    
    # Redis
    redis_url: str = "redis://localhost:6379"
    
    # Security
    secret_key: str = "your-super-secret-key-change-in-production-min-32-chars"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    
    # CORS
    cors_origins: List[str] = ["http://localhost:5173", "http://localhost:3000"]
    
    # Alert Thresholds (days before expiration)
    alert_threshold_120: int = 120
    alert_threshold_90: int = 90
    alert_threshold_60: int = 60
    alert_threshold_30: int = 30
    
    # Dead Stock Threshold
    dead_stock_days: int = 180
    
    # Email Settings
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    email_from: str = "noreply@linoprint.com"
    
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
    return Settings()


settings = get_settings()


