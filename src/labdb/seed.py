"""Safe execution of the deterministic synthetic seed."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import pymysql
from pymysql.connections import Connection

from .config import DatabaseConfig, validate_database_name
from .db import connect_server
from .initialize import (
    StructuralValidationError,
    quote_validated_database_name,
    split_sql_statements,
    validate_structure,
)
from .metadata import EXPECTED_TABLES
from .verify import run_business_checks


class SeedError(RuntimeError):
    """Base class for safe seed failures."""


class SeedRefused(SeedError):
    """Raised before DML when schema or data preflight fails."""


class SeedExecutionError(SeedError):
    """Raised after a complete transaction rollback."""


EXPECTED_SEED_COUNTS = {
    "学院": 2, "用户": 5, "学生": 2, "教师": 3, "实验室负责人": 2,
    "实验室": 3, "设备类别": 2, "供应商": 2, "实验设备": 4, "维修人员": 2,
    "学期": 2, "课程": 2, "预约表": 8, "签到记录": 3, "违规记录": 4,
    "预约设备": 6, "预约变更": 2, "故障报修单": 5, "执行维修": 4,
    "安全检查表": 2, "借用": 2, "设备移库记录": 1,
}


@dataclass(frozen=True)
class SeedResult:
    database: str
    statements_executed: int
    row_counts: tuple[tuple[str, int], ...]

    @property
    def total_rows(self) -> int:
        return sum(count for _, count in self.row_counts)


def default_seed_path() -> Path:
    return Path(__file__).resolve().parents[2] / "sql" / "seed.sql"


def _load_seed_statements(path: Path) -> list[str]:
    try:
        sql = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise SeedError(f"Unable to read seed file {path}: {exc}") from exc
    statements = split_sql_statements(sql)
    if not statements:
        raise SeedError(f"Seed file {path} contains no executable statements")
    invalid = [position for position, statement in enumerate(statements, 1) if not statement.lstrip().upper().startswith("INSERT INTO ")]
    if invalid:
        raise SeedError(f"Seed file may contain only INSERT INTO statements; invalid positions: {invalid}")
    return statements


def table_row_counts(connection: Connection) -> dict[str, int]:
    counts: dict[str, int] = {}
    with connection.cursor() as cursor:
        for table in sorted(EXPECTED_TABLES):
            cursor.execute(f"SELECT COUNT(*) AS row_count FROM `{table}`")
            counts[table] = int(cursor.fetchone()["row_count"])
    return counts


def seed_database(
    config: DatabaseConfig,
    seed_path: Path | None = None,
    connect_factory: Callable[[DatabaseConfig], Connection] | None = None,
) -> SeedResult:
    validate_database_name(config.database)
    statements = _load_seed_statements(default_seed_path() if seed_path is None else Path(seed_path))
    connection = (connect_server if connect_factory is None else connect_factory)(config)
    executed = 0
    transaction_started = False
    try:
        with connection.cursor() as cursor:
            cursor.execute(f"USE {quote_validated_database_name(config.database)}")
        try:
            validate_structure(connection, config.database)
        except StructuralValidationError as exc:
            raise SeedRefused(f"Target schema does not match the frozen D1A contract: {exc}") from exc
        before = table_row_counts(connection)
        occupied = [(table, count) for table, count in sorted(before.items()) if count]
        if occupied:
            summary = ", ".join(f"{table}={count}" for table, count in occupied)
            raise SeedRefused(f"Seed requires all 22 business tables to be empty; found {summary}. No rows were changed")

        connection.begin()
        transaction_started = True
        with connection.cursor() as cursor:
            for position, statement in enumerate(statements, 1):
                cursor.execute(statement)
                executed = position

        actual_counts = table_row_counts(connection)
        if actual_counts != EXPECTED_SEED_COUNTS:
            raise SeedExecutionError(f"Post-seed row counts differ: expected {EXPECTED_SEED_COUNTS!r}, got {actual_counts!r}")
        violations = run_business_checks(connection)
        if violations:
            summary = "; ".join(f"{item.code}:{item.entity_id}" for item in violations)
            raise SeedExecutionError(f"Post-seed consistency verification found violations: {summary}")
        connection.commit()
        transaction_started = False
    except SeedRefused:
        raise
    except (pymysql.MySQLError, SeedExecutionError) as exc:
        if transaction_started:
            connection.rollback()
            transaction_started = False
        if isinstance(exc, SeedExecutionError):
            raise
        raise SeedExecutionError(f"Seed statement {executed + 1} failed; the complete seed transaction was rolled back: {exc}") from exc
    finally:
        if transaction_started:
            connection.rollback()
        connection.close()

    return SeedResult(config.database, executed, tuple(sorted(actual_counts.items())))
