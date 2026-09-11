from __future__ import annotations

import pytest

from labdb.config import ConfigurationError, DatabaseConfig, load_config


VALID_ENV = {
    "LABDB_HOST": "127.0.0.1",
    "LABDB_PORT": "3306",
    "LABDB_USER": "labdb_initializer",
    "LABDB_PASSWORD": "placeholder-for-test-only",
    "LABDB_DATABASE": "labdb_d1",
}


def test_load_config_returns_typed_values() -> None:
    assert load_config(VALID_ENV) == DatabaseConfig(
        host="127.0.0.1",
        port=3306,
        user="labdb_initializer",
        password="placeholder-for-test-only",
        database="labdb_d1",
    )


@pytest.mark.parametrize("missing_name", tuple(VALID_ENV))
def test_missing_or_empty_variables_are_reported(missing_name: str) -> None:
    environment = dict(VALID_ENV)
    environment[missing_name] = ""

    with pytest.raises(ConfigurationError, match=missing_name):
        load_config(environment)


@pytest.mark.parametrize(
    "port",
    ["", "0", "65536", "-1", "3306.0", "port", " 3306", "3306 "],
)
def test_invalid_ports_are_rejected(port: str) -> None:
    environment = dict(VALID_ENV)
    environment["LABDB_PORT"] = port

    with pytest.raises(ConfigurationError, match="LABDB_PORT"):
        load_config(environment)


def test_error_does_not_include_password() -> None:
    environment = dict(VALID_ENV)
    environment["LABDB_PORT"] = "invalid"

    with pytest.raises(ConfigurationError) as captured:
        load_config(environment)

    assert VALID_ENV["LABDB_PASSWORD"] not in str(captured.value)
