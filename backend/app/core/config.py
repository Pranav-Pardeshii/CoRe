import ssl
from functools import lru_cache
from pathlib import Path
from typing import Literal

from fastapi import Request
from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL

_REPO_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_ENV_FILE = _REPO_ROOT / "backend" / ".env"


class Settings(BaseSettings):
    """Application settings loaded from environment variables and backend/.env."""

    model_config = SettingsConfigDict(
        env_file=_DEFAULT_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    ENVIRONMENT: Literal["development", "testing", "production"] = Field(
        default="development",
        validation_alias=AliasChoices("CORE_ENVIRONMENT", "ENVIRONMENT"),
    )
    LOG_LEVEL: str = Field(
        default="INFO",
        validation_alias=AliasChoices("CORE_LOG_LEVEL", "LOG_LEVEL"),
    )
    GCP_PROJECT_ID: str | None = Field(
        default=None,
        validation_alias=AliasChoices("CORE_GCP_PROJECT_ID", "GOOGLE_CLOUD_PROJECT"),
    )
    CORS_ORIGINS: list[str] = Field(
        default_factory=lambda: ["http://localhost:8501", "http://127.0.0.1:8501"],
        validation_alias=AliasChoices("CORE_CORS_ORIGINS", "CORS_ORIGINS"),
    )
    TRUSTED_PROXY_IPS: list[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices("CORE_TRUSTED_PROXY_IPS", "TRUSTED_PROXY_IPS"),
    )
    TRUSTED_PROXY_HOPS: int = Field(
        default=0,
        ge=0,
        validation_alias=AliasChoices("CORE_TRUSTED_PROXY_HOPS", "TRUSTED_PROXY_HOPS"),
    )

    DB_HOST: str | None = Field(
        default=None,
        validation_alias=AliasChoices("CORE_DB_HOST", "DB_HOST"),
    )
    DB_UNIX_SOCKET: str | None = Field(
        default=None,
        validation_alias=AliasChoices("CORE_DB_UNIX_SOCKET", "DB_UNIX_SOCKET"),
    )
    DB_USER: str = Field(validation_alias=AliasChoices("CORE_DB_USER", "DB_USER"))
    DB_PORT: int = Field(default=3306, validation_alias=AliasChoices("CORE_DB_PORT", "DB_PORT"))
    DB_PASS: str = Field(validation_alias=AliasChoices("CORE_DB_PASS", "DB_PASS"))
    DB_NAME: str = Field(validation_alias=AliasChoices("CORE_DB_NAME", "DB_NAME"))
    DB_SSL_CA: str | None = Field(
        default=None,
        validation_alias=AliasChoices("CORE_DB_SSL_CA", "DB_SSL_CA"),
    )

    SECRET_KEY: str = Field(validation_alias=AliasChoices("CORE_SECRET_KEY", "SECRET_KEY"))
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=60,
        ge=1,
        validation_alias=AliasChoices(
            "CORE_ACCESS_TOKEN_EXPIRE_MINUTES",
            "ACCESS_TOKEN_EXPIRE_MINUTES",
        ),
    )

    DB_POOL_SIZE: int = Field(
        default=2,
        ge=1,
        validation_alias=AliasChoices("CORE_DB_POOL_SIZE", "DB_POOL_SIZE"),
    )
    DB_MAX_OVERFLOW: int = Field(
        default=3,
        ge=0,
        validation_alias=AliasChoices("CORE_DB_MAX_OVERFLOW", "DB_MAX_OVERFLOW"),
    )
    DB_POOL_TIMEOUT: int = Field(
        default=5,
        ge=1,
        validation_alias=AliasChoices("CORE_DB_POOL_TIMEOUT", "DB_POOL_TIMEOUT"),
    )
    DB_CONNECT_TIMEOUT: int = Field(
        default=5,
        ge=1,
        validation_alias=AliasChoices("CORE_DB_CONNECT_TIMEOUT", "DB_CONNECT_TIMEOUT"),
    )
    DB_POOL_RECYCLE: int = Field(
        default=1800,
        ge=60,
        validation_alias=AliasChoices("CORE_DB_POOL_RECYCLE", "DB_POOL_RECYCLE"),
    )

    AUTH_RATE_LIMIT_MAX_REQUESTS: int = Field(
        default=20,
        ge=1,
        validation_alias=AliasChoices(
            "CORE_AUTH_RATE_LIMIT_MAX_REQUESTS",
            "AUTH_RATE_LIMIT_MAX_REQUESTS",
        ),
    )
    AUTH_RATE_LIMIT_WINDOW_SECONDS: int = Field(
        default=60,
        ge=1,
        validation_alias=AliasChoices(
            "CORE_AUTH_RATE_LIMIT_WINDOW_SECONDS",
            "AUTH_RATE_LIMIT_WINDOW_SECONDS",
        ),
    )
    AUTH_LOGIN_USERNAME_MAX_ATTEMPTS: int = Field(
        default=10,
        ge=1,
        validation_alias=AliasChoices(
            "CORE_AUTH_LOGIN_USERNAME_MAX_ATTEMPTS",
            "AUTH_LOGIN_USERNAME_MAX_ATTEMPTS",
        ),
    )
    PUBLIC_RATE_LIMIT_MAX_REQUESTS: int = Field(
        default=60,
        ge=1,
        validation_alias=AliasChoices(
            "CORE_PUBLIC_RATE_LIMIT_MAX_REQUESTS",
            "PUBLIC_RATE_LIMIT_MAX_REQUESTS",
        ),
    )
    PUBLIC_RATE_LIMIT_WINDOW_SECONDS: int = Field(
        default=60,
        ge=1,
        validation_alias=AliasChoices(
            "CORE_PUBLIC_RATE_LIMIT_WINDOW_SECONDS",
            "PUBLIC_RATE_LIMIT_WINDOW_SECONDS",
        ),
    )

    RECOMMENDER_YEARS: list[int] | None = Field(
        default=None,
        validation_alias=AliasChoices("CORE_RECOMMENDER_YEARS", "RECOMMENDER_YEARS"),
    )

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, value: str) -> str:
        """Ensure a non-empty JWT signing secret is configured."""
        if not value or not value.strip():
            raise ValueError("SECRET_KEY must be set and non-empty.")
        return value

    @field_validator("DB_USER", "DB_NAME")
    @classmethod
    def validate_non_empty_db_field(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("Database configuration fields must be non-empty.")
        return value

    @model_validator(mode="after")
    def validate_production_and_db_transport(self) -> "Settings":
        """Validate DB transport and production security constraints."""
        has_host = bool(self.DB_HOST and self.DB_HOST.strip())
        has_socket = bool(self.DB_UNIX_SOCKET and self.DB_UNIX_SOCKET.strip())
        if not has_host and not has_socket:
            raise ValueError("Either DB_HOST or DB_UNIX_SOCKET must be set.")

        if self.ENVIRONMENT == "production":
            if len(self.SECRET_KEY.strip()) < 32:
                raise ValueError("SECRET_KEY must be at least 32 characters in production.")
            if "*" in self.CORS_ORIGINS:
                raise ValueError("CORS_ORIGINS must not contain '*' in production.")

        return self

    @property
    def async_database_url(self) -> URL:
        """Build a safe SQLAlchemy asyncmy URL without manual string concatenation."""
        use_socket = bool(self.DB_UNIX_SOCKET and self.DB_UNIX_SOCKET.strip())
        return URL.create(
            drivername="mysql+asyncmy",
            username=self.DB_USER,
            password=self.DB_PASS,
            host=None if use_socket else self.DB_HOST,
            port=None if use_socket else self.DB_PORT,
            database=self.DB_NAME,
        )

    def resolve_ssl_ca_path(self) -> Path | None:
        """Resolve the SSL CA path against the repo root when given as a relative path."""
        if not self.DB_SSL_CA or not self.DB_SSL_CA.strip():
            return None
        candidate = Path(self.DB_SSL_CA)
        if candidate.is_absolute():
            return candidate
        repo_relative = _REPO_ROOT / candidate
        if repo_relative.exists():
            return repo_relative
        backend_relative = _REPO_ROOT / "backend" / candidate
        if backend_relative.exists():
            return backend_relative
        if candidate.exists():
            return candidate
        return candidate

    def build_ssl_context(self) -> ssl.SSLContext | None:
        """Create a verifying SSL context when DB_SSL_CA is configured."""
        ca_path = self.resolve_ssl_ca_path()
        if ca_path is None:
            return None
        if not ca_path.exists():
            raise FileNotFoundError(f"Configured DB_SSL_CA file not found: {ca_path}")
        return ssl.create_default_context(cafile=str(ca_path))


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()  # type: ignore[call-arg]


def get_app_settings(request: Request) -> Settings:
    """Return the Settings instance bound to the active FastAPI application state."""
    return request.app.state.settings
