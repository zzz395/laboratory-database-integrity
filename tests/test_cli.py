from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from labdb import cli
from labdb.config import DatabaseConfig
from labdb.initialize import InitializationRefused
from labdb.seed import SeedRefused


CONFIG = DatabaseConfig("127.0.0.1", 3306, "runtime", "test-only", "labdb_test")


def test_help_lists_all_supported_commands(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as captured:
        cli.main(["--help"])

    assert captured.value.code == 0
    output = capsys.readouterr().out
    for command in ("init", "seed", "verify", "transfer"):
        assert command in output


@pytest.mark.parametrize(
    "arguments",
    (
        [],
        ["unknown"],
        ["transfer"],
        ["transfer", "--transfer-id", "MOVE_TEST"],
    ),
)
def test_invalid_or_missing_arguments_exit_two(
    arguments: list[str],
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as captured:
        cli.main(arguments)

    assert captured.value.code == 2
    assert "usage:" in capsys.readouterr().err


def test_init_cli_success_and_refusal_exit_semantics(
    capsys: pytest.CaptureFixture[str],
) -> None:
    result = SimpleNamespace(
        database="labdb_test",
        tables=22,
        foreign_keys=38,
        unique_constraints=4,
        check_constraints=68,
    )
    with patch("labdb.cli.load_config", return_value=CONFIG), patch(
        "labdb.cli.initialize_database", return_value=result
    ):
        assert cli.main(["init"]) == 0
    assert "Initialized labdb_test: 22 tables" in capsys.readouterr().out

    with patch("labdb.cli.load_config", return_value=CONFIG), patch(
        "labdb.cli.initialize_database",
        side_effect=InitializationRefused("controlled refusal"),
    ):
        assert cli.main(["init"]) == 1
    assert "controlled refusal" in capsys.readouterr().err


def test_seed_cli_success_and_refusal_exit_semantics(
    capsys: pytest.CaptureFixture[str],
) -> None:
    result = SimpleNamespace(
        database="labdb_test",
        total_rows=68,
        row_counts=(("synthetic", 68),),
    )
    with patch("labdb.cli.load_config", return_value=CONFIG), patch(
        "labdb.cli.seed_database", return_value=result
    ):
        assert cli.main(["seed"]) == 0
    assert "68 deterministic synthetic rows" in capsys.readouterr().out

    with patch("labdb.cli.load_config", return_value=CONFIG), patch(
        "labdb.cli.seed_database", side_effect=SeedRefused("controlled refusal")
    ):
        assert cli.main(["seed"]) == 1
    assert "controlled refusal" in capsys.readouterr().err
