"""Application configuration using Pydantic Settings"""
import logging
from functools import lru_cache
from typing import List
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


# Query-string parameters that asyncpg's URL parser passes through to
# ``asyncpg.connect()``. Anything else in the URL becomes an unknown kwarg
# at connect time and raises TypeError. libpq supports a much larger set
# (channel_binding, application_name, connect_timeout, options, gssencmode,
# keepalives, sslrootcert, …) — none of those are accepted by asyncpg via
# the URL, so we strip them. The connection still negotiates SSL / channel
# binding / etc. correctly at the protocol level; the URL params are just
# metadata libpq would have used.
_ASYNCPG_URL_PARAM_ALLOWLIST = frozenset({"ssl", "target_session_attrs"})


def normalize_database_url(db_url: str) -> str:
    """Normalize a Postgres connection URL for the asyncpg driver.

    Transforms applied so that any operator-pasted string (Neon, Railway,
    Render, raw psql) just works:

    - ``postgresql://`` → ``postgresql+asyncpg://`` so SQLAlchemy picks the
      async dialect.
    - ``sslmode=…`` → ``ssl=…`` (asyncpg's parameter name).
    - Drops any other libpq-only query params that asyncpg doesn't accept,
      logging a warning so a real misconfiguration isn't silently lost.
    """
    if not db_url:
        return db_url

    if db_url.startswith("postgresql://"):
        db_url = "postgresql+asyncpg://" + db_url[len("postgresql://"):]

    parts = urlsplit(db_url)
    if not parts.query:
        return db_url

    pairs = parse_qsl(parts.query, keep_blank_values=True)
    kept: list[tuple[str, str]] = []
    dropped: list[str] = []
    for key, value in pairs:
        normalized_key = "ssl" if key == "sslmode" else key
        if normalized_key in _ASYNCPG_URL_PARAM_ALLOWLIST:
            kept.append((normalized_key, value))
        else:
            dropped.append(key)

    if dropped:
        logger.warning(
            "Dropped libpq-only query params from DATABASE_URL (asyncpg doesn't "
            "accept these via URL): %s",
            ", ".join(sorted(set(dropped))),
        )

    if kept != pairs:
        db_url = urlunsplit(parts._replace(query=urlencode(kept)))

    return db_url


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
        db_url = values.get("database_url", "")
        if isinstance(db_url, str):
            values["database_url"] = normalize_database_url(db_url)
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


