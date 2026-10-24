"""Startup configuration with explicit failure for missing required values."""

from dataclasses import dataclass
from os import environ


@dataclass(frozen=True)
class Settings:
    database_url: str


def load_settings() -> Settings:
    database_url = environ.get("DATABASE_URL", "").strip()
    if not database_url:
        raise RuntimeError("DATABASE_URL is required")
    if not database_url.startswith(("postgresql://", "postgres://")):
        raise RuntimeError("DATABASE_URL must use PostgreSQL")
    return Settings(database_url=database_url)
