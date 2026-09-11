"""Environment configuration and target database validation."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Mapping


DATABASE_NAME_PATTERN = re.compile(r"\Alabdb_[a-z0-9_]+\Z")
REQUIRED_VARIABLES = (
    "LABDB_HOST",
    "LABDB_PORT",
    "LABDB_USER",
    "LABDB_PASSWORD",
    "LABDB_DATABASE",
)


class ConfigurationError(ValueError):
    """Raised when required database configuration is missing or invalid."""


@dataclass(frozen=True)
class DatabaseConfig:
    host: str
    port: int
    user: str
    password: str
    database: str


def validate_database_name(name: str) -> str:
    if not isinstance(name, str) or not DATABASE_NAME_PATTERN.fullmatch(name):
        raise ConfigurationError(
            "LABDB_DATABASE must match labdb_[a-z0-9_]+ exactly; "
            "system, historical, empty, uppercase, quoted, spaced, and punctuated names are refused"
        )
    return name


def _parse_port(raw_port: str) -> int:
    if not raw_port or not raw_port.isascii() or not raw_port.isdecimal():
        raise ConfigurationError("LABDB_PORT must be an integer from 1 through 65535")
    port = int(raw_port)
    if not 1 <= port <= 65535:
        raise ConfigurationError("LABDB_PORT must be an integer from 1 through 65535")
    return port


def load_config(environ: Mapping[str, str] | None = None) -> DatabaseConfig:
    source = os.environ if environ is None else environ
    missing = [name for name in REQUIRED_VARIABLES if not source.get(name)]
    if missing:
        raise ConfigurationError(
            "Missing or empty required environment variables: " + ", ".join(missing)
        )

    return DatabaseConfig(
        host=source["LABDB_HOST"],
        port=_parse_port(source["LABDB_PORT"]),
        user=source["LABDB_USER"],
        password=source["LABDB_PASSWORD"],
        database=validate_database_name(source["LABDB_DATABASE"]),
    )
