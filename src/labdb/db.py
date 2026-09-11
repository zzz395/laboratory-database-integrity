"""Low-level MySQL connection setup."""

from __future__ import annotations

import pymysql
from pymysql.connections import Connection
from pymysql.cursors import DictCursor

from .config import DatabaseConfig


STRICT_SQL_MODE = "STRICT_TRANS_TABLES,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION"


class DatabaseConnectionError(RuntimeError):
    """Raised when a safe database session cannot be established."""


def connect_server(config: DatabaseConfig) -> Connection:
    connection: Connection | None = None
    try:
        connection = pymysql.connect(
            host=config.host,
            port=config.port,
            user=config.user,
            password=config.password,
            charset="utf8mb4",
            cursorclass=DictCursor,
            autocommit=True,
            connect_timeout=10,
            read_timeout=30,
            write_timeout=30,
            ssl={"check_hostname": False},
        )
        with connection.cursor() as cursor:
            cursor.execute("SET SESSION foreign_key_checks = 1")
            cursor.execute("SET SESSION sql_mode = %s", (STRICT_SQL_MODE,))
            cursor.execute("SET SESSION time_zone = '+00:00'")
            cursor.execute(
                "SELECT @@SESSION.foreign_key_checks AS fk_checks, "
                "@@SESSION.time_zone AS time_zone, @@SESSION.sql_mode AS sql_mode"
            )
            session = cursor.fetchone()
        actual_modes = set(session["sql_mode"].split(","))
        expected_modes = set(STRICT_SQL_MODE.split(","))
        if (
            session["fk_checks"] != 1
            or session["time_zone"] != "+00:00"
            or not expected_modes.issubset(actual_modes)
        ):
            connection.close()
            connection = None
            raise DatabaseConnectionError(
                "MySQL session safety settings could not be confirmed"
            )
        return connection
    except DatabaseConnectionError:
        if connection is not None:
            connection.close()
        raise
    except (pymysql.MySQLError, RuntimeError) as exc:
        if connection is not None:
            connection.close()
        raise DatabaseConnectionError(
            f"MySQL connection or session setup failed: {exc}"
        ) from exc
