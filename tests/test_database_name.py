from __future__ import annotations

from pathlib import Path
import re
from unittest.mock import patch

import pymysql
import pytest

from labdb.config import ConfigurationError, DatabaseConfig, validate_database_name
from labdb.db import DatabaseConnectionError
from labdb.initialize import (
    InitializationRefused,
    SchemaExecutionError,
    _select_target_database,
    default_schema_path,
    initialize_database,
    split_sql_statements,
)
from labdb.metadata import (
    EXPECTED_CHECKS,
    EXPECTED_COLUMNS,
    EXPECTED_FOREIGN_KEYS,
    EXPECTED_TABLES,
    EXPECTED_UNIQUES,
)


@pytest.mark.parametrize("name", ["labdb_d1", "labdb_test_01"])
def test_valid_database_names(name: str) -> None:
    assert validate_database_name(name) == name


@pytest.mark.parametrize(
    "name",
    [
        "",
        "test0616",
        "mysql",
        "information_schema",
        "performance_schema",
        "sys",
        "LABDB_D1",
        "labdb-Test",
        "labdb test",
        " labdb_test",
        "labdb_test ",
        "labdb_test;",
        "labdb_'test'",
        "labdb_`test`",
        "labdb_测试",
    ],
)
def test_invalid_database_names(name: str) -> None:
    with pytest.raises(ConfigurationError, match="labdb_"):
        validate_database_name(name)


class GuardrailCursor:
    def __init__(self, schema_exists: bool, objects: list[dict[str, str]]) -> None:
        self.schema_exists = schema_exists
        self.objects = objects
        self.result: object = None
        self.executed: list[str] = []

    def __enter__(self) -> "GuardrailCursor":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def execute(self, query: str, parameters: tuple[str, ...] | None = None) -> None:
        self.executed.append(query)
        if "INFORMATION_SCHEMA.SCHEMATA" in query:
            self.result = {"SCHEMA_NAME": parameters[0]} if self.schema_exists else None
        elif "INFORMATION_SCHEMA.TABLES" in query:
            self.result = self.objects
        else:
            self.result = None

    def fetchone(self) -> dict[str, str] | None:
        return self.result if isinstance(self.result, dict) else None

    def fetchall(self) -> list[dict[str, str]]:
        return self.result if isinstance(self.result, list) else []


class GuardrailConnection:
    def __init__(self, cursor: GuardrailCursor) -> None:
        self._cursor = cursor

    def cursor(self) -> GuardrailCursor:
        return self._cursor


def test_missing_database_is_refused_before_use() -> None:
    cursor = GuardrailCursor(schema_exists=False, objects=[])

    with pytest.raises(InitializationRefused, match="does not exist"):
        _select_target_database(GuardrailConnection(cursor), "labdb_missing")

    assert not any(query.startswith("USE ") for query in cursor.executed)


def test_nonempty_database_is_refused_without_changes() -> None:
    cursor = GuardrailCursor(
        schema_exists=True,
        objects=[{"TABLE_NAME": "existing_table", "TABLE_TYPE": "BASE TABLE"}],
    )

    with pytest.raises(InitializationRefused, match="not empty"):
        _select_target_database(GuardrailConnection(cursor), "labdb_d1")

    assert not any(query.startswith("USE ") for query in cursor.executed)
    assert not any("DROP" in query.upper() for query in cursor.executed)


class FailingCursor(GuardrailCursor):
    def execute(self, query: str, parameters: tuple[str, ...] | None = None) -> None:
        if "CONTROLLED_INVALID_DDL" in query:
            self.executed.append(query)
            raise pymysql.ProgrammingError(1064, "controlled test syntax error")
        super().execute(query, parameters)


class FailingConnection(GuardrailConnection):
    def __init__(self) -> None:
        super().__init__(FailingCursor(schema_exists=True, objects=[]))
        self.closed = False

    def close(self) -> None:
        self.closed = True


def config(database: str = "labdb_d1") -> DatabaseConfig:
    return DatabaseConfig("127.0.0.1", 3306, "test_user", "test_password", database)


def test_controlled_ddl_failure_stops_and_does_not_clean_up() -> None:
    fixture = Path("controlled-failure.sql")
    fixture_sql = (
        "CREATE TABLE `first_table` (`id` INT NOT NULL);\n"
        "CONTROLLED_INVALID_DDL;\n"
        "CREATE TABLE `never_reached` (`id` INT NOT NULL);"
    )
    connection = FailingConnection()

    with patch.object(Path, "read_text", return_value=fixture_sql):
        with pytest.raises(SchemaExecutionError) as captured:
            initialize_database(config(), fixture, lambda _: connection)

    message = str(captured.value)
    assert "statement 2" in message
    assert "partial DDL may remain" in message
    assert "No automatic cleanup" in message
    assert any("first_table" in query for query in connection._cursor.executed)
    assert not any("never_reached" in query for query in connection._cursor.executed)
    assert not any(
        destructive in query.upper()
        for query in connection._cursor.executed
        for destructive in ("DROP ", "TRUNCATE ", "DELETE ")
    )
    assert connection.closed


def test_invalid_name_is_rejected_before_connection() -> None:
    called = False

    def forbidden_connect(_: DatabaseConfig) -> None:
        nonlocal called
        called = True
        raise AssertionError("connection must not be attempted")

    with pytest.raises(ConfigurationError):
        initialize_database(config("test0616"), connect_factory=forbidden_connect)

    assert not called


def test_connection_error_is_propagated_without_password() -> None:
    secret = "must-not-appear"
    database_config = DatabaseConfig("127.0.0.1", 3306, "bad_user", secret, "labdb_d1")

    def fail_connection(_: DatabaseConfig) -> None:
        raise DatabaseConnectionError("MySQL authentication failed")

    with pytest.raises(DatabaseConnectionError) as captured:
        initialize_database(database_config, connect_factory=fail_connection)

    assert secret not in str(captured.value)


def test_schema_and_independent_contract_have_frozen_cardinality() -> None:
    schema = default_schema_path().read_text(encoding="utf-8")
    statements = split_sql_statements(schema)

    assert len(statements) == 22
    assert len(EXPECTED_TABLES) == 22
    assert len(EXPECTED_COLUMNS) == 22
    assert len(EXPECTED_FOREIGN_KEYS) == 38
    assert len(EXPECTED_UNIQUES) == 4
    assert len(EXPECTED_CHECKS) > 0
    assert all(statement.lstrip().upper().startswith("CREATE TABLE ") for statement in statements)


def test_schema_object_names_match_independent_contract() -> None:
    schema = default_schema_path().read_text(encoding="utf-8")
    table_names = set(re.findall(r"CREATE TABLE `([^`]+)`", schema))
    foreign_key_names = set(re.findall(r"CONSTRAINT `(fk_[^`]+)`", schema))
    unique_names = set(re.findall(r"CONSTRAINT `(uq_[^`]+)`", schema))
    check_names = set(re.findall(r"CONSTRAINT `(ck_[^`]+)`", schema))

    assert table_names == EXPECTED_TABLES
    assert foreign_key_names == {item.name for item in EXPECTED_FOREIGN_KEYS}
    assert unique_names == set(EXPECTED_UNIQUES)
    assert check_names == EXPECTED_CHECKS


@pytest.mark.parametrize(
    "forbidden",
    [
        "CREATE DATABASE",
        "DROP DATABASE",
        "DROP TABLE",
        "TRUNCATE",
        "SET FOREIGN_KEY_CHECKS",
        "CREATE TRIGGER",
        "CREATE PROCEDURE",
        "CREATE FUNCTION",
        "CREATE EVENT",
        "CREATE VIEW",
        "`选择`",
        "用户密码",
    ],
)
def test_schema_has_no_forbidden_constructs(forbidden: str) -> None:
    schema = default_schema_path().read_text(encoding="utf-8")
    assert forbidden.casefold() not in schema.casefold()
