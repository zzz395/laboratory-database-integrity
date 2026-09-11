from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from labdb.initialize import split_sql_statements
from labdb.config import DatabaseConfig
from labdb.initialize import StructuralValidationError
from labdb.seed import (
    EXPECTED_SEED_COUNTS,
    SeedError,
    SeedRefused,
    _load_seed_statements,
    default_seed_path,
    seed_database,
)


def test_canonical_seed_has_exact_frozen_inventory() -> None:
    assert len(EXPECTED_SEED_COUNTS) == 22
    assert sum(EXPECTED_SEED_COUNTS.values()) == 68
    assert EXPECTED_SEED_COUNTS["预约表"] == 8
    assert EXPECTED_SEED_COUNTS["执行维修"] == 4


def test_seed_is_explicit_deterministic_insert_only_dml() -> None:
    sql = default_seed_path().read_text(encoding="utf-8")
    statements = split_sql_statements(sql)

    assert len(statements) == 22
    assert all(statement.lstrip().upper().startswith("INSERT INTO ") for statement in statements)
    assert all("(" in statement.partition("VALUES")[0] for statement in statements)
    for forbidden in (
        "CREATE DATABASE", "DROP ", "TRUNCATE", "ALTER ", "DELETE ",
        "SET FOREIGN_KEY_CHECKS", "INSERT IGNORE", "REPLACE ",
        "ON DUPLICATE KEY UPDATE", "NOW()", "CURRENT_TIMESTAMP",
    ):
        assert forbidden.casefold() not in sql.casefold()


def test_non_insert_seed_fixture_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "invalid-seed.sql"
    path.write_text("DELETE FROM `用户`;", encoding="utf-8")

    with pytest.raises(SeedError, match="only INSERT INTO"):
        _load_seed_statements(path)


def test_seed_requires_exact_schema_before_transaction() -> None:
    connection = MagicMock()
    config = DatabaseConfig("127.0.0.1", 3306, "test", "secret", "labdb_test")
    with patch("labdb.seed.validate_structure", side_effect=StructuralValidationError("drift")):
        with pytest.raises(SeedRefused, match="frozen D1A contract"):
            seed_database(config, connect_factory=lambda _: connection)
    connection.begin.assert_not_called()


def test_seed_requires_all_business_tables_empty_before_transaction() -> None:
    connection = MagicMock()
    config = DatabaseConfig("127.0.0.1", 3306, "test", "secret", "labdb_test")
    counts = dict.fromkeys(EXPECTED_SEED_COUNTS, 0)
    counts["用户"] = 1
    with patch("labdb.seed.validate_structure"), patch("labdb.seed.table_row_counts", return_value=counts):
        with pytest.raises(SeedRefused, match="用户=1"):
            seed_database(config, connect_factory=lambda _: connection)
    connection.begin.assert_not_called()
