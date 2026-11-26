"""Configuration loading for the CoRe ETL pipeline."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ENV_FILE = REPO_ROOT / "backend" / ".env"
DEFAULT_PDF_DIR = REPO_ROOT / "PDFs"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "csvs"
DEFAULT_CSV_PATH = REPO_ROOT / "cutoffs_flat.csv"


def _env_or_legacy(primary: str, legacy: str, default: str | None = None) -> str | None:
    """Return primary environment variable or fallback to legacy name."""
    value = os.getenv(primary)
    if value is not None and value.strip() != "":
        return value.strip()
    legacy_value = os.getenv(legacy)
    if legacy_value is not None and legacy_value.strip() != "":
        return legacy_value.strip()
    return default


def resolve_ssl_ca_path(ssl_ca: str | None, repo_root: Path = REPO_ROOT) -> Path | None:
    """Resolve an SSL CA path against the repository root if given as a relative path."""
    if not ssl_ca or not ssl_ca.strip():
        return None
    candidate = Path(ssl_ca.strip())
    if candidate.is_absolute():
        if not candidate.exists():
            raise FileNotFoundError(f"SSL CA certificate not found at {candidate}")
        return candidate
    repo_relative = repo_root / candidate
    if repo_relative.exists():
        return repo_relative.resolve()
    backend_relative = repo_root / "backend" / candidate
    if backend_relative.exists():
        return backend_relative.resolve()
    if candidate.exists():
        return candidate.resolve()
    raise FileNotFoundError(
        f"SSL CA certificate '{ssl_ca}' not found (checked CWD, repo root, and backend/)."
    )


@dataclass(frozen=True, slots=True)
class DatabaseConfig:
    """Synchronous MySQL connection configuration for ETL."""

    user: str
    password: str
    database: str
    host: str | None = None
    port: int = 3306
    unix_socket: str | None = None
    ssl_ca: Path | None = None

    def to_connector_kwargs(self) -> dict[str, object]:
        """Build keyword arguments for ``mysql.connector.connect``."""
        kwargs: dict[str, object] = {
            "user": self.user,
            "password": self.password,
            "database": self.database,
            "use_pure": True,
        }
        if self.unix_socket:
            kwargs["unix_socket"] = self.unix_socket
        else:
            kwargs["host"] = self.host
            kwargs["port"] = self.port

        if self.ssl_ca is not None:
            kwargs["ssl_ca"] = str(self.ssl_ca)
            kwargs["ssl_verify_cert"] = True

        return kwargs


def load_db_config(
    env_file: Path | None = DEFAULT_ENV_FILE,
    repo_root: Path = REPO_ROOT,
) -> DatabaseConfig:
    """Load database settings from ``backend/.env`` (if present) and environment variables."""
    if env_file is not None and env_file.exists():
        load_dotenv(env_file, override=False)

    user = _env_or_legacy("CORE_DB_USER", "DB_USER")
    password = _env_or_legacy("CORE_DB_PASS", "DB_PASS", "")
    database = _env_or_legacy("CORE_DB_NAME", "DB_NAME")
    host = _env_or_legacy("CORE_DB_HOST", "DB_HOST")
    port_raw = _env_or_legacy("CORE_DB_PORT", "DB_PORT", "3306") or "3306"
    unix_socket = _env_or_legacy("CORE_DB_UNIX_SOCKET", "DB_UNIX_SOCKET")
    ssl_ca_raw = _env_or_legacy("CORE_DB_SSL_CA", "DB_SSL_CA")

    if not user:
        raise ValueError("Database user is required (set CORE_DB_USER or DB_USER).")
    if not database:
        raise ValueError("Database name is required (set CORE_DB_NAME or DB_NAME).")
    if not unix_socket and not host:
        raise ValueError(
            "Either CORE_DB_HOST/DB_HOST or CORE_DB_UNIX_SOCKET/DB_UNIX_SOCKET must be set."
        )

    try:
        port = int(port_raw)
    except ValueError as exc:
        raise ValueError(f"Invalid DB_PORT value: {port_raw!r}") from exc

    ssl_ca = resolve_ssl_ca_path(ssl_ca_raw, repo_root=repo_root)

    return DatabaseConfig(
        user=user,
        password=password or "",
        database=database,
        host=host,
        port=port,
        unix_socket=unix_socket,
        ssl_ca=ssl_ca,
    )
