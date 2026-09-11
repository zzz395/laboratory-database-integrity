from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from conftest import pytest_sessionfinish


def test_fail_on_skip_changes_a_successful_session_to_failure() -> None:
    reporter = SimpleNamespace(
        stats={"skipped": [object()]},
        write_sep=MagicMock(),
    )
    config = SimpleNamespace(
        getoption=lambda option: option == "--fail-on-skip",
        pluginmanager=SimpleNamespace(get_plugin=lambda name: reporter),
    )
    session = SimpleNamespace(config=config, exitstatus=pytest.ExitCode.OK)

    pytest_sessionfinish(session, pytest.ExitCode.OK)

    assert session.exitstatus is pytest.ExitCode.TESTS_FAILED
    reporter.write_sep.assert_called_once_with(
        "=",
        "zero-skip enforcement failed: 1 test(s) skipped",
        red=True,
    )
