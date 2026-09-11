from __future__ import annotations

from unittest.mock import patch

from labdb import cli
from labdb.config import DatabaseConfig
from labdb.initialize import StructuralValidationError
from labdb.verify import (
    BUSINESS_CHECKS,
    VerificationError,
    VerificationResult,
    Violation,
    _structural_violations,
)


EXPECTED_CODES = tuple(f"V{number:02d}_" for number in range(1, 17))


def config() -> DatabaseConfig:
    return DatabaseConfig("127.0.0.1", 3306, "test", "secret", "labdb_test")


def test_business_codes_are_unique_complete_and_ordered() -> None:
    codes = tuple(item[0] for item in BUSINESS_CHECKS)
    assert len(codes) == len(set(codes)) == 16
    assert all(code.startswith(prefix) for code, prefix in zip(codes, EXPECTED_CODES, strict=True))


def test_structural_drift_is_reported_with_stable_schema_identifier() -> None:
    with patch(
        "labdb.verify.validate_structure",
        side_effect=StructuralValidationError(
            "Post-initialization metadata validation failed:\n- table set differs"
        ),
    ):
        violations = _structural_violations(object(), "labdb_test")

    assert violations == [
        Violation(
            "S01_SCHEMA_DRIFT",
            "INFORMATION_SCHEMA",
            "labdb_test",
            "table set differs",
        )
    ]


def test_verify_cli_returns_one_and_prints_stable_identifiers(capsys) -> None:
    result = VerificationResult(
        "labdb_test",
        (Violation("V04_RESERVATION_CAPACITY_EXCEEDED", "预约表", "RES_TEST_01", "capacity"),),
    )
    with patch("labdb.cli.load_config", return_value=config()), patch("labdb.cli.verify_database", return_value=result):
        assert cli.main(["verify"]) == 1

    output = capsys.readouterr().out
    assert "V04_RESERVATION_CAPACITY_EXCEEDED\t预约表\tRES_TEST_01\tcapacity" in output


def test_verify_cli_returns_two_for_execution_error(capsys) -> None:
    with patch("labdb.cli.load_config", return_value=config()), patch("labdb.cli.verify_database", side_effect=VerificationError("controlled")):
        assert cli.main(["verify"]) == 2
    assert "Verification execution failed" in capsys.readouterr().err


def test_verify_cli_returns_zero_for_valid_database(capsys) -> None:
    with patch("labdb.cli.load_config", return_value=config()), patch("labdb.cli.verify_database", return_value=VerificationResult("labdb_test", ())):
        assert cli.main(["verify"]) == 0
    assert "0 violations" in capsys.readouterr().out
