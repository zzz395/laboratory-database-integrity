"""Non-destructive schema initialization and structural validation."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import pymysql
from pymysql.connections import Connection

from .config import DatabaseConfig, validate_database_name
from .db import connect_server
from .metadata import (
    EXPECTED_CHECKS,
    EXPECTED_COLLATION,
    EXPECTED_COLUMNS,
    EXPECTED_ENGINE,
    EXPECTED_FOREIGN_KEYS,
    EXPECTED_PRIMARY_KEYS,
    EXPECTED_TABLES,
    EXPECTED_UNIQUES,
    ForeignKeySpec,
)


class InitializationError(RuntimeError):
    """Base class for controlled initialization failures."""


class InitializationRefused(InitializationError):
    """Raised before DDL when the target is missing, unsafe, or non-empty."""


class SchemaExecutionError(InitializationError):
    """Raised when one DDL statement fails after execution has begun."""


class StructuralValidationError(InitializationError):
    """Raised when actual metadata differs from the independent contract."""


@dataclass(frozen=True)
class InitializationResult:
    database: str
    statements_executed: int
    tables: int
    foreign_keys: int
    unique_constraints: int
    check_constraints: int


def default_schema_path() -> Path:
    return Path(__file__).resolve().parents[2] / "sql" / "schema.sql"


def quote_validated_database_name(database: str) -> str:
    return f"`{validate_database_name(database)}`"


def split_sql_statements(sql: str) -> list[str]:
    statements: list[str] = []
    buffer: list[str] = []
    state = "normal"
    index = 0

    while index < len(sql):
        char = sql[index]
        following = sql[index + 1] if index + 1 < len(sql) else ""

        if state == "normal":
            if char == "'":
                state = "single"
            elif char == '"':
                state = "double"
            elif char == "`":
                state = "backtick"
            elif char == "#":
                state = "line_comment"
            elif char == "-" and following == "-" and (
                index + 2 == len(sql) or sql[index + 2].isspace()
            ):
                state = "line_comment"
                buffer.append(char)
                index += 1
                char = following
            elif char == "/" and following == "*":
                state = "block_comment"
                buffer.append(char)
                index += 1
                char = following
            elif char == ";":
                statement = "".join(buffer).strip()
                if statement:
                    statements.append(statement)
                buffer.clear()
                index += 1
                continue
        elif state in {"single", "double", "backtick"}:
            closing = {"single": "'", "double": '"', "backtick": "`"}[state]
            if char == "\\" and state != "backtick" and following:
                buffer.append(char)
                index += 1
                char = following
            elif char == closing:
                if following == closing:
                    buffer.append(char)
                    index += 1
                    char = following
                else:
                    state = "normal"
        elif state == "line_comment" and char in "\r\n":
            state = "normal"
        elif state == "block_comment" and char == "*" and following == "/":
            buffer.append(char)
            index += 1
            char = following
            state = "normal"

        buffer.append(char)
        index += 1

    if state in {"single", "double", "backtick", "block_comment"}:
        raise InitializationError("schema.sql contains an unterminated quote or comment")

    tail = "".join(buffer).strip()
    if tail:
        statements.append(tail)
    return statements


def _statement_object(statement: str) -> str:
    match = re.search(r"\bCREATE\s+TABLE\s+(`[^`]+`|[A-Za-z0-9_]+)", statement, re.IGNORECASE)
    return match.group(1) if match else "unknown object"


def _select_target_database(connection: Connection, database: str) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME = %s",
            (database,),
        )
        if cursor.fetchone() is None:
            raise InitializationRefused(
                f"Target database {database!r} does not exist; initialization never creates databases"
            )

        cursor.execute(
            "SELECT TABLE_NAME, TABLE_TYPE FROM INFORMATION_SCHEMA.TABLES "
            "WHERE TABLE_SCHEMA = %s ORDER BY TABLE_NAME",
            (database,),
        )
        existing_objects = cursor.fetchall()
        if existing_objects:
            names = ", ".join(row["TABLE_NAME"] for row in existing_objects[:5])
            suffix = "" if len(existing_objects) <= 5 else ", ..."
            raise InitializationRefused(
                f"Target database {database!r} is not empty ({names}{suffix}); no objects were changed"
            )

        cursor.execute(f"USE {quote_validated_database_name(database)}")


def _group_ordered(rows: list[dict], table_key: str, name_key: str, column_key: str) -> dict[tuple[str, str], tuple[str, ...]]:
    grouped: dict[tuple[str, str], list[tuple[int, str]]] = {}
    for row in rows:
        key = (row[table_key], row[name_key])
        grouped.setdefault(key, []).append((int(row["ORDINAL_POSITION"]), row[column_key]))
    return {
        key: tuple(column for _, column in sorted(values))
        for key, values in grouped.items()
    }


def validate_structure(connection: Connection, database: str) -> None:
    problems: list[str] = []
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT TABLE_NAME, TABLE_TYPE, ENGINE, TABLE_COLLATION "
            "FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = %s",
            (database,),
        )
        table_rows = cursor.fetchall()
        actual_tables = {row["TABLE_NAME"] for row in table_rows}
        if actual_tables != EXPECTED_TABLES:
            problems.append(
                f"table set differs: expected {sorted(EXPECTED_TABLES)!r}, got {sorted(actual_tables)!r}"
            )
        for row in table_rows:
            if row["TABLE_TYPE"] != "BASE TABLE":
                problems.append(f"{row['TABLE_NAME']}: expected BASE TABLE, got {row['TABLE_TYPE']}")
            if row["ENGINE"] != EXPECTED_ENGINE:
                problems.append(f"{row['TABLE_NAME']}: expected engine {EXPECTED_ENGINE}, got {row['ENGINE']}")
            if row["TABLE_COLLATION"] != EXPECTED_COLLATION:
                problems.append(
                    f"{row['TABLE_NAME']}: expected collation {EXPECTED_COLLATION}, got {row['TABLE_COLLATION']}"
                )

        cursor.execute(
            "SELECT TABLE_NAME, COLUMN_NAME, ORDINAL_POSITION, COLUMN_TYPE, IS_NULLABLE, "
            "COLLATION_NAME, COLUMN_DEFAULT FROM INFORMATION_SCHEMA.COLUMNS "
            "WHERE TABLE_SCHEMA = %s ORDER BY TABLE_NAME, ORDINAL_POSITION",
            (database,),
        )
        column_rows = cursor.fetchall()
        actual_by_table: dict[str, list[dict]] = {}
        for row in column_rows:
            actual_by_table.setdefault(row["TABLE_NAME"], []).append(row)
        for table, expected_columns in EXPECTED_COLUMNS.items():
            actual_rows = actual_by_table.get(table, [])
            actual_order = tuple(row["COLUMN_NAME"] for row in actual_rows)
            expected_order = tuple(expected_columns)
            if actual_order != expected_order:
                problems.append(f"{table}: column order/set differs; expected {expected_order!r}, got {actual_order!r}")
                continue
            for row in actual_rows:
                name = row["COLUMN_NAME"]
                expected = expected_columns[name]
                if row["COLUMN_TYPE"].lower() != expected.column_type:
                    problems.append(
                        f"{table}.{name}: expected type {expected.column_type}, got {row['COLUMN_TYPE']}"
                    )
                actual_nullable = row["IS_NULLABLE"] == "YES"
                if actual_nullable != expected.nullable:
                    problems.append(
                        f"{table}.{name}: expected nullable={expected.nullable}, got {actual_nullable}"
                    )
                expected_column_collation = EXPECTED_COLLATION if expected.column_type.startswith("varchar(") else None
                if row["COLLATION_NAME"] != expected_column_collation:
                    problems.append(
                        f"{table}.{name}: expected collation {expected_column_collation}, got {row['COLLATION_NAME']}"
                    )
        term_points = next(
            (row for row in column_rows if row["TABLE_NAME"] == "学期" and row["COLUMN_NAME"] == "初始积分"),
            None,
        )
        if term_points is not None and str(term_points["COLUMN_DEFAULT"]) != "12":
            problems.append(
                f"学期.初始积分: expected default 12, got {term_points['COLUMN_DEFAULT']!r}"
            )

        cursor.execute(
            "SELECT TABLE_NAME, CONSTRAINT_NAME, COLUMN_NAME, ORDINAL_POSITION "
            "FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE "
            "WHERE CONSTRAINT_SCHEMA = %s AND CONSTRAINT_NAME = 'PRIMARY' "
            "ORDER BY TABLE_NAME, ORDINAL_POSITION",
            (database,),
        )
        primary_rows = cursor.fetchall()
        actual_primary_grouped = _group_ordered(
            primary_rows, "TABLE_NAME", "CONSTRAINT_NAME", "COLUMN_NAME"
        )
        actual_primary = {
            table: columns for (table, _), columns in actual_primary_grouped.items()
        }
        if actual_primary != EXPECTED_PRIMARY_KEYS:
            problems.append(f"primary key set differs: expected {EXPECTED_PRIMARY_KEYS!r}, got {actual_primary!r}")

        cursor.execute(
            "SELECT tc.TABLE_NAME, tc.CONSTRAINT_NAME, kcu.COLUMN_NAME, kcu.ORDINAL_POSITION "
            "FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS AS tc "
            "JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE AS kcu "
            "ON kcu.CONSTRAINT_SCHEMA = tc.CONSTRAINT_SCHEMA "
            "AND kcu.TABLE_NAME = tc.TABLE_NAME AND kcu.CONSTRAINT_NAME = tc.CONSTRAINT_NAME "
            "WHERE tc.CONSTRAINT_SCHEMA = %s AND tc.CONSTRAINT_TYPE = 'UNIQUE' "
            "ORDER BY tc.TABLE_NAME, tc.CONSTRAINT_NAME, kcu.ORDINAL_POSITION",
            (database,),
        )
        unique_rows = cursor.fetchall()
        grouped_uniques = _group_ordered(unique_rows, "TABLE_NAME", "CONSTRAINT_NAME", "COLUMN_NAME")
        actual_uniques = {
            constraint: (table, columns)
            for (table, constraint), columns in grouped_uniques.items()
        }
        if actual_uniques != EXPECTED_UNIQUES:
            problems.append(f"unique constraint set differs: expected {EXPECTED_UNIQUES!r}, got {actual_uniques!r}")

        cursor.execute(
            "SELECT rc.CONSTRAINT_NAME, rc.TABLE_NAME, kcu.COLUMN_NAME, "
            "kcu.ORDINAL_POSITION, kcu.REFERENCED_TABLE_NAME, kcu.REFERENCED_COLUMN_NAME, "
            "rc.UPDATE_RULE, rc.DELETE_RULE "
            "FROM INFORMATION_SCHEMA.REFERENTIAL_CONSTRAINTS AS rc "
            "JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE AS kcu "
            "ON kcu.CONSTRAINT_SCHEMA = rc.CONSTRAINT_SCHEMA "
            "AND kcu.TABLE_NAME = rc.TABLE_NAME AND kcu.CONSTRAINT_NAME = rc.CONSTRAINT_NAME "
            "WHERE rc.CONSTRAINT_SCHEMA = %s "
            "ORDER BY rc.CONSTRAINT_NAME, kcu.ORDINAL_POSITION",
            (database,),
        )
        foreign_key_rows = cursor.fetchall()
        fk_parts: dict[str, list[dict]] = {}
        for row in foreign_key_rows:
            fk_parts.setdefault(row["CONSTRAINT_NAME"], []).append(row)
        actual_foreign_keys = set()
        for name, rows in fk_parts.items():
            ordered = sorted(rows, key=lambda row: int(row["ORDINAL_POSITION"]))
            first = ordered[0]
            actual_foreign_keys.add(
                ForeignKeySpec(
                    name=name,
                    child_table=first["TABLE_NAME"],
                    child_columns=tuple(row["COLUMN_NAME"] for row in ordered),
                    parent_table=first["REFERENCED_TABLE_NAME"],
                    parent_columns=tuple(row["REFERENCED_COLUMN_NAME"] for row in ordered),
                    update_rule=first["UPDATE_RULE"],
                    delete_rule=first["DELETE_RULE"],
                )
            )
        expected_foreign_keys = set(EXPECTED_FOREIGN_KEYS)
        if actual_foreign_keys != expected_foreign_keys:
            missing = sorted(expected_foreign_keys - actual_foreign_keys, key=lambda item: item.name)
            unexpected = sorted(actual_foreign_keys - expected_foreign_keys, key=lambda item: item.name)
            problems.append(f"foreign key topology differs: missing={missing!r}, unexpected={unexpected!r}")

        cursor.execute(
            "SELECT CONSTRAINT_NAME, ENFORCED FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS "
            "WHERE CONSTRAINT_SCHEMA = %s AND CONSTRAINT_TYPE = 'CHECK'",
            (database,),
        )
        check_rows = cursor.fetchall()
        actual_checks = {row["CONSTRAINT_NAME"] for row in check_rows}
        if actual_checks != EXPECTED_CHECKS:
            problems.append(
                f"check constraint set differs: expected {sorted(EXPECTED_CHECKS)!r}, got {sorted(actual_checks)!r}"
            )
        not_enforced = sorted(
            row["CONSTRAINT_NAME"] for row in check_rows if row["ENFORCED"] != "YES"
        )
        if not_enforced:
            problems.append(f"check constraints are not enforced: {not_enforced!r}")

    if problems:
        detail = "\n- ".join(problems)
        raise StructuralValidationError(
            "Post-initialization metadata validation failed. Partial DDL may remain and was not cleaned up:\n- "
            + detail
        )


def initialize_database(
    config: DatabaseConfig,
    schema_path: Path | None = None,
    connect_factory: Callable[[DatabaseConfig], Connection] | None = None,
) -> InitializationResult:
    validate_database_name(config.database)
    path = default_schema_path() if schema_path is None else Path(schema_path)
    try:
        sql = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise InitializationError(f"Unable to read schema file {path}: {exc}") from exc
    statements = split_sql_statements(sql)
    if not statements:
        raise InitializationError(f"Schema file {path} contains no executable statements")

    factory = connect_server if connect_factory is None else connect_factory
    connection = factory(config)
    executed = 0
    try:
        try:
            _select_target_database(connection, config.database)
        except pymysql.MySQLError as exc:
            raise InitializationRefused(
                f"Target database preflight failed before DDL; no schema objects were changed: {exc}"
            ) from exc
        with connection.cursor() as cursor:
            for position, statement in enumerate(statements, start=1):
                try:
                    cursor.execute(statement)
                except pymysql.MySQLError as exc:
                    raise SchemaExecutionError(
                        f"Schema statement {position} for {_statement_object(statement)} failed: {exc}. "
                        "Execution stopped; partial DDL may remain because MySQL DDL can commit implicitly. "
                        "No automatic cleanup was attempted."
                    ) from exc
                executed = position
        try:
            validate_structure(connection, config.database)
        except StructuralValidationError:
            raise
        except pymysql.MySQLError as exc:
            raise StructuralValidationError(
                "Post-initialization metadata inspection failed. Partial DDL may remain and was not "
                f"cleaned up: {exc}"
            ) from exc
    finally:
        connection.close()

    return InitializationResult(
        database=config.database,
        statements_executed=executed,
        tables=len(EXPECTED_TABLES),
        foreign_keys=len(EXPECTED_FOREIGN_KEYS),
        unique_constraints=len(EXPECTED_UNIQUES),
        check_constraints=len(EXPECTED_CHECKS),
    )
