from __future__ import annotations

import os

import pytest

from labdb.config import load_config
from labdb.db import connect_server
from labdb.initialize import InitializationRefused, initialize_database
from labdb.metadata import (
    EXPECTED_CHECKS,
    EXPECTED_FOREIGN_KEYS,
    EXPECTED_TABLES,
    EXPECTED_UNIQUES,
)


pytestmark = pytest.mark.integration


def _require_explicit_integration_target():
    if os.environ.get("LABDB_RUN_INTEGRATION") != "1":
        pytest.skip("set LABDB_RUN_INTEGRATION=1 only for a disposable empty labdb_* database")
    return load_config()


def _metadata_fingerprint(connection, database: str) -> tuple[tuple[object, ...], ...]:
    queries = (
        (
            "SELECT TABLE_NAME, ENGINE, TABLE_COLLATION FROM INFORMATION_SCHEMA.TABLES "
            "WHERE TABLE_SCHEMA = %s ORDER BY TABLE_NAME",
            (database,),
        ),
        (
            "SELECT TABLE_NAME, COLUMN_NAME, ORDINAL_POSITION, COLUMN_TYPE, IS_NULLABLE "
            "FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = %s "
            "ORDER BY TABLE_NAME, ORDINAL_POSITION",
            (database,),
        ),
        (
            "SELECT TABLE_NAME, CONSTRAINT_NAME, CONSTRAINT_TYPE, ENFORCED "
            "FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS WHERE CONSTRAINT_SCHEMA = %s "
            "ORDER BY TABLE_NAME, CONSTRAINT_NAME",
            (database,),
        ),
    )
    result: list[tuple[object, ...]] = []
    with connection.cursor() as cursor:
        for query, parameters in queries:
            cursor.execute(query, parameters)
            for row in cursor.fetchall():
                result.append(tuple(sorted(row.items())))
    return tuple(result)


def test_clean_initialization_and_repeat_refusal() -> None:
    config = _require_explicit_integration_target()
    preflight = connect_server(config)
    try:
        with preflight.cursor() as cursor:
            cursor.execute("SELECT VERSION() AS version")
            server_version = cursor.fetchone()["version"]
        assert server_version.startswith("8.4."), (
            f"integration target must be MySQL 8.4 LTS, got {server_version!r}"
        )
    finally:
        preflight.close()

    result = initialize_database(config)
    assert result.tables == len(EXPECTED_TABLES) == 22
    assert result.foreign_keys == len(EXPECTED_FOREIGN_KEYS) == 38
    assert result.unique_constraints == len(EXPECTED_UNIQUES) == 4
    assert result.check_constraints == len(EXPECTED_CHECKS)

    connection = connect_server(config)
    try:
        before_repeat = _metadata_fingerprint(connection, config.database)
    finally:
        connection.close()

    with pytest.raises(InitializationRefused, match="not empty"):
        initialize_database(config)

    connection = connect_server(config)
    try:
        after_repeat = _metadata_fingerprint(connection, config.database)
    finally:
        connection.close()
    assert after_repeat == before_repeat
